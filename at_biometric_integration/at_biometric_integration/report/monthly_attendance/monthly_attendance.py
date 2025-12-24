import frappe
from frappe.utils import getdate, nowdate, add_days
from datetime import datetime


# --------------------------------------------------
# Helper: Get earliest IN and last OUT from checkins
# --------------------------------------------------
def get_checkin_times(employee, date):
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]],
        },
        fields=["time"],
        order_by="time",
    )

    if not checkins:
        return None, None

    times = [c.time for c in checkins]
    return min(times), max(times)


# --------------------------------------------------
# Helper: TOTAL WORKING HOURS (First IN → Last OUT)
# --------------------------------------------------
def total_working_duration(employee, date):
    first_in, last_out = get_checkin_times(employee, date)

    if not first_in or not last_out or last_out <= first_in:
        return "-"

    total_seconds = (last_out - first_in).total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)

    return f"{hours:02d}:{minutes:02d}"


# --------------------------------------------------
# Helper: Check Leave on Date
# --------------------------------------------------
def get_leave_on_date(employee, date):
    leave = frappe.db.sql(
        """
        SELECT leave_type
        FROM `tabLeave Application`
        WHERE employee = %s
          AND docstatus = 1
          AND %s BETWEEN from_date AND to_date
        LIMIT 1
        """,
        (employee, date),
        as_dict=True,
    )

    return leave[0].leave_type if leave else None


# --------------------------------------------------
# MAIN REPORT
# --------------------------------------------------
def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = [
        {"label": "Employee Code", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 140},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "Shift", "fieldname": "shift", "fieldtype": "Data", "width": 100},
        {"label": "Date", "fieldname": "date", "fieldtype": "Data", "width": 110},
        {"label": "In Time", "fieldname": "in_time", "fieldtype": "Data", "width": 90},
        {"label": "Out Time", "fieldname": "out_time", "fieldtype": "Data", "width": 90},
        {"label": "Total Working Hours", "fieldname": "total_working_hours", "fieldtype": "Data", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": "Remarks", "fieldname": "remark", "fieldtype": "Data", "width": 150},
    ]

    # --------------------------
    # Date Range
    # --------------------------
    from_date = getdate(filters.get("from_date") or nowdate())
    to_date = getdate(filters.get("to_date") or nowdate())

    # --------------------------
    # Employees
    # --------------------------
    employees = frappe.get_all(
        "Employee",
        fields=["name", "employee_name"]
    )

    data = []

    # --------------------------
    # MAIN LOOP (Employee × Date)
    # --------------------------
    for emp in employees:
        current_date = from_date

        while current_date <= to_date:
            attendance = frappe.db.get_value(
                "Attendance",
                {
                    "employee": emp.name,
                    "attendance_date": current_date,
                },
                ["shift", "status"],
                as_dict=True,
            )

            leave_type = get_leave_on_date(emp.name, current_date)
            in_time, out_time = get_checkin_times(emp.name, current_date)

            if attendance:
                data.append({
                    "employee": emp.name,
                    "employee_name": emp.employee_name,
                    "shift": attendance.shift or "",
                    "date": current_date.strftime("%d-%b-%Y"),
                    "in_time": in_time.strftime("%H:%M") if in_time else "-",
                    "out_time": out_time.strftime("%H:%M") if out_time else "-",
                    "total_working_hours": total_working_duration(emp.name, current_date),
                    "status": attendance.status,
                    "remark": "",
                })

            elif leave_type:
                data.append({
                    "employee": emp.name,
                    "employee_name": emp.employee_name,
                    "shift": "",
                    "date": current_date.strftime("%d-%b-%Y"),
                    "in_time": "-",
                    "out_time": "-",
                    "total_working_hours": "-",
                    "status": f"Leave ({leave_type})",
                    "remark": "",
                })

            else:
                data.append({
                    "employee": emp.name,
                    "employee_name": emp.employee_name,
                    "shift": "",
                    "date": current_date.strftime("%d-%b-%Y"),
                    "in_time": "-",
                    "out_time": "-",
                    "total_working_hours": "-",
                    "status": "Absent",
                    "remark": "",
                })

            current_date = add_days(current_date, 1)

        # ✅ ONE EMPTY ROW AFTER EACH EMPLOYEE
        data.append({})

    return columns, data

