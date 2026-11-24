# import frappe
# import json
# from frappe.utils import getdate, nowdate
# from datetime import datetime, timedelta
# import calendar


# def format_number(val):
#     if val is None or val in [0, 0.0, "0", "00", "0.0", "00.00"]:
#         return "-"

#     if isinstance(val, int):
#         return f"{val:02d}"

#     if isinstance(val, float):
#         return f"{val:05.2f}"

#     return val


# def execute(filters=None):
#     try:
#         filters = frappe._dict(filters or {})
#         result = []

#         columns = [
#             {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 160},
#             {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
#             {"label": "Present", "fieldname": "present", "fieldtype": "Data", "width": 100},
#             {"label": "Leave", "fieldname": "leave", "fieldtype": "Data", "width": 100},
#             {"label": "No Of Weekends", "fieldname": "no_of_weekends", "fieldtype": "Data", "width": 100},
#             {"label": "No Of Holidays", "fieldname": "no_of_holidays", "fieldtype": "Data", "width": 100},
#             {"label": "Absent", "fieldname": "absent", "fieldtype": "Data", "width": 100},
#             {"label": "Half Day", "fieldname": "half_day", "fieldtype": "Data", "width": 100},
#             {"label": "Absent-Half Day", "fieldname": "absent_half_day", "fieldtype": "Data", "width": 130},
#             {"label": "Paid Leave", "fieldname": "paid_leave", "fieldtype": "Data", "width": 140},
#             {"label": "Unpaid Leave", "fieldname": "unpaid_leave", "fieldtype": "Data", "width": 140},
#             {"label": "Work From Home", "fieldname": "wfh", "fieldtype": "Data", "width": 120},
#             {"label": "Total Absent", "fieldname": "total_absent", "fieldtype": "Data", "width": 100},
#             {"label": "Total Working Days", "fieldname": "total_working_days", "fieldtype": "Data", "width": 100},
#             {"label": "Payment Days", "fieldname": "payment_days", "fieldtype": "Data", "width": 100},
#         ]

#         # 1. Login User Permission
#         current_user = frappe.session.user
#         user_roles = frappe.get_roles(current_user)

#         allowed_all_employee_roles = {
#             "System Manager",
#             "HR Manager",
#             "HR User"
#         }

#         is_admin = (
#             current_user == "Administrator"
#             or bool(
#                 set(user_roles).intersection(
#                     allowed_all_employee_roles
#                 )
#             )
#         )

#         logged_in_employee = None

#         if not is_admin:
#             logged_in_employee = frappe.db.get_value(
#                 "Employee",
#                 {"user_id": current_user},
#                 "name"
#             )

#             if not logged_in_employee:
#                 frappe.throw(
#                     "Your User ID is not linked with any Employee record. "
#                     "Please contact HR."
#                 )

#             # Employee cannot access another employee's report
#             if (
#                 filters.get("employee")
#                 and filters.get("employee") != logged_in_employee
#             ):
#                 frappe.throw(
#                     "You are not permitted to view another employee's attendance."
#                 )

#             # Force logged-in employee
#             filters.employee = logged_in_employee

#         # 2. Date Filter Logic
#         today = getdate(nowdate())

#         if filters.get("from_date") and filters.get("to_date"):
#             from_date = getdate(filters.get("from_date"))
#             to_date = getdate(filters.get("to_date"))

#         else:
#             month_str = filters.get("month")
#             year = int(filters.get("year") or today.year)

#             if month_str:
#                 month_map = {
#                     "January": 1,
#                     "February": 2,
#                     "March": 3,
#                     "April": 4,
#                     "May": 5,
#                     "June": 6,
#                     "July": 7,
#                     "August": 8,
#                     "September": 9,
#                     "October": 10,
#                     "November": 11,
#                     "December": 12,
#                 }

#                 month = month_map.get(month_str)

#                 if not month:
#                     frappe.throw("Invalid month selected")

#                 from_date = datetime(year, month, 1).date()
#                 to_date = datetime(
#                     year,
#                     month,
#                     calendar.monthrange(year, month)[1]
#                 ).date()

#             else:
#                 frappe.throw(
#                     "Please select both From Date and To Date, "
#                     "or select Month and Year"
#                 )

