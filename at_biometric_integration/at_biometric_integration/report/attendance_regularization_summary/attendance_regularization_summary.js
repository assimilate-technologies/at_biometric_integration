frappe.query_reports["Attendance Regularization Summary"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company"
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department"
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee"
        },
        {
            fieldname: "employee_type",
            label: __("Employee Type"),
            fieldtype: "Link",
            options: "Employment Type"
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nPresent\nAbsent\nHalf Day\nOn Leave\nWork From Home\nHoliday\nWeek Off\nNot Marked"
        },
        {
            fieldname: "missed_punch",
            label: __("Missed Punch"),
            fieldtype: "Select",
            options: "\nIN\nOUT\nBOTH\n-\nNA"
        },
        {
            fieldname: "eligibility",
            label: __("Regularization Eligible"),
            fieldtype: "Select",
            options: "\nYes\nNo"
        }
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (!data) {
            return value;
        }

        if (column.fieldname === "employee" && data.regularization_name) {
            value += '<span class="reg-created-row-marker" style="display:none"></span>';
        }

        if (column.fieldname === "status") {
            if (data.status === "Present") {
                value = `<span style="color:#198754;font-weight:bold">${value}</span>`;
            } else if (data.status === "Absent") {
                value = `<span style="color:#dc3545;font-weight:bold">${value}</span>`;
            } else if (data.status === "Half Day") {
                value = `<span style="color:#f0ad4e;font-weight:bold">${value}</span>`;
            } else if (data.status === "On Leave") {
                value = `<span style="color:#dc3545;font-weight:bold">${value}</span>`;
            } else if (data.status === "Holiday") {
                value = `<span style="color:#0d6efd;font-weight:bold">${value}</span>`;
            } else if (data.status === "Week Off") {
                value = `<span style="color:#6f42c1;font-weight:bold">${value}</span>`;
            } else if (data.status === "Not Marked") {
                value = `<span style="color:#6c757d;font-weight:bold">${value}</span>`;
            }else if (data.status === "Work From Home") {
                value = `<span style="color:#198754;font-weight:bold">${value}</span>`;
            }
        }

        if (column.fieldname === "eligible" && data.eligible === "Yes") {
            value = `<span style="color:#198754;font-weight:bold">${value}</span>`;
        }

        if (
            column.fieldname === "missed_punch" &&
            ["IN", "OUT", "BOTH"].includes(data.missed_punch)
        ) {
            value = `<span style="color:#dc3545;font-weight:bold">${value}</span>`;
        }

        if (column.fieldname === "action") {
            if (data.regularization_name) {
                const name = encodeURIComponent(data.regularization_name);
                const state = frappe.utils.escape_html(data.action || "Open Request");

                value = `<a href="/app/attendance-regularization/${name}">${state}</a>`;
            } else if (data.eligible === "Yes") {
                const employee = frappe.utils.escape_html(data.employee);
                const date = frappe.utils.escape_html(data.attendance_date);

                value = `
                    <button class="btn btn-xs btn-primary create-regularization"
                        data-employee="${employee}"
                        data-date="${date}">
                        ${__("Create Regularization")}
                    </button>`;
            } else {
                value = "";
            }
        }

        return value;
    },

    onload: function (report) {
        if (!document.getElementById("attendance-regularization-summary-style")) {
            const style = document.createElement("style");
            style.id = "attendance-regularization-summary-style";
            style.innerHTML = `
                .dt-row:has(.reg-created-row-marker) .dt-cell {
                    background-color: #f8d7da !important;
                }
            `;
            document.head.appendChild(style);
        }

        report.page.wrapper.on(
            "click",
            ".create-regularization",
            function () {
                const employee = $(this).attr("data-employee");
                const date = $(this).attr("data-date");

                const row = report.data.find(
                    d => d.employee === employee &&
                        d.attendance_date === date
                );

                if (!row) {
                    frappe.msgprint(__("Unable to find report row."));
                    return;
                }

                frappe.new_doc("Attendance Regularization", {
                    employee: row.employee,
                    date: row.attendance_date,
                    attendance_status: row.status,
                    system_in_time: row.in_time !== "-" ? row.in_time : "",
                    system_out_time: row.out_time !== "-" ? row.out_time : "",
                    in_time: row.in_time !== "-" ? row.in_time : "",
                    out_time: row.out_time !== "-" ? row.out_time : ""
                });
            }
        );
    }
};