// frappe.query_reports["Monthly Attendance Summary"] = {
//   filters: [
//     {
//       fieldname: "month",
//       label: "Month",
//       fieldtype: "Select",
//       options: [
//         "", "January", "February", "March", "April", "May", "June",
//         "July", "August", "September", "October", "November", "December"
//       ].join("\n"),
//       reqd: 1,
//       on_change: function () {
//         setDatesFromMonthYear();
//         frappe.query_report.refresh();
//       }
//     },
//     {
//       fieldname: "year",
//       label: "Year",
//       fieldtype: "Select",
//       on_change: function () {
//         setDatesFromMonthYear();
//         frappe.query_report.refresh();
//       }
//     },
//     {
//       fieldname: "from_date",
//       label: "From Date",
//       fieldtype: "Date"
//     },
//     {
//       fieldname: "to_date",
//       label: "To Date",
//       fieldtype: "Date"
//     },
//     {
//       fieldname: "employee",
//       label: "Employee",
//       fieldtype: "Link",
//       options: "Employee"
//     },
//     {
//       fieldname: "company",
//       label: "Company",
//       fieldtype: "Link",
//       options: "Company"
//     }
//   ],

//   onload: function (report) {
//     updateYearOptions();
//     setCurrentMonthAndYear();
//   }
// };

// // Format date as "YYYY-MM-DD"
// function formatDateToYYYYMMDD(date) {
//   const year = date.getFullYear();
//   const month = String(date.getMonth() + 1).padStart(2, '0');
//   const day = String(date.getDate()).padStart(2, '0');
//   return `${year}-${month}-${day}`;
// }

// function setDatesFromMonthYear() {
//   const month = frappe.query_report.get_filter_value("month");
//   const year = frappe.query_report.get_filter_value("year");

//   if (!month || !year) return;

//   const monthMap = {
//     "January": 0, "February": 1, "March": 2, "April": 3,
//     "May": 4, "June": 5, "July": 6, "August": 7,
//     "September": 8, "October": 9, "November": 10, "December": 11
//   };

//   const start = new Date(year, monthMap[month], 1);
//   const end = new Date(year, monthMap[month] + 1, 0);

//   frappe.query_report.set_filter_value("from_date", formatDateToYYYYMMDD(start));
//   frappe.query_report.set_filter_value("to_date", formatDateToYYYYMMDD(end));
// }

// function setCurrentMonthAndYear() {
//   const currentDate = new Date();
//   const currentMonth = currentDate.toLocaleString('default', { month: 'long' });
//   const currentYear = currentDate.getFullYear();

//   frappe.query_report.get_filter("month").set_input(currentMonth);
//   frappe.query_report.get_filter("year").set_input(currentYear.toString());

//   setDatesFromMonthYear();
//   frappe.query_report.refresh();
// }

// function updateYearOptions() {
//   const yearField = frappe.query_report.get_filter("year");

//   frappe.call({
//     method: "frappe.client.get_list",
//     args: {
//       doctype: "Attendance",
//       fields: ["YEAR(attendance_date) as year"],
//       group_by: "YEAR(attendance_date)",
//       order_by: "year desc"
//     },
//     callback: function (response) {
//       if (response && response.message) {
//         const currentYear = new Date().getFullYear();
//         const years = response.message
//           .map(entry => entry.year && entry.year.toString())
//           .filter(Boolean)
//           .filter(year => parseInt(year) >= currentYear - 5);

//         if (years.length) {
//           yearField.df.options = years.join("\n");
//           yearField.set_input(currentYear.toString());
//           yearField.refresh();
//         }
//       }
//     }
//   });
// }



// frappe.query_reports["Monthly Attendance Summary"] = {
//     filters: [
//         {
//             fieldname: "month",
//             label: "Month",
//             fieldtype: "Select",
//             options: [
//                 "",
//                 "January", "February", "March", "April",
//                 "May", "June", "July", "August",
//                 "September", "October", "November", "December"
//             ].join("\n"),
//             reqd: 1,
//             on_change: function () {
//                 setDatesFromMonthYear();
//                 frappe.query_report.refresh();
//             }
//         },
//         {
//             fieldname: "year",
//             label: "Year",
//             fieldtype: "Select",
//             on_change: function () {
//                 setDatesFromMonthYear();
//                 frappe.query_report.refresh();
//             }
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
//         }
//     ],
//     onload: function (report) {
//         updateYearOptions();
//         setCurrentMonthAndYear();
//     }
// };

// // Format date as YYYY-MM-DD
// function formatDateToYYYYMMDD(date) {
//     const year = date.getFullYear();
//     const month = String(date.getMonth() + 1).padStart(2, "0");
//     const day = String(date.getDate()).padStart(2, "0");
//     return `${year}-${month}-${day}`;
// }

