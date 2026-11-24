// frappe.query_reports["Attendance Report Summary"] = {
//     filters: [
//         {
//             fieldname: "period",
//             label: "Period",
//             fieldtype: "Select",
//             options: "Daily\nWeekly\nMonthly",
//             default: "Daily",
//             reqd: 1,
//             on_change: function () {
//                 updateVisibility();
//                 updateYearOptions();
//                 frappe.query_report.refresh();
//             }
//         },
//         {
//             fieldname: "months",
//             label: "Month",
//             fieldtype: "Select",
//             options: "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
//             on_change: function () {
//                 updateVisibility();
//                 frappe.query_report.refresh();
//             }
//         },
//         {
//             fieldname: "year",
//             label: "Year",
//             fieldtype: "Select"
//         },
//         {
//             fieldname: "from_date",
//             label: "From Date",
//             fieldtype: "Date"
//         },
//         {
//             fieldname: "to_date",
//             label: "To Date",
//             fieldtype: "Date"
//         },
//         {
//             fieldname: "status",
//             label: "Status",
//             fieldtype: "Select",
//             options: "\nPresent\nAbsent\nHalf Day\nOn Leave\nWork From Home"
//         },
//         {
//             fieldname: "employee",
//             label: "Employee",
//             fieldtype: "Link",
//             options: "Employee"
//         },
//         {
//             fieldname: "company",
//             label: "Company",
//             fieldtype: "Link",
//             options: "Company"
//         },
//         {
//             fieldname: "department",
//             label: "Department",
//             fieldtype: "Link",
//             options: "Department"
//         }
//     ],
//     onload: function () {
//         updateVisibility();
//         updateYearOptions();
//     }
// };

// // Show or hide filters according to selected period
// function updateVisibility() {
//     if (!frappe.query_report) return;
//     let period = frappe.query_report.get_filter_value("period");
//     let months = frappe.query_report.get_filter("months");
//     let year = frappe.query_report.get_filter("year");
//     if (!months || !year) return;
//     let showMonthlyFilters = period === "Monthly";
//     months.df.hidden = showMonthlyFilters ? 0 : 1;
//     months.refresh();
//     year.df.hidden = showMonthlyFilters ? 0 : 1;
//     year.refresh();
// }

// // Fetch attendance dates without SQL functions.
// // Calculate unique years in JavaScript instead.
// function updateYearOptions() {
//     if (!frappe.query_report) return;
//     let yearField = frappe.query_report.get_filter("year");
//     if (!yearField) return;
//     let currentYear = new Date().getFullYear();
//     frappe.call({
//         method: "frappe.client.get_list",
//         args: {
//             doctype: "Attendance",
//             fields: ["attendance_date"],
//             filters: {
//                 docstatus: ["<", 2]
//             },
//             limit_page_length: 0,
//             order_by: "attendance_date desc"
//         },
//         callback: function (response) {
//             let years = [];
//             if (response && Array.isArray(response.message)) {
//                 years = [
//                     ...new Set(
//                         response.message
//                             .map(function (row) {
//                                 if (!row.attendance_date) return null;
//                                 // Date format: YYYY-MM-DD
//                                 return String(row.attendance_date).substring(0, 4);
//                             })
//                             .filter(function (year) {
//                                 return year && /^\d{4}$/.test(year);
//                             })
//                     )
//                 ];
//             }
//             // Ensure current year is available in the options.
//             if (!years.includes(String(currentYear))) {
//                 years.push(String(currentYear));
//             }
//             // Show current year and previous five years.
//             let filteredYears = years
//                 .filter(function (year) {
//                     let numericYear = parseInt(year, 10);
//                     return numericYear >= currentYear - 5 &&
//                         numericYear <= currentYear;
//                 })
//                 .sort(function (a, b) {
//                     return parseInt(b, 10) - parseInt(a, 10);
//                 });
//             yearField.df.options = filteredYears.join("\n");
//             yearField.refresh();
//             let selectedYear = frappe.query_report.get_filter_value("year");
//             if (selectedYear && filteredYears.includes(String(selectedYear))) {
//                 yearField.set_value(String(selectedYear));
//             } else {
//                 yearField.set_value(String(currentYear));
//             }
//         },
//         error: function (error) {
//             console.error("Attendance year options load error:", error);
//         }
//     });
// }






