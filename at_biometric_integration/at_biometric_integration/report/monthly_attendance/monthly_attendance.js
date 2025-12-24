frappe.query_reports["Monthly Attendance"] = {
    "filters": [
        {
            "fieldname": "period",
            "label": "Period",
            "fieldtype": "Select",
            "options": "Daily\nWeekly\nMonthly",
            "default": "Daily",
            "reqd": 1,
            "on_change": function() {
                updateVisibility();
                updateYearOptions();
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "months",
            "label": "Month",
            "fieldtype": "Select",
            "options": "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
            "on_change": function() {
                updateVisibility();
                updateMonthOptions();
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "year",
            "label": "Year",
            "fieldtype": "Select"
        },
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date"
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date"
        },
        {
            "fieldname": "status",
            "label": "Status",
            "fieldtype": "Select",
            "options": "\nPresent\nAbsent\nHalf Day\nOn Leave\nWork From Home"
          },
          {
            "fieldname": "employee",
            "label": "Employee",
            "fieldtype": "Link",
            "options": "Employee"
          },
          {
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company"
          },
          {
            "fieldname": "department",
            "label": "Department",
            "fieldtype": "Link",
            "options": "Department"
          }
    ],

    // Onload function for initial setup
    onload: function(report) {
        updateVisibility();
        updateYearOptions();
        updateMonthOptions();
        frappe.query_report.refresh();
    }
};

// Handles showing/hiding fields based on Period
function updateVisibility() {
    let period = frappe.query_report.get_filter_value("period");
    let months = frappe.query_report.get_filter("months");
    let year = frappe.query_report.get_filter("year");
    if (period === "Monthly") {
        months.df.hidden = 0;
        months.refresh();
        year.df.hidden = 0;
        year.refresh();
    } else {
        months.df.hidden = 1;
        months.refresh();
        year.df.hidden = 1;
        year.refresh();
    }
}


function updateYearOptions() {
    let yearField = frappe.query_report.get_filter("year");
    let period = frappe.query_report.get_filter_value("period");
    let currentYear = new Date().getFullYear();
    let years = [];
    // Query the Attendance doctype to get distinct years
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Attendance",
            fields: ["YEAR(attendance_date) as year"],
            filters: {},
            group_by: "YEAR(attendance_date)",
            order_by: "year desc"
        },
        callback: function(response) {
            if (response && response.message) {
                // Add the distinct years to the years array
                years = response.message.map(yearObj => yearObj.year.toString());

                // If period is "Monthly", show years from the last 5 years
                if (period === "Monthly") {
                    let filteredYears = years.filter(year => parseInt(year) >= (currentYear - 5));
                    yearField.df.options = filteredYears.join('\n');
                    yearField.set_input(currentYear.toString());
                } 
                // else {
                //     // If period is not "Monthly", show years from the last 2 years
                //     let filteredYears = years.filter(year => parseInt(year) >= (currentYear - 1) && parseInt(year) <= (currentYear + 1));
                //     yearField.df.options = filteredYears.join('\n');
                //     yearField.set_input(currentYear.toString());
                // }

                yearField.refresh();
            }
        }
    });
}

function updateMonthOptions(){
   let currentMonth = new Date().getMonth();
   return currentMonth;
}