#         if from_date > to_date:
#             frappe.throw("From Date cannot be greater than To Date")

#         # Total calendar days in selected date range (inclusive)
#         total_date_range_days = (to_date - from_date).days + 1

#         # 3. Fetch Attendance Records
#         attendance_filters = [from_date, to_date]

#         attendance_query = """
#             SELECT
#                 employee,
#                 attendance_date,
#                 status,
#                 leave_type
#             FROM `tabAttendance`
#             WHERE
#                 attendance_date BETWEEN %s AND %s
#                 AND docstatus = 1
#         """

#         if filters.get("employee"):
#             attendance_query += " AND employee = %s"
#             attendance_filters.append(filters.get("employee"))

#         attendance = frappe.db.sql(
#             attendance_query,
#             tuple(attendance_filters),
#             as_dict=True
#         )

#         attendance_map = {}

#         for att in attendance:
#             attendance_map.setdefault(att.employee, {})[
#                 getdate(att.attendance_date)
#             ] = att

#         # 4. Fetch Active Employees
#         emp_filters = {
#             "status": "Active"
#         }

#         if filters.get("employee"):
#             emp_filters["name"] = filters.get("employee")

#         if filters.get("company"):
#             emp_filters["company"] = filters.get("company")

#         employees = frappe.get_all(
#             "Employee",
#             fields=[
#                 "name",
#                 "employee_name",
#                 "holiday_list",
#                 "company"
#             ],
#             filters=emp_filters,
#             order_by="employee_name asc"
#         )

#         # 5. Fetch Leave Type Classification
#         leave_type_map = {}

#         leave_types = frappe.get_all(
#             "Leave Type",
#             fields=["name", "is_lwp"]
#         )

#         for leave_type in leave_types:
#             leave_type_name = (leave_type.name or "").strip().lower()

#             if leave_type_name == "paid leave":
#                 leave_type_map[leave_type.name] = "paid"

#             elif leave_type.is_lwp:
#                 leave_type_map[leave_type.name] = "unpaid"

#             else:
#                 leave_type_map[leave_type.name] = "normal"

#         # 6. Initialize Grand Totals
#         totals = {
#             "employee": "Total",
#             "present": 0,
#             "leave": 0,
#             "no_of_weekends": 0,
#             "no_of_holidays": 0,
#             "absent": 0,
#             "half_day": 0,
#             "absent_half_day": 0,
#             "paid_leave": 0,
#             "unpaid_leave": 0,
#             "wfh": 0,
#             "total_absent": 0,
#             "total_working_days": 0,
#             "payment_days": 0,
#         }

#         all_dates = [
#             from_date + timedelta(days=i)
#             for i in range(total_date_range_days)
#         ]

#         # 7. Employee-wise Attendance Summary
#         for emp in employees:

#             emp_attendance = attendance_map.get(emp.name, {})

#             weekend_dates = {
#                 date for date in all_dates
#                 if date.weekday() in [5, 6]
#             }

#             # 8. Fetch Holidays
#             holiday_dates = set()

#             if emp.holiday_list:
#                 holidays = frappe.get_all(
#                     "Holiday",
#                     fields=["holiday_date"],
#                     filters={
#                         "parent": emp.holiday_list,
#                         "holiday_date": [
#                             "between",
#                             [from_date, to_date]
#                         ]
#                     }
#                 )

#                 holiday_dates = {
#                     getdate(holiday.holiday_date)
#                     for holiday in holidays
#                 }

#             final_holidays = holiday_dates - weekend_dates

#             # 9. Initialize Attendance Counts
#             present = 0
#             leave = 0
#             absent = 0
#             half_day = 0
#             absent_half_day = 0
#             wfh = 0
#             paid_leave = 0
#             unpaid_leave = 0

#             # 10. Count Actual Attendance Records
#             for attendance_date in all_dates:

#                 record = emp_attendance.get(attendance_date)

#                 if not record:
#                     continue

#                 status = (record.status or "").strip()
#                 leave_type = record.leave_type

#                 if status == "Present":
#                     present += 1

#                 elif status == "Absent":
#                     absent += 1

#                 elif status == "Half Day":
#                     half_day += 1

