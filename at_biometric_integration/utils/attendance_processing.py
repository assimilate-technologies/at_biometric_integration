# at_biometric_integration/utils/attendance_processing.py
import frappe
from frappe.utils import getdate, get_datetime, now_datetime, time_diff_in_hours
from .helpers import (
    get_leave_status, is_holiday, get_employee_shift,
    calculate_working_hours, determine_attendance_status,
    has_pending_regularization, has_approved_regularization,
    can_auto_submit, log_error, get_attendance_settings
)

# Link checkins utility
def link_checkins_to_attendance(attendance_name, employee, attendance_date):
    """
    Link all Employee Checkin rows for the date to the attendance record.
    Mark first checkin log_type=IN and last checkin log_type=OUT.
    """
    try:
        checkins = frappe.get_all("Employee Checkin",
            filters={"employee": employee, "time": ["between", [f"{attendance_date} 00:00:00", f"{attendance_date} 23:59:59"]]},
            fields=["name", "time"],
            order_by="time asc"
        )
        if not checkins:
            return

        first = checkins[0]
        last = checkins[-1]

        for c in checkins:
            fields = {"attendance": attendance_name}
            if c["name"] == first["name"]:
                fields["log_type"] = "IN"
            if c["name"] == last["name"]:
                fields["log_type"] = "OUT"
            frappe.db.set_value("Employee Checkin", c["name"], fields)
    except Exception as e:
        log_error(e, "link_checkins_to_attendance")

def process_attendance_realtime(date=None):
    """
    Process checkins for the given date (default today).
    Returns a list of created/updated attendance names.
    """
    processed = []
    if date is None:
        date = getdate()

    try:
        # fetch employees who have checkins on date
        employees = frappe.db.sql_list("""
            select distinct employee from `tabEmployee Checkin`
            where date(time) = %s
        """, (date,))

        for emp in employees:
            try:
                name = create_or_update_attendance(emp, date)
                if name:
                    processed.append(name)
            except Exception as e:
                log_error(f"process_employee {emp} failed: {e}", "process_attendance_realtime")
        return processed
    except Exception as e:
        log_error(e, "process_attendance_realtime")
        return processed

def create_or_update_attendance(employee, date):
    """
    Build or update Attendance for employee on date using first/last checkin.
    Applies Option B: leave/holiday override.
    """
    try:
        first = frappe.db.sql("""
            select name, time from `tabEmployee Checkin`
            where employee=%s and date(time) = %s
            order by time asc limit 1
        """, (employee, date), as_dict=True)
        last = frappe.db.sql("""
            select name, time from `tabEmployee Checkin`
            where employee=%s and date(time) = %s
            order by time desc limit 1
        """, (employee, date), as_dict=True)

        first = first[0] if first else None
        last = last[0] if last else None

        leave_status = get_leave_status(employee, date)
        holiday_flag = is_holiday(employee, date)
        shift = get_employee_shift(employee, date)

        working_hours = 0.0
        if first and last:
            working_hours = calculate_working_hours({"time": first["time"]}, {"time": last["time"]})

        status = determine_attendance_status(working_hours, leave_status, holiday_flag)
        existing = frappe.db.get_value("Attendance", {"employee": employee, "attendance_date": date}, "name")

        if existing:
            # update
            frappe.db.set_value("Attendance", existing, {
                "in_time": first["time"] if first else None,
                "out_time": last["time"] if last else None,
                "working_hours": working_hours,
                "status": status,
                "shift": shift if shift else None 
            })
            attendance_name = existing
        else:
            # insert
            emp = frappe.get_doc("Employee", employee)
            att_doc = frappe.get_doc({
                "doctype": "Attendance",
                "employee": employee,
                "employee_name": emp.employee_name,
                "attendance_date": date,
                "company": emp.company,
                "shift": shift if shift else None,
                "status": status,
                "working_hours": working_hours,
                "in_time": first["time"] if first else None,
                "out_time": last["time"] if last else None
            })
            att_doc.insert(ignore_permissions=True)
            attendance_name = att_doc.name

        # link checkins
        link_checkins_to_attendance(attendance_name, employee, date)

        # attempt auto submit if eligible and no pending reg
        # use central can_auto_submit function that reads settings
        att_doc = frappe.get_doc("Attendance", attendance_name)
        if can_auto_submit(att_doc):
            try:
                att_doc.submit()
            except Exception as e:
                log_error(f"Auto-submit failed for {attendance_name}: {e}", "Auto Submit")

        frappe.db.commit()
        return attendance_name
    except Exception as e:
        log_error(f"create_or_update_attendance failed for {employee} {date}: {e}", "Create/Update Attendance")
        return None

def mark_absent_for_date(employee, date):
    """
    Create Attendance = Absent if no checkins and not on leave/holiday and no attendance exists.
    """
    try:
        has_checkin = frappe.db.exists("Employee Checkin", {"employee": employee, "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]})
        has_att = frappe.db.exists("Attendance", {"employee": employee, "attendance_date": date})
        leave_status = get_leave_status(employee, date)
        holiday_flag = is_holiday(employee, date)

        if not has_checkin and not has_att and not holiday_flag:
            status = leave_status[0] if leave_status[0] else "Absent"
            emp = frappe.get_doc("Employee", employee)
            att_doc = frappe.get_doc({
                "doctype": "Attendance",
                "employee": employee,
                "employee_name": emp.employee_name,
                "attendance_date": date,
                "company": emp.company,
                "status": status,
                "leave_type": leave_status[1],
                "leave_application": leave_status[2]
            })
            att_doc.insert(ignore_permissions=True)
            frappe.db.commit()
    except Exception as e:
        log_error(e, "mark_absent_for_date")