// // Set From Date and To Date according to selected month and year
// function setDatesFromMonthYear() {
//     const month = frappe.query_report.get_filter_value("month");
//     const year = frappe.query_report.get_filter_value("year");
//     if (!month || !year) {
//         return;
//     }
//     const monthMap = {
//         "January": 0,
//         "February": 1,
//         "March": 2,
//         "April": 3,
//         "May": 4,
//         "June": 5,
//         "July": 6,
//         "August": 7,
//         "September": 8,
//         "October": 9,
//         "November": 10,
//         "December": 11
//     };
//     if (monthMap[month] === undefined) {
//         return;
//     }
//     const start = new Date(
//         Number(year),
//         monthMap[month],
//         1
//     );
//     const end = new Date(
//         Number(year),
//         monthMap[month] + 1,
//         0
//     );
//     frappe.query_report.set_filter_value(
//         "from_date",
//         formatDateToYYYYMMDD(start)
//     );
//     frappe.query_report.set_filter_value(
//         "to_date",
//         formatDateToYYYYMMDD(end)
//     );
// }

// // Set current month and year by default
// function setCurrentMonthAndYear() {
//     const currentDate = new Date();
//     const currentMonth = currentDate.toLocaleString(
//         "en-US",
//         { month: "long" }
//     );
//     const currentYear = String(currentDate.getFullYear());
//     frappe.query_report.get_filter("month").set_input(currentMonth);
//     frappe.query_report.get_filter("year").set_input(currentYear);
//     setDatesFromMonthYear();
//     frappe.query_report.refresh();
// }

// // Fetch Attendance dates without using SQL functions in fields
// function updateYearOptions() {
//     const yearField = frappe.query_report.get_filter("year");
//     const currentYear = new Date().getFullYear();
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
//         callback: function (response) {
//             if (response && response.message) {
//                 const years = [
//                     ...new Set(
//                         response.message
//                             .map(function (entry) {
//                                 if (!entry.attendance_date) {
//                                     return null;
//                                 }
//                                 return String(
//                                     entry.attendance_date
//                                 ).substring(0, 4);
//                             })
//                             .filter(Boolean)
//                     )
//                 ]
//                 .filter(function (year) {
//                     return parseInt(year, 10) >= currentYear - 5;
//                 })
//                 .sort(function (a, b) {
//                     return parseInt(b, 10) - parseInt(a, 10);
//                 });
//                 // Ensure current year is available
//                 if (!years.includes(String(currentYear))) {
//                     years.unshift(String(currentYear));
//                 }
//                 yearField.df.options = years.join("\n");
//                 yearField.refresh();
//                 // Keep the selected year if valid; otherwise use current year
//                 const selectedYear = String(
//                     frappe.query_report.get_filter_value("year") || ""
//                 );
//                 if (years.includes(selectedYear)) {
//                     yearField.set_input(selectedYear);
//                 } else {
//                     yearField.set_input(String(currentYear));
//                 }
//             }
//         }
//     });
// }



const REPORT_NAME = "Monthly Attendance Summary";
const PREF_METHOD =
    "at_biometric_integration.at_biometric_integration.report.monthly_attendance_summary.monthly_attendance_summary";

let savedColumnOrder = [];
let columnEventsAttached = false;