#                 elif status == "Absent-Half Day":
#                     absent_half_day += 1

#                 elif status == "Work From Home":
#                     wfh += 1

#                 elif status == "On Leave":
#                     # Every On Leave record counts in Leave
#                     leave += 1

#                     # Paid and Unpaid are also counted separately
#                     leave_category = leave_type_map.get(
#                         leave_type, "normal"
#                     )

#                     if leave_category == "paid":
#                         paid_leave += 1

#                     elif leave_category == "unpaid":
#                         unpaid_leave += 1

#             # 11. Employee Summary Row
#             row = {
#                 "employee": emp.name,
#                 "employee_name": emp.employee_name,

#                 "present": present,
#                 "leave": leave,

#                 "no_of_weekends": len(weekend_dates),
#                 "no_of_holidays": len(final_holidays),

#                 "absent": absent,
#                 "half_day": half_day,
#                 "absent_half_day": absent_half_day,

#                 "paid_leave": paid_leave,
#                 "unpaid_leave": unpaid_leave,

#                 "wfh": wfh,

#                 # Only Absent + Absent-Half Day
#                 "total_absent": (
#                     absent
#                     + absent_half_day
#                 ),

#                 # Total calendar days in selected date range
#                 "total_working_days": total_date_range_days,

#                 # Payment Days calculation
#                 "payment_days": (
#                     paid_leave
#                     + len(final_holidays)
#                     + len(weekend_dates)
#                     + present
#                     + (half_day * 0.5)
#                     + wfh
#                     + (absent * 0.5)
#                     + (absent_half_day * 0.5)
#                 ),
#             }

#             # 12. Update Grand Totals
#             for key in totals:
#                 if key != "employee":
#                     totals[key] += row.get(key, 0)

#             formatted_row = {}

#             for col in columns:
#                 fieldname = col["fieldname"]
#                 value = row.get(fieldname)

#                 if fieldname == "employee":
#                     formatted_row[fieldname] = value
#                 else:
#                     formatted_row[fieldname] = format_number(value)

#             result.append(formatted_row)

#         # 13. Append Grand Total
#         if result:
#             formatted_totals = {}

#             for col in columns:
#                 fieldname = col["fieldname"]
#                 value = totals.get(fieldname)

#                 if fieldname == "employee":
#                     formatted_totals[fieldname] = value
#                 else:
#                     formatted_totals[fieldname] = format_number(value)

#             result.append(formatted_totals)

#         return columns, result

#     except Exception:
#         frappe.log_error(
#             frappe.get_traceback(),
#             "Monthly Attendance Summary Error"
#         )
#         raise


# # ==========================================================
# # USER-WISE COLUMN ORDER PREFERENCE
# # ==========================================================

# COLUMN_ORDER_DEFAULT_KEY = "monthly_attendance_summary_column_order"

# ALLOWED_REPORT_COLUMNS = {
#     "employee",
#     "employee_name",
#     "present",
#     "leave",
#     "no_of_weekends",
#     "no_of_holidays",
#     "absent",
#     "half_day",
#     "absent_half_day",
#     "paid_leave",
#     "unpaid_leave",
#     "wfh",
#     "total_absent",
#     "total_working_days",
#     "payment_days",
# }


# @frappe.whitelist()
# def get_column_order():
#     """Return the logged-in user's saved column order."""

#     if frappe.session.user == "Guest":
#         frappe.throw("Please login to access column preferences.")

#     saved_order = frappe.defaults.get_user_default(
#         COLUMN_ORDER_DEFAULT_KEY
#     )

#     if not saved_order:
#         return []

#     try:
#         column_order = json.loads(saved_order)

#         if not isinstance(column_order, list):
#             return []

#         return [
#             fieldname
#             for fieldname in column_order
#             if fieldname in ALLOWED_REPORT_COLUMNS
#         ]

#     except (ValueError, TypeError):
#         return []


# @frappe.whitelist()
# def save_column_order(column_order):
#     """Save column order separately for the logged-in user."""

#     if frappe.session.user == "Guest":
#         frappe.throw("Please login to save column preferences.")

#     try:
#         if isinstance(column_order, str):
#             column_order = json.loads(column_order)

#         if not isinstance(column_order, list):
#             frappe.throw("Invalid column order.")

