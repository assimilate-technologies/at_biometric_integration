// frappe.query_reports["Attendance Report Summary"] = {
//     "filters": [
//         {
//             "fieldname": "period",
//             "label": "Period",
//             "fieldtype": "Select",
//             "options": "Daily\nWeekly\nMonthly",
//             "default": "Daily",
//             "reqd": 1,
//             "on_change": function() {
//                 updateVisibility();
//                 updateYearOptions();
//                 frappe.query_report.refresh();
//             }
//         },
//         {
//             "fieldname": "months",
//             "label": "Month",
//             "fieldtype": "Select",
//             "options": "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
//             "on_change": function() {
//                 updateVisibility();
//                 updateMonthOptions();
//                 frappe.query_report.refresh();
//             }
//         },
//         {
//             "fieldname": "year",
//             "label": "Year",
//             "fieldtype": "Select"
//         },
//         {
//             "fieldname": "from_date",
//             "label": "From Date",
//             "fieldtype": "Date"
//         },
//         {
//             "fieldname": "to_date",
//             "label": "To Date",
//             "fieldtype": "Date"
//         },
//         {
//             "fieldname": "status",
//             "label": "Status",
//             "fieldtype": "Select",
//             "options": "\nPresent\nAbsent\nHalf Day\nOn Leave\nWork From Home"
//           },
//           {
//             "fieldname": "employee",
//             "label": "Employee",
//             "fieldtype": "Link",
//             "options": "Employee"
//           },
//           {
//             "fieldname": "company",
//             "label": "Company",
//             "fieldtype": "Link",
//             "options": "Company"
//           },
//           {
//             "fieldname": "department",
//             "label": "Department",
//             "fieldtype": "Link",
//             "options": "Department"
//           }
//     ],

//     // Onload function for initial setup
//     onload: function(report) {
//         updateVisibility();
//         updateYearOptions();
//         updateMonthOptions();
//         frappe.query_report.refresh();
//     }
// };

// // Handles showing/hiding fields based on Period
// function updateVisibility() {
//     let period = frappe.query_report.get_filter_value("period");
//     let months = frappe.query_report.get_filter("months");
//     let year = frappe.query_report.get_filter("year");
//     if (period === "Monthly") {
//         months.df.hidden = 0;
//         months.refresh();
//         year.df.hidden = 0;
//         year.refresh();
//     } else {
//         months.df.hidden = 1;
//         months.refresh();
//         year.df.hidden = 1;
//         year.refresh();
//     }
// }


// function updateYearOptions() {
//     let yearField = frappe.query_report.get_filter("year");
//     let period = frappe.query_report.get_filter_value("period");
//     let currentYear = new Date().getFullYear();
//     let years = [];
//     // Query the Attendance doctype to get distinct years
//     frappe.call({
//         method: "frappe.client.get_list",
//         args: {
//             doctype: "Attendance",
//             fields: ["YEAR(attendance_date) as year"],
//             filters: {},
//             group_by: "YEAR(attendance_date)",
//             order_by: "year desc"
//         },
//         callback: function(response) {
//             if (response && response.message) {
//                 // Add the distinct years to the years array
//                 years = response.message.map(yearObj => yearObj.year.toString());

//                 // If period is "Monthly", show years from the last 5 years
//                 if (period === "Monthly") {
//                     let filteredYears = years.filter(year => parseInt(year) >= (currentYear - 5));
//                     yearField.df.options = filteredYears.join('\n');
//                     yearField.set_input(currentYear.toString());
//                 } 
//                 // else {
//                 //     // If period is not "Monthly", show years from the last 2 years
//                 //     let filteredYears = years.filter(year => parseInt(year) >= (currentYear - 1) && parseInt(year) <= (currentYear + 1));
//                 //     yearField.df.options = filteredYears.join('\n');
//                 //     yearField.set_input(currentYear.toString());
//                 // }

//                 yearField.refresh();
//             }
//         }
//     });
// }

// function updateMonthOptions(){
//    let currentMonth = new Date().getMonth();
//    return currentMonth;
// }


// frappe.query_reports["Attendance Report Summary"] = {
//     filters: [
//         {
//             fieldname: "period",
//             label: "Period",
//             fieldtype: "Select",
//             options: "Daily\nWeekly\nMonthly",
//             default: "Daily",
//             reqd: 1,
//             on_change: function() {
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
//             on_change: function() {
//                 updateVisibility();
//                 updateMonthOptions();
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
 
