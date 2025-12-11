import frappe
from frappe.utils import getdate, nowdate
from datetime import datetime, timedelta

def get_checkin_times(employee, date):
    """Return earliest and latest checkin times for the employee on the given date."""
    checkins = frappe.get_all("Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
        },
        fields=["time"],
        order_by="time"
    )
    if not checkins:
        return None, None
    times = [c.time for c in checkins]
    return min(times), max(times)

def actual_working_duration(employee, date):
    """Calculate actual working hours based on alternating IN/OUT checkins and return in HH:MM format."""
    checkins = frappe.get_all("Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
        },
        fields=["time"],
        order_by="time"
    )
    total_duration = 0.0
    times = [c.time for c in checkins]
    for i in range(0, len(times) - 1, 2):
        in_time = times[i]
        out_time = times[i + 1]
        if out_time > in_time:
            total_duration += (out_time - in_time).total_seconds()
    if total_duration:
        hours = int(total_duration // 3600)
        minutes = int((total_duration % 3600) // 60)
        return f"{hours:02d}:{minutes:02d}"
    return "-"

def get_shift_duration(shift_start, shift_end):
    try:
        shift_start_dt = datetime.strptime(str(shift_start), "%H:%M:%S")
        shift_end_dt = datetime.strptime(str(shift_end), "%H:%M:%S")
        if shift_end_dt < shift_start_dt:
            shift_end_dt += timedelta(days=1)
        return (shift_end_dt - shift_start_dt).total_seconds() / 3600
    except Exception:
        return 0

def time_diff_in_hhmm(t1, t2):
    try:
        delta = abs(datetime.combine(datetime.today(), t1) - datetime.combine(datetime.today(), t2))
        minutes = delta.seconds // 60
        return f"{minutes // 60:02d}:{minutes % 60:02d}"
    except Exception:
        return "-"

def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 160},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
        {"label": "Shift", "fieldname": "shift", "fieldtype": "Link", "options": "Shift Type", "width": 120},
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 100},
        {"label": "In Time", "fieldname": "in_time", "fieldtype": "Data", "width": 100},
        {"label": "Out Time", "fieldname": "out_time", "fieldtype": "Data", "width": 100},
        {"label": "Actual Work Duration", "fieldname": "working_hours", "fieldtype": "Data", "width": 100},
        {"label": "Total Work Duration", "fieldname": "total_working_hours", "fieldtype": "Data", "width": 100},
        {"label": "Early Entry (Time HH:MM)", "fieldname": "early_entry", "fieldtype": "Data", "width": 100},
        {"label": "Late By (Time HH:MM)", "fieldname": "late_entry", "fieldtype": "Data", "width": 100},
        {"label": "Early Going By (Time HH:MM)", "fieldname": "early_going", "fieldtype": "Data", "width": 100},
        {"label": "Late Going (Time HH:MM)", "fieldname": "late_going", "fieldtype": "Data", "width": 100},
        {"label": "Over Time (Time HH:MM)", "fieldname": "over_time", "fieldtype": "Data", "width": 100},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 120},
        {"label": "Remark", "fieldname": "remark", "fieldtype": "Data", "width": 200}
    ]

    today = getdate(nowdate())
    period = filters.get("period")
    if period == "Monthly" and filters.get("months"):
        month_map = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        month = month_map.get(filters.months, today.month)
        year = int(filters.get("year", today.year))
        filters.from_date = datetime(year, month, 1).date()
        filters.to_date = (datetime(year + (month // 12), (month % 12) + 1, 1) - timedelta(days=1)).date()
    elif period == "Weekly":
        start_of_week = today - timedelta(days=today.weekday())
        filters.from_date = start_of_week
        filters.to_date = start_of_week + timedelta(days=6)
    elif period == "Daily":
        filters.from_date = filters.to_date = today
    else:
        filters.from_date = getdate(filters.get("from_date") or today)
        filters.to_date = getdate(filters.get("to_date") or today)

    # Build conditions
    conditions = [f"attendance.attendance_date BETWEEN '{filters.from_date}' AND '{filters.to_date}'"]
    if filters.get("status"):
        conditions.append(f"attendance.status = '{filters.status}'")
    if filters.get("employee"):
        conditions.append(f"attendance.employee = '{filters.employee}'")
    if filters.get("company"):
        conditions.append(f"attendance.company = '{filters.company}'")
    if filters.get("department"):
        conditions.append(f"emp.department = '{filters.department}'")
    condition_str = "WHERE " + " AND ".join(conditions)

    data = frappe.db.sql(f"""
        SELECT
            attendance.name AS attendance_id,
            attendance.employee,
            emp.employee_name as employee_name,
            attendance.status,
            attendance.attendance_date AS date,
            attendance.shift,
            attendance.working_hours AS t_working_hours,
            attendance.company,
            TIME(attendance.in_time) AS in_time,
            TIME(attendance.out_time) AS out_time,
            emp.department,
            st.start_time AS shift_start,
            st.end_time AS shift_end
        FROM `tabAttendance` attendance
        LEFT JOIN `tabEmployee` emp ON emp.name = attendance.employee
        LEFT JOIN `tabShift Type` st ON st.name = attendance.shift
        {condition_str}
        ORDER BY attendance.attendance_date DESC
        """, as_dict=True)

    for row in data:
        # Get checkin times if in_time/out_time missing
        in_time = row.get("in_time")
        out_time = row.get("out_time")
        if not in_time or not out_time or in_time == "None" or out_time == "None":
            checkin_in, checkin_out = get_checkin_times(row.employee, row.date)
            if checkin_in:
                in_time = checkin_in.time()
                row["in_time"] = in_time.strftime("%H:%M:%S")
            else:
                row["in_time"] = "-"
            if checkin_out:
                out_time = checkin_out.time()
                row["out_time"] = out_time.strftime("%H:%M:%S")
            else:
                row["out_time"] = "-"
        else:
            # Convert string to time
            try:
                in_time = datetime.strptime(str(in_time), "%H:%M:%S").time()
                out_time = datetime.strptime(str(out_time), "%H:%M:%S").time()
            except Exception:
                in_time = out_time = None

        # Actual working hours from checkins
        row["working_hours"] = actual_working_duration(row.employee, row.date)
       
        # Total working hours (from attendance)
        twh = row.get("t_working_hours")
        if twh is not None:
            try:
                hours = int(twh)
                minutes = int(round((float(twh) - hours) * 60))
                row["total_working_hours"] = f"{hours:02d}:{minutes:02d}" if twh else "-"
            except Exception:
                row["total_working_hours"] = "-"
        else:
            row["total_working_hours"] = "-"

        # Shift duration
        shift_duration = get_shift_duration(row.get("shift_start"), row.get("shift_end"))

        # Over Time
        try:
            ot = float(row.get("t_working_hours") or 0) - shift_duration
            if ot > 0:
                hours = int(ot)
                minutes = int(round((ot - hours) * 60))
                row["over_time"] = f"{hours:02d}:{minutes:02d}"
            else:
                row["over_time"] = "-"
        except Exception:
            row["over_time"] = "-"

        # Early/Late calculations
        for metric, condition, time_field1, time_field2 in [
            ("early_entry", lambda i, s: i < s, "in_time", "shift_start"),
            ("early_going", lambda o, e: o < e, "out_time", "shift_end"),
            ("late_entry", lambda i, s: i > s, "in_time", "shift_start"),
            ("late_going", lambda o, e: o > e, "out_time", "shift_end"),
        ]:
            try:
                t1_str = row.get(time_field1)
                t2_str = row.get(time_field2)
                if t1_str and t2_str and t1_str != "-" and t2_str != "-":
                    t1 = datetime.strptime(str(t1_str), "%H:%M:%S").time()
                    t2 = datetime.strptime(str(t2_str), "%H:%M:%S").time()
                    if condition(t1, t2):
                        row[metric] = time_diff_in_hhmm(t1, t2)
                    else:
                        row[metric] = "-"
                else:
                    row[metric] = "-"
            except Exception:
                row[metric] = "-"
        row["in_time"] = in_time.strftime("%H:%M") if in_time else "-"
        row["out_time"] = out_time.strftime("%H:%M") if out_time else "-"
        # Always ensure all fields are present
        for field in ["in_time", "out_time", "working_hours", "total_working_hours", "early_entry", "late_entry", "early_going", "late_going", "over_time"]:
            if field not in row or row[field] is None:
                row[field] = "-"

    return columns, data