#         valid_order = []

#         for fieldname in column_order:
#             if (
#                 isinstance(fieldname, str)
#                 and fieldname in ALLOWED_REPORT_COLUMNS
#                 and fieldname not in valid_order
#             ):
#                 valid_order.append(fieldname)

#         if not valid_order:
#             frappe.throw("No valid report columns received.")

#         frappe.defaults.set_user_default(
#             COLUMN_ORDER_DEFAULT_KEY,
#             json.dumps(valid_order)
#         )

#         return {
#             "success": True,
#             "message": "Column order saved successfully."
#         }

#     except (ValueError, TypeError):
#         frappe.throw("Invalid column order format.")









import frappe
import json
from frappe.utils import getdate, nowdate
from datetime import datetime, timedelta
import calendar


def format_number(val):
    if val is None or val in [0, 0.0, "0", "00", "0.0", "00.00"]:
        return "-"

    if isinstance(val, int):
        return f"{val:02d}"

    if isinstance(val, float):
        return f"{val:05.2f}"

    return val


def execute(filters=None):
    try:
        filters = frappe._dict(filters or {})
        result = []

        columns = [
            {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 160},
            {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
            {"label": "Present", "fieldname": "present", "fieldtype": "Data", "width": 100},
            {"label": "Leave", "fieldname": "leave", "fieldtype": "Data", "width": 100},
            {"label": "No Of Weekends", "fieldname": "no_of_weekends", "fieldtype": "Data", "width": 100},
            {"label": "No Of Holidays", "fieldname": "no_of_holidays", "fieldtype": "Data", "width": 100},
            {"label": "Absent", "fieldname": "absent", "fieldtype": "Data", "width": 100},
            {"label": "Half Day", "fieldname": "half_day", "fieldtype": "Data", "width": 100},
            {"label": "Absent-Half Day", "fieldname": "absent_half_day", "fieldtype": "Data", "width": 130},
            {"label": "Paid Leave", "fieldname": "paid_leave", "fieldtype": "Data", "width": 140},
            {"label": "Unpaid Leave", "fieldname": "unpaid_leave", "fieldtype": "Data", "width": 140},
            {"label": "Work From Home", "fieldname": "wfh", "fieldtype": "Data", "width": 120},
            {"label": "Total Absent", "fieldname": "total_absent", "fieldtype": "Data", "width": 100},
            {"label": "Total Working Days", "fieldname": "total_working_days", "fieldtype": "Data", "width": 100},
            {"label": "Payment Days", "fieldname": "payment_days", "fieldtype": "Data", "width": 100},
        ]

        # 1. Login User Permission
        current_user = frappe.session.user
        user_roles = frappe.get_roles(current_user)

        allowed_all_employee_roles = {
            "System Manager",
            "HR Manager",
            "HR User"
        }

        is_admin = (
            current_user == "Administrator"
            or bool(
                set(user_roles).intersection(
                    allowed_all_employee_roles
                )
            )
        )

        logged_in_employee = None

        if not is_admin:
            logged_in_employee = frappe.db.get_value(
                "Employee",
                {"user_id": current_user},
                "name"
            )

            if not logged_in_employee:
                frappe.throw(
                    "Your User ID is not linked with any Employee record. "
                    "Please contact HR."
                )

            # Employee cannot access another employee's report
            if (
                filters.get("employee")
                and filters.get("employee") != logged_in_employee
            ):
                frappe.throw(
                    "You are not permitted to view another employee's attendance."
                )

            # Force logged-in employee
            filters.employee = logged_in_employee

        # 2. Date Filter Logic
        today = getdate(nowdate())

        if filters.get("from_date") and filters.get("to_date"):
            from_date = getdate(filters.get("from_date"))
            to_date = getdate(filters.get("to_date"))

        else:
            month_str = filters.get("month")
            year = int(filters.get("year") or today.year)

            if month_str:
                month_map = {
                    "January": 1,
                    "February": 2,
                    "March": 3,
                    "April": 4,
                    "May": 5,
                    "June": 6,
                    "July": 7,
                    "August": 8,
                    "September": 9,
                    "October": 10,
                    "November": 11,
                    "December": 12,
                }

                month = month_map.get(month_str)

                if not month:
                    frappe.throw("Invalid month selected")

                from_date = datetime(year, month, 1).date()
                to_date = datetime(
                    year,
                    month,
                    calendar.monthrange(year, month)[1]
                ).date()

            else:
                frappe.throw(
                    "Please select both From Date and To Date, "
                    "or select Month and Year"
                )

        if from_date > to_date:
            frappe.throw("From Date cannot be greater than To Date")

        # Total calendar days in selected date range (inclusive)
        total_date_range_days = (to_date - from_date).days + 1

        # 3. Fetch Attendance Records
        attendance_filters = [from_date, to_date]

        attendance_query = """
            SELECT
                employee,
                attendance_date,
                status,
                leave_type
            FROM `tabAttendance`
            WHERE
                attendance_date BETWEEN %s AND %s
                AND docstatus = 1
        """

        if filters.get("employee"):
            attendance_query += " AND employee = %s"
            attendance_filters.append(filters.get("employee"))

        attendance = frappe.db.sql(
            attendance_query,
            tuple(attendance_filters),
            as_dict=True
        )

        attendance_map = {}

        for att in attendance:
            attendance_map.setdefault(att.employee, {})[
                getdate(att.attendance_date)
            ] = att

        # 4. Fetch Active Employees
        emp_filters = {
            "status": "Active"
        }

        if filters.get("employee"):
            emp_filters["name"] = filters.get("employee")

        if filters.get("company"):
            emp_filters["company"] = filters.get("company")

        employees = frappe.get_all(
            "Employee",
            fields=[
                "name",
                "employee_name",
                "holiday_list",
                "company"
            ],
            filters=emp_filters,
            order_by="employee_name asc"
        )

        # 5. Fetch Leave Type Classification
        # is_lwp checked   = Unpaid Leave
        # is_lwp unchecked = Paid Leave

        leave_type_map = {}

        leave_types = frappe.get_all(
            "Leave Type",
            fields=["name", "is_lwp"]
        )

        for leave_type in leave_types:
            if leave_type.is_lwp:
                leave_type_map[leave_type.name] = "unpaid"
            else:
                leave_type_map[leave_type.name] = "paid"

        # 6. Initialize Grand Totals
        totals = {
            "employee": "Total",
            "present": 0,
            "leave": 0,
            "no_of_weekends": 0,
            "no_of_holidays": 0,
            "absent": 0,
            "half_day": 0,
            "absent_half_day": 0,
            "paid_leave": 0,
            "unpaid_leave": 0,
            "wfh": 0,
            "total_absent": 0,
            "total_working_days": 0,
            "payment_days": 0,
        }

        all_dates = [
            from_date + timedelta(days=i)
            for i in range(total_date_range_days)
        ]

        # 7. Employee-wise Attendance Summary
        for emp in employees:

            emp_attendance = attendance_map.get(emp.name, {})

            weekend_dates = {
                date for date in all_dates
                if date.weekday() in [5, 6]
            }

            # 8. Fetch Holidays
            holiday_dates = set()

            if emp.holiday_list:
                holidays = frappe.get_all(
                    "Holiday",
                    fields=["holiday_date"],
                    filters={
                        "parent": emp.holiday_list,
                        "holiday_date": [
                            "between",
                            [from_date, to_date]
                        ]
                    }
                )

                holiday_dates = {
                    getdate(holiday.holiday_date)
                    for holiday in holidays
                }

            final_holidays = holiday_dates - weekend_dates

            # 9. Initialize Attendance Counts
            present = 0
            leave = 0
            absent = 0
            half_day = 0
            absent_half_day = 0
            wfh = 0
            paid_leave = 0
            unpaid_leave = 0

            # 10. Count Actual Attendance Records
            for attendance_date in all_dates:

                record = emp_attendance.get(attendance_date)

                if not record:
                    continue

                status = (record.status or "").strip()
                leave_type = record.leave_type

                if status == "Present":
                    present += 1

                elif status == "Absent":
                    absent += 1

                elif status == "Half Day":
                    half_day += 1

                elif status == "Absent-Half Day":
                    absent_half_day += 1

                elif status == "Work From Home":
                    wfh += 1

                elif status == "On Leave":
                    # Every On Leave record counts in Leave
                    leave += 1

                    # Classify using Leave Type is_lwp checkbox
                    leave_category = leave_type_map.get(
                        leave_type
                    )

                    if leave_category == "paid":
                        paid_leave += 1

                    elif leave_category == "unpaid":
                        unpaid_leave += 1

            # 11. Employee Summary Row
            row = {
                "employee": emp.name,
                "employee_name": emp.employee_name,

                "present": present,
                "leave": leave,

                "no_of_weekends": len(weekend_dates),
                "no_of_holidays": len(final_holidays),

                "absent": absent,
                "half_day": half_day,
                "absent_half_day": absent_half_day,

                "paid_leave": paid_leave,
                "unpaid_leave": unpaid_leave,

                "wfh": wfh,

                # Only Absent + Absent-Half Day
                "total_absent": (
                    absent
                    + absent_half_day
                ),

                # Total calendar days in selected date range
                "total_working_days": total_date_range_days,

                # Payment Days calculation
                "payment_days": (
                    paid_leave
                    + len(final_holidays)
                    + len(weekend_dates)
                    + present
                    + (half_day * 0.5)
                    + wfh
                    + (absent * 0.5)
                    + (absent_half_day * 0.5)
                ),
            }

            # 12. Update Grand Totals
            for key in totals:
                if key != "employee":
                    totals[key] += row.get(key, 0)

            formatted_row = {}

            for col in columns:
                fieldname = col["fieldname"]
                value = row.get(fieldname)

                if fieldname == "employee":
                    formatted_row[fieldname] = value
                else:
                    formatted_row[fieldname] = format_number(value)

            result.append(formatted_row)

        # 13. Append Grand Total
        if result:
            formatted_totals = {}

            for col in columns:
                fieldname = col["fieldname"]
                value = totals.get(fieldname)

                if fieldname == "employee":
                    formatted_totals[fieldname] = value
                else:
                    formatted_totals[fieldname] = format_number(value)

            result.append(formatted_totals)

        return columns, result

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Monthly Attendance Summary Error"
        )
        raise