frappe.query_reports["Attendance Report Summary"] = {
    filters: [
        {
            fieldname: "period",
            label: "Period",
            fieldtype: "Select",
            options: "Daily\nWeekly\nMonthly",
            default: "Daily",
            reqd: 1,
            on_change: function () {
                setPeriodDefaults();
                updateVisibility();
                frappe.query_report.refresh();
            }
        },
        {
            fieldname: "months",
            label: "Month",
            fieldtype: "Select",
            options: "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
            on_change: function () {
                updateMonthlyDateRange();
                frappe.query_report.refresh();
            }
        },
        {
            fieldname: "year",
            label: "Year",
            fieldtype: "Select",
            on_change: function () {
                updateMonthlyDateRange();
                frappe.query_report.refresh();
            }
        },
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date"
        },
        {
            fieldname: "status",
            label: "Status",
            fieldtype: "Select",
            options: "\nPresent\nAbsent\nHalf Day\nOn Leave\nWork From Home"
        },
        {
            fieldname: "employee",
            label: "Employee",
            fieldtype: "Link",
            options: "Employee",

            get_query: function () {
                let department = frappe.query_report.get_filter_value("department");

                let filters = {
                    status: "Active"
                };

                if (department) {
                    filters.department = department;
                }

                return {
                    filters: filters
                };
            },

            on_change: function () {
                let employee = frappe.query_report.get_filter_value("employee");

                if (!employee) {
                    frappe.query_report.set_filter_value("department", "");
                    frappe.query_report.refresh();
                    return;
                }

                frappe.db.get_value(
                    "Employee",
                    employee,
                    "department"
                ).then(function (response) {
                    let department = response &&
                        response.message
                        ? response.message.department
                        : "";

                    frappe.query_report.set_filter_value(
                        "department",
                        department || ""
                    );
                });
            }
        },
        {
            fieldname: "company",
            label: "Company",
            fieldtype: "Link",
            options: "Company"
        },
        {
            fieldname: "department",
            label: "Department",
            fieldtype: "Link",
            options: "Department",

            on_change: function () {
                let department = frappe.query_report.get_filter_value("department");
                let employee = frappe.query_report.get_filter_value("employee");

                if (!employee) {
                    frappe.query_report.refresh();
                    return;
                }

                frappe.db.get_value(
                    "Employee",
                    employee,
                    "department"
                ).then(function (response) {
                    let employeeDepartment = response &&
                        response.message
                        ? response.message.department
                        : "";

                    if (department && employeeDepartment !== department) {
                        frappe.query_report.set_filter_value("employee", "");
                    } else {
                        frappe.query_report.refresh();
                    }
                });
            }
        }
    ],

    onload: function () {
        setPeriodDefaults();

        setTimeout(function () {
            updateVisibility();
            updateYearOptions();
        }, 300);
    }
};


// Today's date in YYYY-MM-DD format.
function getTodayDate() {
    let today = new Date();

    let year = today.getFullYear();
    let month = String(today.getMonth() + 1).padStart(2, "0");
    let day = String(today.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}


// Convert Date object to YYYY-MM-DD.
function formatDate(date) {
    let year = date.getFullYear();
    let month = String(date.getMonth() + 1).padStart(2, "0");
    let day = String(date.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}


// Current month name.
function getCurrentMonthName() {
    return [
        "January", "February", "March", "April",
        "May", "June", "July", "August",
        "September", "October", "November", "December"
    ][new Date().getMonth()];
}


// Get month number from month name.
function getMonthNumber(monthName) {
    let months = [
        "January", "February", "March", "April",
        "May", "June", "July", "August",
        "September", "October", "November", "December"
    ];

    return months.indexOf(monthName);
}


// Set default dates according to selected period.
function setPeriodDefaults() {
    if (!frappe.query_report) return;

    let period = frappe.query_report.get_filter_value("period");

    let today = new Date();
    let todayString = getTodayDate();

    if (period === "Daily") {

        // Daily: Today's date only.
        frappe.query_report.set_filter_value("from_date", todayString);
        frappe.query_report.set_filter_value("to_date", "");

    }

    else if (period === "Weekly") {

        // Weekly: Current Monday to today.
        let startOfWeek = new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate()
        );

        let day = startOfWeek.getDay();
        let difference = day === 0 ? 6 : day - 1;

        startOfWeek.setDate(startOfWeek.getDate() - difference);

        frappe.query_report.set_filter_value(
            "from_date",
            formatDate(startOfWeek)
        );

        frappe.query_report.set_filter_value(
            "to_date",
            todayString
        );

    }

    else if (period === "Monthly") {

        // Monthly: Current month's first date to today.
        frappe.query_report.set_filter_value(
            "months",
            getCurrentMonthName()
        );

        frappe.query_report.set_filter_value(
            "year",
            String(today.getFullYear())
        );

        updateMonthlyDateRange();
    }
}


// Update monthly date range according to selected Month and Year.
function updateMonthlyDateRange() {
    if (!frappe.query_report) return;

    let period = frappe.query_report.get_filter_value("period");

    if (period !== "Monthly") return;

    let monthName = frappe.query_report.get_filter_value("months");
    let yearValue = frappe.query_report.get_filter_value("year");

    if (!monthName || !yearValue) return;

    let monthNumber = getMonthNumber(monthName);

    if (monthNumber < 0) return;

    let selectedYear = parseInt(yearValue, 10);

    if (isNaN(selectedYear)) return;

    let today = new Date();
    let todayString = getTodayDate();

    // First date of selected month.
    let startDate = new Date(selectedYear, monthNumber, 1);

    // Last date of selected month.
    let endDate = new Date(selectedYear, monthNumber + 1, 0);

    // Do not include future dates.
    if (endDate > today) {
        endDate = new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate()
        );
    }

    // If selected month is entirely in the future,
    // keep the range at today's date rather than extending into future.
    if (startDate > today) {
        startDate = new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate()
        );
    }

    frappe.query_report.set_filter_value(
        "from_date",
        formatDate(startDate)
    );

    frappe.query_report.set_filter_value(
        "to_date",
        formatDate(endDate)
    );
}


