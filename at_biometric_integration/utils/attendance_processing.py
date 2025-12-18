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

def process_attendance_realtime(from_date=None, to_date=None):
    """
    Process attendance for all dates where check-ins exist.
    Updates attendance ONLY when IN/OUT mismatch.
    """

    processed = []

    if not from_date:
        from_date = frappe.db.sql("""
            SELECT DATE(MIN(time))
            FROM `tabEmployee Checkin`
        """)[0][0]


    if not to_date:
        to_date = getdate()

    try:
        rows = frappe.db.sql("""
            SELECT
                employee,
                DATE(time) AS att_date,
                MIN(time) AS first_in,
                MAX(time) AS last_out
            FROM `tabEmployee Checkin`
            WHERE date(time) BETWEEN %s AND %s
            GROUP BY employee, DATE(time)
        """, (from_date, to_date), as_dict=True)

        for row in rows:
            name = create_or_update_attendance_if_needed(
                row.employee,
                row.att_date,
                row.first_in,
                row.last_out
            )
            if name:
                processed.append(name)

        return processed

    except Exception as e:
        log_error(e, "process_attendance_realtime")
        return processed


def create_or_update_attendance_if_needed(employee, date, first_in, last_out):
    """
    Update attendance ONLY when IN/OUT mismatch
    and when rules allow update.
    """

    try:
        att = frappe.db.get_value(
            "Attendance",
            {"employee": employee, "attendance_date": date},
            ["name", "in_time", "out_time", "docstatus"],
            as_dict=True
        )

        # Skip submitted attendance
        if att and att.docstatus == 1:
            return None

        # Skip regularization / attendance request cases
        if has_pending_regularization(employee, date) or has_approved_regularization(employee, date):
            return None

        # Skip if no change in times
        if att and att.in_time == first_in and att.out_time == last_out:
            return None

        leave_status = get_leave_status(employee, date)
        holiday_flag = is_holiday(employee, date)
        shift = get_employee_shift(employee, date)

        working_hours = calculate_working_hours(
            {"time": first_in}, {"time": last_out}
        ) if first_in and last_out else 0

        status = determine_attendance_status(
            working_hours, leave_status, holiday_flag
        )

        if att:
            frappe.db.set_value("Attendance", att.name, {
                "in_time": first_in,
                "out_time": last_out,
                "working_hours": working_hours,
                "status": status,
                "shift": shift
            })
            attendance_name = att.name

        else:
            emp = frappe.get_doc("Employee", employee)
            doc = frappe.get_doc({
                "doctype": "Attendance",
                "employee": employee,
                "employee_name": emp.employee_name,
                "attendance_date": date,
                "company": emp.company,
                "shift": shift,
                "status": status,
                "working_hours": working_hours,
                "in_time": first_in,
                "out_time": last_out
            })
            doc.insert(ignore_permissions=True)
            attendance_name = doc.name

        # Link checkins safely
        link_checkins_to_attendance(attendance_name, employee, date)

        # Auto submit only if allowed
        att_doc = frappe.get_doc("Attendance", attendance_name)
        if can_auto_submit(att_doc):
            att_doc.submit()

        return attendance_name

    except Exception as e:
        log_error(f"{employee} {date}: {e}", "create_or_update_attendance_if_needed")
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
