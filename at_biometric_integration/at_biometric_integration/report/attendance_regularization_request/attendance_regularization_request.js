// ---------------- Dynamic Attendance Regularization Request Report ---------------- //
frappe.query_reports["Attendance Regularization Request"] = {
    filters: [
        {
            fieldname: "year",
            label: "Year",
            fieldtype: "Select",
            options: ["", "2023", "2024", "2025", "2026", "2027"],
            default: String(new Date().getFullYear()),
            on_change: function () {
                const period = frappe.query_report.get_filter_value("period");
                if (!period || period === "Date Range") return;
                updateMonthlyDates();
                frappe.query_report.refresh();
            },
        },
        {
            fieldname: "period",
            label: "Period",
            fieldtype: "Select",
            // Default = Date Range: shows only From/To Date for a simple date-range lookup.
            // Monthly auto-computes date ranges from Month/Year filters.
            options: ["", "Date Range", "Monthly"],
            default: "Date Range",
            on_change: function () {
                updateFilterVisibility();
                setDefaultDates();
                frappe.query_report.refresh();
            },
        },
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            on_change: function () {
                // Only manually trigger refresh in Date Range mode; Monthly mode
                // has its dates auto-set so double‑fetches are avoided.
                const period = frappe.query_report.get_filter_value("period");
                if (period === "Date Range") frappe.query_report.refresh();
            },
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            on_change: function () {
                const period = frappe.query_report.get_filter_value("period");
                if (period === "Date Range") frappe.query_report.refresh();
            },
        },
        {
            fieldname: "employee",
            label: "Employee",
            fieldtype: "Link",
            options: "Employee",
            on_change: function () {
                frappe.query_report.refresh();
            },
        },
        {
            fieldname: "status",
            label: "Status",
            fieldtype: "Select",
            options: ["", "Present", "Absent", "On Leave", "Half Day", "Missed Punch"],
            on_change: function () {
                frappe.query_report.refresh();
            },
        },
        // ---- Hidden helper filters (controlled by updateFilterVisibility) ----
        {
            fieldname: "month",
            label: "Month",
            fieldtype: "Select",
            options: [
                "",
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ],
            default: new Date().toLocaleString("en-US", { month: "long" }),
            on_change: function () {
                const period = frappe.query_report.get_filter_value("period");
                if (!period || period === "Date Range") return;
                updateMonthlyDates();
                frappe.query_report.refresh();
            },
        },
        {
            // Week filter is hidden (Weekly period removed). Kept as a hidden
            // helper filter so any residual references stay safe.
            fieldname: "week",
            label: "Week",
            fieldtype: "Select",
            options: ["", "Week 1", "Week 2", "Week 3", "Week 4", "Week 5"],
            hidden: 1,
            on_change: function () {
                setDefaultDates();
                frappe.query_report.refresh();
            },
        },
    ],

    onload: function (report) {
        // Period is blank on load → From/To are left empty so the
        // report shows ALL data by default. User can pick Period =
        // Monthly for auto-ranges, or manually set From/To.
        updateFilterVisibility();
        setDefaultDates();
        attachRegularizeButtonHandler();
    },

    onrefresh: function (report) {
        // Only re-derive dates when a Period is chosen; with no Period
        // the From/To stay empty and the report shows all data.
        if (frappe.query_report.get_filter_value("period")) {
            setDefaultDates();
        }
        setTimeout(() => attachRegularizeButtonHandler(), 300);
    },

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        switch (column.fieldname) {
            case "action":
                if (data.action && data.action.includes("Create")) {
                    const buttonId = `reg-btn-${data.employee}-${data.attendance_date}`;
                    return `<button id="${buttonId}" class="btn btn-primary btn-sm reg-btn"
                        data-employee='${data.employee}'
                        data-employee_name='${data.employee_name}'
                        data-date='${data.attendance_date}'
                        data-shift_start='${data.shift_start}'
                        data-shift_end='${data.shift_end}'
                        data-in_time='${data.in_time}'
                        data-out_time='${data.out_time}'
                        data-status='${data.status}'
                        style="font-weight:500;">
                        ${data.action}
                    </button>`;
                } else {
                    return `<button class="btn btn-light btn-sm" disabled>-</button>`;
                }

            case "regularization_eligible":
                const eligibleColor = data.regularization_eligible === "Yes" ? "#16a34a" : "#dc2626";
                return `<span style="color:${eligibleColor};font-weight:600;">${value}</span>`;

            case "remarks":
                let color = "#000";
                if (data.remarks.includes("Wait")) color = "#f39c12";
                else if (data.remarks.includes("Eligible")) color = "#16a34a";
                else if (data.remarks.includes("Exceeded") || data.remarks.includes("Limit")) color = "#e74c3c";
                return `<span style="color:${color};font-weight:500;">${frappe.utils.escape_html(data.remarks)}</span>`;
        }
        return value;
    },
};

