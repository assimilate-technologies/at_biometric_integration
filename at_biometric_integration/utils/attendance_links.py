# at_biometric_integration/utils/attendance_links.py
import frappe
from frappe.utils import getdate, get_datetime


def pick_checkin(checkins, attendance_name=None, in_time=None):
    """Pick the Employee Checkin for an attendance from a list ordered by time asc.

    Priority:
    1. Checkin already linked to this attendance (attendance field)
    2. Checkin matching attendance in_time
    3. First (earliest) checkin of the day
    """
    if not checkins:
        return None

    if attendance_name:
        for c in checkins:
            if c.get("attendance") == attendance_name:
                return c.get("name")

    if in_time:
        in_time = get_datetime(in_time)
        for c in checkins:
            if get_datetime(c.get("time")) == in_time:
                return c.get("name")

    return checkins[0].get("name")


def get_checkins_for_day(employee, attendance_date):
    """All Employee Checkin of an employee on a date, ordered by time asc."""
    if not employee or not attendance_date:
        return []

    attendance_date = getdate(attendance_date)
    return frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [f"{attendance_date} 00:00:00", f"{attendance_date} 23:59:59"]],
        },
        fields=["name", "time", "attendance", "log_type"],
        order_by="time asc",
    )


def get_checkin_for_attendance(employee, attendance_date, attendance_name=None, in_time=None):
    checkins = get_checkins_for_day(employee, attendance_date)
    return pick_checkin(checkins, attendance_name=attendance_name, in_time=in_time)


def set_employee_checkin_link(doc, method=None):
    """Attendance validate hook: populate the 'employee_checkin' child table
    with ALL Employee Checkin records for this employee + date.
    Take the first record time as in_time and the last record time as out_time.
    When only one record, in_time and out_time show the same.
    """
    if not doc.get("employee") or not doc.get("attendance_date"):
        return

    from at_biometric_integration.utils.helpers import calculate_working_hours

    checkins = get_checkins_for_day(doc.employee, doc.attendance_date)
    if not checkins:
        # Also check child table if checkins were already linked
        child_checkins = [r.checkin for r in (doc.get("employee_checkin") or []) if r.get("checkin")]
        if child_checkins:
            checkins = frappe.get_all(
                "Employee Checkin",
                filters={"name": ["in", child_checkins]},
                fields=["name", "time"],
                order_by="time asc",
            )

    if not checkins:
        return

    # Collect names already in the child table to avoid duplicates
    existing = {row.checkin for row in (doc.get("employee_checkin") or []) if row.get("checkin")}

    for c in checkins:
        if c.name not in existing:
            doc.append("employee_checkin", {"checkin": c.name})

    # Rule: Take first record time as in_time and last record time as out_time
    # When only one record, in_time and out_time show the exact same
    valid_times = [c.get("time") for c in checkins if c.get("time")]
    if valid_times:
        doc.in_time = valid_times[0]
        doc.out_time = valid_times[-1]
        if doc.in_time == doc.out_time:
            doc.working_hours = "00:00:00"
        else:
            doc.working_hours = calculate_working_hours(doc.in_time, doc.out_time)


def get_regularization_for_attendance(employee, attendance_date):
    """Submitted Attendance Regularization of that employee on the date.

    Prefers an approved one, otherwise the latest submitted.
    """
    if not employee or not attendance_date:
        return None

    regularizations = frappe.get_all(
        "Attendance Regularization",
        filters={"employee": employee, "date": getdate(attendance_date), "docstatus": 1},
        fields=["name", "workflow_state"],
        order_by="creation desc",
    )
    if not regularizations:
        return None

    for reg in regularizations:
        state = reg.get("workflow_state") or ""
        if "Approved" in state and "Rejected" not in state:
            return reg.get("name")

    return regularizations[0].get("name")


def set_attendance_regularization_link(doc, method=None):
    """Attendance validate hook: link Attendance Regularization of that employee/date."""
    if doc.get("attendance_regularization") or not doc.get("employee") or not doc.get("attendance_date"):
        return

    regularization = get_regularization_for_attendance(doc.get("employee"), doc.get("attendance_date"))
    if regularization:
        doc.attendance_regularization = regularization


def calculate_and_set_working_hours(doc, method=None):
    """Attendance validate hook: calculate working_hours and set status per rules:
       - Approved Leave preserved
       - If in_time or out_time not present → status = 'Absent'
       - working_hours < 5 hr               → status = 'Absent'
       - working_hours in between 5 to 8.44 → status = 'Half Day'
       - working_hours >= 8:45 hr           → status = 'Present'
    """
    if doc.get("status") == "On Leave" and (doc.get("leave_application") or doc.get("leave_type")):
        return

    from at_biometric_integration.utils.helpers import calculate_working_hours
    from at_biometric_integration.utils.attendance_processing import get_working_hours_seconds, get_status_by_working_hours

    if not doc.get("in_time") or not doc.get("out_time"):
        doc.status = "Absent"
        if not doc.get("working_hours"):
            doc.working_hours = "00:00:00"
        return

    if doc.in_time == doc.out_time:
        doc.working_hours = "00:00:00"
    else:
        doc.working_hours = calculate_working_hours(doc.in_time, doc.out_time)

    work_seconds = get_working_hours_seconds(doc.working_hours)
    doc.status = get_status_by_working_hours(work_seconds, doc.in_time, doc.out_time)