frappe.query_reports[REPORT_NAME] = {
    filters: [
        {
            fieldname: "month",
            label: "Month",
            fieldtype: "Select",
            options: [
                "",
                "January", "February", "March", "April",
                "May", "June", "July", "August",
                "September", "October", "November", "December"
            ].join("\n"),
            on_change: function () {
                setDatesFromMonthYear();
                frappe.query_report.refresh();
            }
        },
        {
            fieldname: "year",
            label: "Year",
            fieldtype: "Select",
            on_change: function () {
                setDatesFromMonthYear();
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
        }
    ],

    onload: async function (report) {
        await loadSavedColumnOrder();

        // Apply saved order whenever columns are prepared,
        // including after report refresh.
        if (!report._column_order_patched) {
            const originalPrepareColumns =
                report.prepare_columns.bind(report);

            report.prepare_columns = function (columns) {
                const prepared = originalPrepareColumns(columns);
                return applySavedColumnOrder(prepared);
            };

            report._column_order_patched = true;
        }

        updateYearOptions();
        setCurrentMonthAndYear();
    },

    get_datatable_options: function (options) {
        options.columns = applySavedColumnOrder(options.columns);

        options.events = options.events || {};

        options.events.onSwitchColumn = function () {
            // Wait until DataTable finishes updating its column order.
            setTimeout(function () {
                saveCurrentColumnOrder();
            }, 100);
        };

        columnEventsAttached = true;

        return options;
    }
};


// Apply saved order to columns
function applySavedColumnOrder(columns) {
    if (!savedColumnOrder.length || !columns) {
        return columns;
    }

    const orderMap = new Map(
        savedColumnOrder.map((fieldname, index) => [
            fieldname,
            index
        ])
    );

    return [...columns].sort(function (a, b) {
        const aIndex = orderMap.has(a.fieldname)
            ? orderMap.get(a.fieldname)
            : Number.MAX_SAFE_INTEGER;

        const bIndex = orderMap.has(b.fieldname)
            ? orderMap.get(b.fieldname)
            : Number.MAX_SAFE_INTEGER;

        return aIndex - bIndex;
    });
}


// Load current user's saved column order
async function loadSavedColumnOrder() {
    try {
        const response = await frappe.call({
            method: PREF_METHOD + ".get_column_order"
        });

        if (response && response.message) {
            savedColumnOrder = response.message;
        } else {
            savedColumnOrder = [];
        }
    } catch (error) {
        console.error(
            "Unable to load saved column order:",
            error
        );
        savedColumnOrder = [];
    }
}


// Save current column order for logged-in user
function saveCurrentColumnOrder() {
    const report = frappe.query_report;

    if (
        !report ||
        report.report_name !== REPORT_NAME ||
        !report.datatable ||
        !report.datatable.datamanager
    ) {
        return;
    }

    const columns = report.datatable.datamanager.getColumns(true);

    const order = columns
        .map(column => column.id || column.fieldname)
        .filter(Boolean);

    if (!order.length) {
        return;
    }

    savedColumnOrder = order;

    frappe.call({
        method: PREF_METHOD + ".save_column_order",
        args: {
            column_order: JSON.stringify(order)
        }
    }).catch(function (error) {
        console.error(
            "Unable to save column order:",
            error
        );
    });
}


// Format date as YYYY-MM-DD
function formatDateToYYYYMMDD(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}


// Set From Date and To Date according to selected Month and Year
function setDatesFromMonthYear() {
    const month = frappe.query_report.get_filter_value("month");
    const year = frappe.query_report.get_filter_value("year");

    if (!month || !year) {
        return;
    }

    const monthMap = {
        "January": 0,
        "February": 1,
        "March": 2,
        "April": 3,
        "May": 4,
        "June": 5,
        "July": 6,
        "August": 7,
        "September": 8,
        "October": 9,
        "November": 10,
        "December": 11
    };

    if (monthMap[month] === undefined) {
        return;
    }

    const start = new Date(
        Number(year),
        monthMap[month],
        1
    );

    const end = new Date(
        Number(year),
        monthMap[month] + 1,
        0
    );

    frappe.query_report.set_filter_value(
        "from_date",
        formatDateToYYYYMMDD(start)
    );

    frappe.query_report.set_filter_value(
        "to_date",
        formatDateToYYYYMMDD(end)
    );
}


// Set current Month and Year by default
function setCurrentMonthAndYear() {
    const currentDate = new Date();

    const currentMonth = currentDate.toLocaleString(
        "en-US",
        { month: "long" }
    );

    const currentYear = String(currentDate.getFullYear());

    frappe.query_report.get_filter("month").set_input(currentMonth);
    frappe.query_report.get_filter("year").set_input(currentYear);

    setDatesFromMonthYear();

    frappe.query_report.refresh();
}


// Fetch available Attendance years
function updateYearOptions() {
    const yearField = frappe.query_report.get_filter("year");
    const currentYear = new Date().getFullYear();

    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Attendance",
            fields: ["attendance_date"],
            filters: {
                attendance_date: ["is", "set"]
            },
            limit_page_length: 0,
            order_by: "attendance_date desc"
        },

        callback: function (response) {
            if (response && response.message) {
                const years = [
                    ...new Set(
                        response.message
                            .map(function (entry) {
                                if (!entry.attendance_date) {
                                    return null;
                                }

                                return String(
                                    entry.attendance_date
                                ).substring(0, 4);
                            })
                            .filter(Boolean)
                    )
                ]
                .filter(function (year) {
                    return parseInt(year, 10) >= currentYear - 5;
                })
                .sort(function (a, b) {
                    return parseInt(b, 10) - parseInt(a, 10);
                });

                if (!years.includes(String(currentYear))) {
                    years.unshift(String(currentYear));
                }

                yearField.df.options = years.join("\n");
                yearField.refresh();

                const selectedYear = String(
                    frappe.query_report.get_filter_value("year") || ""
                );

                if (years.includes(selectedYear)) {
                    yearField.set_input(selectedYear);
                } else {
                    yearField.set_input(String(currentYear));
                }
            }
        }
    });
}