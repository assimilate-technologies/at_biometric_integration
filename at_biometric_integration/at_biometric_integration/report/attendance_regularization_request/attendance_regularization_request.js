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
                if (!frappe.query_report.get_filter_value("period")) return;
                updateMonthlyDates();
                frappe.query_report.refresh();
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
            fieldname: "period",
            label: "Period",
            fieldtype: "Select",
            // Blank by default — the user must pick Weekly / Monthly.
            options: ["", "Weekly", "Monthly"],
            reqd: 1,
            on_change: function () {
                updateFilterVisibility();
                setDefaultDates();
                frappe.query_report.refresh();
            },
        },
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
            // Refresh only when Period is already chosen (otherwise "Please set filters"
            // would flash). The Period filter itself handles the cascade.
            on_change: function () {
                if (!frappe.query_report.get_filter_value("period")) return;
                updateMonthlyDates();
                frappe.query_report.refresh();
            },
        },
        {
            fieldname: "week",
            label: "Week",
            fieldtype: "Select",
            options: ["", "Week 1", "Week 2", "Week 3", "Week 4", "Week 5"],
            // Visibility is controlled by updateFilterVisibility() in period.on_change
            // (using depends_on caused an auto-clear cascade that swallowed
            //  the period filter's own handler).
            on_change: function () {
                setDefaultDates();
                frappe.query_report.refresh();
            },
        },
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            // These are auto-managed — their on_change is intentionally
            // left out to avoid double-fetches when the Period cascade runs.
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
        },
    ],

    onload: function (report) {
        // Period is blank on load → setDefaultDates() now defaults to
        // today..today (single day) so From/To are pre-filled even before
        // the user picks a Period. Frappe then runs report.refresh()
        // immediately after onload (see query_report.js refresh_report()),
        // which will show "Please set filters" until Period is chosen.
        updateFilterVisibility();
        setDefaultDates();
        attachRegularizeButtonHandler();
    },

    onrefresh: function (report) {
        if (!frappe.query_report.get_filter_value("from_date") || !frappe.query_report.get_filter_value("to_date")) {
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

    // From / To Date: HIDE when a Period is chosen (auto-managed)
    qr.toggle_filter_display("from_date", !!period);
    qr.toggle_filter_display("to_date", !!period);

    // Month: HIDE when Period is NOT Monthly (i.e., SHOW only when Monthly)
    qr.toggle_filter_display("month", period !== "Monthly");

    // Week: HIDE when Period is NOT Weekly (i.e., SHOW only when Weekly)
    qr.toggle_filter_display("week", period !== "Weekly");

    // Clear auto-managed filters when they become hidden, so stale
    // values don't leak into the report when switching modes.
    if (period) {
        qr.set_filter_value("from_date", null);
        qr.set_filter_value("to_date", null);
    }
    if (period === "Weekly") {
        qr.set_filter_value("month", null);
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

// Month/Year to calculate against: the Month & Year filters when both are
// set, otherwise today's month/year.
function getReferenceMonthYear() {
    const today = frappe.datetime.get_today(); // "YYYY-MM-DD"
    const month = frappe.query_report.get_filter_value("month");
    const year = frappe.query_report.get_filter_value("year");

    const month_index = REPORT_MONTHS.indexOf(month);

    return {
        year: Number(year) || Number(today.slice(0, 4)),
        month_index: month_index >= 0 ? month_index : Number(today.slice(5, 7)) - 1,
    };
}

// Week 1 = 1st-7th, Week 2 = 8th-14th, Week 3 = 15th-21st,
// Week 4 = 22nd-28th, Week 5 = 29th → month end.
// Clamped to the selected month (Week 5 of February → 28th only).
function getWeekRange(week_label) {
    const week_number = parseInt(String(week_label).replace(/\D/g, ""), 10);
    if (!week_number) return null;

    const { year, month_index } = getReferenceMonthYear();
    const month_str = `${year}-${String(month_index + 1).padStart(2, "0")}`;
    const last_day = new Date(year, month_index + 1, 0).getDate();

    let start = 1 + (week_number - 1) * 7;
    let end = start + 6;
    if (start > last_day) start = last_day;
    if (end > last_day) end = last_day;

    return {
        from_date: `${month_str}-${String(start).padStart(2, "0")}`,
        to_date: `${month_str}-${String(end).padStart(2, "0")}`,
    };
}

function setDefaultDates() {
    const period = frappe.query_report.get_filter_value("period");
    const today = frappe.datetime.get_today();
    let from_date = today;
    let to_date = today;

    if (!period) {
        // Period blank → default to today..today (single day)
        // From/To are visible and editable in this state.
    } else if (period === "Weekly") {
        const week = frappe.query_report.get_filter_value("week");
        const week_range = week && getWeekRange(week);

        if (week_range) {
            from_date = week_range.from_date;
            to_date = week_range.to_date;
        } else {
            // no week chosen yet → current week
            from_date = to_date_str(frappe.datetime.week_start());
            to_date = to_date_str(frappe.datetime.week_end());
        }
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
    const period = frappe.query_report.get_filter_value("period");
    const week = frappe.query_report.get_filter_value("week");
    const month = frappe.query_report.get_filter_value("month");
    const year = frappe.query_report.get_filter_value("year");

    // Weekly: the chosen week (inside the current month of the selected year)
    if (period === "Weekly") {
        const week_range = week && getWeekRange(week);
        if (!week_range) return;
        frappe.query_report.set_filter_value("from_date", week_range.from_date);
        frappe.query_report.set_filter_value("to_date", week_range.to_date);
        return;
    }

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