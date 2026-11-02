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
    """Attendance validate hook: link Employee Checkin of that employee/date."""
    if doc.get("employee_checkin") or not doc.get("employee") or not doc.get("attendance_date"):
        return

    checkin = get_checkin_for_attendance(
        doc.get("employee"),
        doc.get("attendance_date"),
        attendance_name=doc.get("name"),
        in_time=doc.get("in_time"),
    )
    if checkin:
        doc.employee_checkin = checkin


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