// Show/hide filters according to selected period.
function updateVisibility() {
    if (!frappe.query_report) return;

    let period = frappe.query_report.get_filter_value("period");

    let months = frappe.query_report.get_filter("months");
    let year = frappe.query_report.get_filter("year");
    let fromDate = frappe.query_report.get_filter("from_date");
    let toDate = frappe.query_report.get_filter("to_date");

    if (!months || !year || !fromDate || !toDate) return;

    // Daily: Only From Date visible.
    // Weekly: From Date and To Date visible.
    // Monthly: All date and month/year filters visible.

    let showFromDate = true;
    let showToDate = period === "Weekly" || period === "Monthly";
    let showMonthYear = period === "Monthly";

    setFilterVisibility(months, showMonthYear);
    setFilterVisibility(year, showMonthYear);
    setFilterVisibility(fromDate, showFromDate);
    setFilterVisibility(toDate, showToDate);
}


// Common filter visibility function.
function setFilterVisibility(field, show) {
    if (!field) return;

    field.df.hidden = show ? 0 : 1;

    if (field.$wrapper) {
        field.$wrapper.toggle(show);
    }

    field.refresh();
}


// Fetch available years from Attendance.
function updateYearOptions() {
    if (!frappe.query_report) return;

    let yearField = frappe.query_report.get_filter("year");

    if (!yearField) return;

    let currentYear = new Date().getFullYear();

    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Attendance",
            fields: ["attendance_date"],
            filters: {
                docstatus: ["<", 2]
            },
            limit_page_length: 0,
            order_by: "attendance_date desc"
        },

        callback: function (response) {
            let years = [];

            if (response && Array.isArray(response.message)) {
                years = [
                    ...new Set(
                        response.message
                            .map(function (row) {
                                if (!row.attendance_date) return null;

                                return String(row.attendance_date).substring(0, 4);
                            })
                            .filter(function (year) {
                                return year && /^\d{4}$/.test(year);
                            })
                    )
                ];
            }

            if (!years.includes(String(currentYear))) {
                years.push(String(currentYear));
            }

            let filteredYears = years
                .filter(function (year) {
                    let numericYear = parseInt(year, 10);

                    return numericYear >= currentYear - 5 &&
                        numericYear <= currentYear;
                })
                .sort(function (a, b) {
                    return parseInt(b, 10) - parseInt(a, 10);
                });

            yearField.df.options = filteredYears.join("\n");
            yearField.refresh();

            let selectedYear = frappe.query_report.get_filter_value("year");

            if (
                selectedYear &&
                filteredYears.includes(String(selectedYear))
            ) {
                yearField.set_value(String(selectedYear));
            } else {
                yearField.set_value(String(currentYear));
            }

            updateVisibility();
        },

        error: function (error) {
            console.error("Attendance year options load error:", error);
        }
    });
}