// ---------- Visibility helpers ----------
// Manually toggle filter visibility to avoid the `depends_on` auto-clear
// cascade that would swallow the Period filter's on_change handler.
// toggle_filter_display(fieldname, flag): flag=true -> HIDE, flag=false -> SHOW
function updateFilterVisibility() {
    const period = frappe.query_report.get_filter_value("period");
    const qr = frappe.query_report;

    // Date Range: show From/To Date (user picks dates manually); hide Month & Week.
    // Monthly: hide From/To Date (auto-managed); show Month; hide Week.
    // Blank: show From/To Date for free-form date range; hide Month & Week.

    const isDateRange = period === "Date Range";
    const isMonthly   = period === "Monthly";

    // From / To Date: SHOW for Date Range or blank; HIDE for Monthly (auto-managed)
    qr.toggle_filter_display("from_date", isMonthly);
    qr.toggle_filter_display("to_date",   isMonthly);

    // Month: SHOW only when Monthly
    qr.toggle_filter_display("month", !isMonthly);

    // Week: always HIDDEN (Weekly period removed)
    qr.toggle_filter_display("week", true);

    // Clear auto-managed date filters when switching away from Date Range/blank
    // so stale manual dates don't bleed into Monthly mode.
    if (isMonthly) {
        qr.set_filter_value("from_date", null);
        qr.set_filter_value("to_date", null);
    }
}

// ---------------- Helper Functions ---------------- //

// `var` (not `const`): report scripts are injected as global <script> tags,
// and re-declaring a global `const` would throw if this file is ever eval'd twice.
var REPORT_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
];

// Normalise frappe.datetime's ISO output ("2026-10-26T00:00:00+05:30")
// to a plain date string the Date filter accepts in any user date format.
function to_date_str(value) {
    return String(value || "").slice(0, 10);
}

function setDefaultDates() {
    const period = frappe.query_report.get_filter_value("period");

    if (!period) {
        // Period blank → no default date range.
        // Clear From/To so the report fetches ALL data by default.
        frappe.query_report.set_filter_value("from_date", null);
        frappe.query_report.set_filter_value("to_date", null);
        return;
    }

    let from_date = null;
    let to_date = null;

    if (period === "Date Range") {
        // Date Range → default both From Date and To Date to today.
        // The user may then adjust them freely.
        const today = frappe.datetime.get_today();
        from_date = today;
        to_date   = today;

    } else if (period === "Monthly") {
        // Monthly: respect Month/Year filters if both are set; else current month/year
        const month = frappe.query_report.get_filter_value("month");
        const year = frappe.query_report.get_filter_value("year");

        if (month && year) {
            const month_index = REPORT_MONTHS.indexOf(month);
            if (month_index >= 0) {
                const month_str = `${year}-${String(month_index + 1).padStart(2, "0")}`;
                const last_day = new Date(Number(year), month_index + 1, 0).getDate();
                from_date = `${month_str}-01`;
                to_date = `${month_str}-${String(last_day).padStart(2, "0")}`;
            } else {
                // invalid month → current month
                from_date = to_date_str(frappe.datetime.month_start());
                to_date = to_date_str(frappe.datetime.month_end());
            }
        } else {
            // no month/year → current month
            from_date = to_date_str(frappe.datetime.month_start());
            to_date = to_date_str(frappe.datetime.month_end());
        }
    }

    frappe.query_report.set_filter_value("from_date", from_date);
    frappe.query_report.set_filter_value("to_date", to_date);
}

// Update monthly date range based on selected month/year
function updateMonthlyDates() {
    const month = frappe.query_report.get_filter_value("month");
    const year = frappe.query_report.get_filter_value("year");

    if (!month || !year) return;

    const month_index = REPORT_MONTHS.indexOf(month);
    if (month_index < 0) return;

    const month_str = `${year}-${String(month_index + 1).padStart(2, "0")}`;
    const last_day = new Date(Number(year), month_index + 1, 0).getDate();

    frappe.query_report.set_filter_value("from_date", `${month_str}-01`);
    frappe.query_report.set_filter_value(
        "to_date",
        `${month_str}-${String(last_day).padStart(2, "0")}`
    );
}

// ---------------- Button Handler ---------------- //
function attachRegularizeButtonHandler() {
    $(document).off("click", ".reg-btn");
    $(document).on("click", ".reg-btn", function () {
        const btn = $(this);
        openAttendanceRegularizationForm(
            btn.data("employee"),
            btn.data("employee_name"),
            btn.data("date"),
            btn.data("shift_start"),
            btn.data("shift_end"),
            btn.data("in_time"),
            btn.data("out_time"),
            btn.data("status")
        );
    });
}

function openAttendanceRegularizationForm(employee, employee_name, attendance_date, shift_start, shift_end, in_time, out_time, status) {
    frappe.new_doc("Attendance Regularization", {
        employee,
        employee_name,
        date: attendance_date,
        shift_start,
        shift_end,
        in_time,
        out_time,
        attendance_status: status,
        reason: "Requested via Attendance Regularization Report",
    });
}