# ==========================================================
# USER-WISE COLUMN ORDER PREFERENCE
# ==========================================================

COLUMN_ORDER_DEFAULT_KEY = "monthly_attendance_summary_column_order"

ALLOWED_REPORT_COLUMNS = {
    "employee",
    "employee_name",
    "present",
    "leave",
    "no_of_weekends",
    "no_of_holidays",
    "absent",
    "half_day",
    "absent_half_day",
    "paid_leave",
    "unpaid_leave",
    "wfh",
    "total_absent",
    "total_working_days",
    "payment_days",
}


@frappe.whitelist()
def get_column_order():
    """Return the logged-in user's saved column order."""

    if frappe.session.user == "Guest":
        frappe.throw("Please login to access column preferences.")

    saved_order = frappe.defaults.get_user_default(
        COLUMN_ORDER_DEFAULT_KEY
    )

    if not saved_order:
        return []

    try:
        column_order = json.loads(saved_order)

        if not isinstance(column_order, list):
            return []

        return [
            fieldname
            for fieldname in column_order
            if fieldname in ALLOWED_REPORT_COLUMNS
        ]

    except (ValueError, TypeError):
        return []


@frappe.whitelist()
def save_column_order(column_order):
    """Save column order separately for the logged-in user."""

    if frappe.session.user == "Guest":
        frappe.throw("Please login to save column preferences.")

    try:
        if isinstance(column_order, str):
            column_order = json.loads(column_order)

        if not isinstance(column_order, list):
            frappe.throw("Invalid column order.")

        valid_order = []

        for fieldname in column_order:
            if (
                isinstance(fieldname, str)
                and fieldname in ALLOWED_REPORT_COLUMNS
                and fieldname not in valid_order
            ):
                valid_order.append(fieldname)

        if not valid_order:
            frappe.throw("No valid report columns received.")

        frappe.defaults.set_user_default(
            COLUMN_ORDER_DEFAULT_KEY,
            json.dumps(valid_order)
        )

        return {
            "success": True,
            "message": "Column order saved successfully."
        }

    except (ValueError, TypeError):
        frappe.throw("Invalid column order format.")