//     onload: function(report) {
//         updateVisibility();
//         updateYearOptions();
//         updateMonthOptions();
//         frappe.query_report.refresh();
//     }
// };
 
 
// // Show or hide filters according to Period
// function updateVisibility() {
//     let period = frappe.query_report.get_filter_value("period");
//     let months = frappe.query_report.get_filter("months");
//     let year = frappe.query_report.get_filter("year");
 
//     if (period === "Monthly") {
//         months.df.hidden = 0;
//         months.refresh();
 
//         year.df.hidden = 0;
//         year.refresh();
//     } else {
//         months.df.hidden = 1;
//         months.refresh();
 
//         year.df.hidden = 1;
//         year.refresh();
//     }
// }
 
 
// // Fetch Attendance dates and create Year options
// function updateYearOptions() {
//     let yearField = frappe.query_report.get_filter("year");
//     let period = frappe.query_report.get_filter_value("period");
//     let currentYear = new Date().getFullYear();
 
//     frappe.call({
//         method: "frappe.client.get_list",
//         args: {
//             doctype: "Attendance",
//             fields: ["attendance_date"],
//             filters: {
//                 attendance_date: ["is", "set"]
//             },
//             limit_page_length: 0,
//             order_by: "attendance_date desc"
//         },
//         callback: function(response) {
//             if (response && response.message) {
//                 let years = [
//                     ...new Set(
//                         response.message
//                             .map(function(row) {
//                                 if (!row.attendance_date) {
//                                     return null;
//                                 }
 
//                                 return String(row.attendance_date).substring(0, 4);
//                             })
//                             .filter(Boolean)
//                     )
//                 ];
 
//                 years.sort(function(a, b) {
//                     return parseInt(b, 10) - parseInt(a, 10);
//                 });
 
//                 if (period === "Monthly") {
//                     let filteredYears = years.filter(function(year) {
//                         return parseInt(year, 10) >= currentYear - 5;
//                     });
 
//                     if (!filteredYears.includes(String(currentYear))) {
//                         filteredYears.unshift(String(currentYear));
//                     }
 
//                     yearField.df.options = filteredYears.join("\n");
//                     yearField.set_input(String(currentYear));
//                 }
 
//                 yearField.refresh();
//             }
//         }
//     });
// }
 
 
// // Return current month number (January = 0)
// function updateMonthOptions() {
//     let currentMonth = new Date().getMonth();
//     return currentMonth;
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
                updateVisibility();
                updateYearOptions();
                frappe.query_report.refresh();
            }
        },
        {
            fieldname: "months",
            label: "Month",
            fieldtype: "Select",
            options: "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
            on_change: function () {
                updateVisibility();
                frappe.query_report.refresh();
            }
        },
        {
            fieldname: "year",
            label: "Year",
            fieldtype: "Select"
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
            options: "Employee"
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
            options: "Department"
        }
    ],
    onload: function () {
        updateVisibility();
        updateYearOptions();
    }
};

// Show or hide filters according to selected period
function updateVisibility() {
    if (!frappe.query_report) return;
    let period = frappe.query_report.get_filter_value("period");
    let months = frappe.query_report.get_filter("months");
    let year = frappe.query_report.get_filter("year");
    if (!months || !year) return;
    let showMonthlyFilters = period === "Monthly";
    months.df.hidden = showMonthlyFilters ? 0 : 1;
    months.refresh();
    year.df.hidden = showMonthlyFilters ? 0 : 1;
    year.refresh();
}

// Fetch attendance dates without SQL functions.
// Calculate unique years in JavaScript instead.
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
                                // Date format: YYYY-MM-DD
                                return String(row.attendance_date).substring(0, 4);
                            })
                            .filter(function (year) {
                                return year && /^\d{4}$/.test(year);
                            })
                    )
                ];
            }
            // Ensure current year is available in the options.
            if (!years.includes(String(currentYear))) {
                years.push(String(currentYear));
            }
            // Show current year and previous five years.
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
            if (selectedYear && filteredYears.includes(String(selectedYear))) {
                yearField.set_value(String(selectedYear));
            } else {
                yearField.set_value(String(currentYear));
            }
        },
        error: function (error) {
            console.error("Attendance year options load error:", error);
        }
    });
}
 