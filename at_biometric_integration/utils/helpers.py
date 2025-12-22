# at_biometric_integration/utils/helpers.py
import frappe
from frappe.utils import (
    get_datetime,
    now_datetime,
    time_diff_in_hours,
    add_days,
    cint,
    getdate,
)

# ------------------------------------------------
# Logging helper
# ------------------------------------------------
def log_error(msg, title="Biometric Integration Error"):
    try:
        frappe.log_error(str(msg), title)
    except Exception:
        frappe.logger().error(f"{title}: {msg}")

# ------------------------------------------------
# Attendance Settings (central)
# ------------------------------------------------
def get_attendance_settings():
    try:
        s = frappe.get_single("Attendance Settings")
        return frappe._dict({
            "enable_regularization": bool(getattr(s, "enable_regularization", False)),
            "regularization_from_hours": float(getattr(s, "regularization_from_hours", 0) or 0),
            "regularization_to_hours": float(getattr(s, "regularization_to_hours", 24) or 24),
            "min_working_hours": float(getattr(s, "min_working_hours", 4) or 4),
            "auto_submit_hours_after_shift": float(getattr(s, "auto_submit_hours_after_shift", 4) or 4),
            "max_regularization_days": int(getattr(s, "max_regularization_days", 3) or 3)
        })
    except Exception as e:
        log_error(e, "Load Attendance Settings")
        # sensible defaults
        return frappe._dict({
            "enable_regularization": False,
            "regularization_from_hours": 0,
            "regularization_to_hours": 24,
            "min_working_hours": 4,
            "auto_submit_hours_after_shift": 4,
            "max_regularization_days": 3
        })

# ------------------------------------------------
# Holidays & Leave
# ------------------------------------------------
def is_holiday(employee, date):
    try:
        holiday_list = frappe.get_value("Employee", employee, "holiday_list")
        if not holiday_list:
            return False
        return frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": date})
    except Exception as e:
        log_error(e, "is_holiday")
        return False

def get_leave_status(employee, date):
    """
    returns tuple: (status_str_or_None, leave_type_or_None, leave_app_name_or_None)
    status_str: "On Leave" / "Half Day"
    """
    try:
        leaves = frappe.get_all(
            "Leave Application",
            filters={
                "employee": employee,
                "from_date": ["<=", date],
                "to_date": [">=", date],
                "status": "Approved"
            },
            fields=["name", "leave_type", "half_day"],
            limit_page_length=1
        )
        if leaves:
            half = bool(leaves[0].get("half_day"))
            return ("Half Day" if half else "On Leave", leaves[0].leave_type, leaves[0].name)
        return (None, None, None)
    except Exception as e:
        log_error(e, "get_leave_status")
        return (None, None, None)

# ------------------------------------------------
# Shift helpers
# ------------------------------------------------
def get_employee_shift(employee, attendance_date):
    # Try Shift Assignment then Employee.default_shift then None
    try:
        shift_type = frappe.db.get_value("Shift Assignment", {"employee": employee, "date": attendance_date}, "shift_type")
        if not shift_type:
            shift_type = frappe.db.get_value("Employee", employee, "default_shift")
        if not shift_type:
            return None
        return frappe.get_doc("Shift Type", shift_type)
    except Exception as e:
        log_error(e, "get_employee_shift")
        return None

def get_shift_end_datetime(shift_doc, attendance_date):
    try:
        if not shift_doc:
            return get_datetime(f"{attendance_date} 18:30:00")
        start_time = getattr(shift_doc, "start_time", None)
        end_time = getattr(shift_doc, "end_time", None)
        if not end_time:
            return get_datetime(f"{attendance_date} 18:30:00")
        end_dt = get_datetime(f"{attendance_date} {end_time}")
        # if overnight
        if start_time and end_dt < get_datetime(f"{attendance_date} {start_time}"):
            end_dt = end_dt + add_days(end_dt, 1)  # shift to next day
        return end_dt
    except Exception as e:
        log_error(e, "get_shift_end_datetime")
        return get_datetime(f"{attendance_date} 18:30:00")

# ------------------------------------------------
# Regularization checks
# ------------------------------------------------
def has_pending_regularization(employee, attendance_date):
    try:
        regs = frappe.get_all("Attendance Regularization", filters={
            "employee": employee, "attendance_date": attendance_date, "status": "Pending"
        }, fields=["name"], limit_page_length=1)
        if regs:
            return True
        # Also check Attendance Request doctype if used in your setup
        reqs = frappe.get_all("Attendance Request", filters={
            "employee": employee, "attendance_date": attendance_date, "status": "Pending"
        }, fields=["name"], limit_page_length=1)
        return bool(reqs)
    except Exception as e:
        log_error(e, "has_pending_regularization")
        return False

def has_approved_regularization(employee, attendance_date):
    try:
        regs = frappe.get_all("Attendance Regularization", filters={
            "employee": employee, "attendance_date": attendance_date, "status": "Approved"
        }, fields=["name"], limit_page_length=1)
        if regs:
            return True
        reqs = frappe.get_all("Attendance Request", filters={
            "employee": employee, "attendance_date": attendance_date, "status": "Approved"
        }, fields=["name"], limit_page_length=1)
        return bool(reqs)
    except Exception as e:
        log_error(e, "has_approved_regularization")
        return False

# ------------------------------------------------
# Working hours
# ------------------------------------------------
def calculate_working_hours_from_times(in_time, out_time):
    try:
        if not in_time or not out_time:
            return 0.0
        return round(time_diff_in_hours(out_time, in_time), 2)
    except Exception as e:
        log_error(e, "calculate_working_hours_from_times")
        return 0.0

# Expecting checkin objects or dicts with 'time' key
def calculate_working_hours(first_checkin, last_checkin):
    try:
        if not first_checkin or not last_checkin:
            return 0.0

        # CASE 1: already datetime (your current usage)
        if isinstance(first_checkin, (str,)) or not hasattr(first_checkin, "get"):
            in_t = get_datetime(first_checkin)
            out_t = get_datetime(last_checkin)
            return calculate_working_hours_from_times(in_t, out_t)

        # CASE 2: dict or doc with time key
        in_t = first_checkin.get("time") if isinstance(first_checkin, dict) else getattr(first_checkin, "time", None)
        out_t = last_checkin.get("time") if isinstance(last_checkin, dict) else getattr(last_checkin, "time", None)

        return calculate_working_hours_from_times(get_datetime(in_t), get_datetime(out_t))
    except Exception as e:
        log_error(e, "calculate_working_hours")
        return 0.0


# ------------------------------------------------
# Status determination (Option B)
# ------------------------------------------------
def determine_attendance_status(working_hours, leave_status, is_holiday_flag, min_hours=None):
    settings = get_attendance_settings()
    min_h = min_hours if min_hours is not None else settings.min_working_hours
    if is_holiday_flag:
        return "Holiday"
    if leave_status and leave_status[0] == "On Leave":
        return "On Leave"
    if leave_status and leave_status[0] == "Half Day":
        return "Half Day"
    if working_hours >= float(min_h):
        return "Present"
    return "Half Day" if working_hours > 0 else "Absent"

# ------------------------------------------------
# Auto-submit eligibility (central)
# ------------------------------------------------
def can_auto_submit(att_doc):
    """
    att_doc: Attendance doc
    Uses Attendance Settings and Shift end to decide.
    Also respects pending regularization.
    """
    settings = get_attendance_settings()
    try:
        if att_doc.docstatus == 1:
            return False
        # skip holidays and On Leave
        if att_doc.status in ("Holiday", "On Leave"):
            return False
        # pending regularization prevents auto submit
        if has_pending_regularization(att_doc.employee, att_doc.attendance_date):
            return False

        shift = get_employee_shift(att_doc.employee, att_doc.attendance_date)
        shift_end = get_shift_end_datetime(shift, att_doc.attendance_date)
        now = now_datetime()
        # condition 1: after fixed buffer (auto_submit_hours_after_shift)
        if now >= shift_end + frappe.utils.timedelta(hours=settings.auto_submit_hours_after_shift):
            # if working hours meet min OR approved regularization exists
            if float(att_doc.working_hours or 0) >= float(settings.min_working_hours) or has_approved_regularization(att_doc.employee, att_doc.attendance_date):
                return True
        # condition 2: if regularization window expired (regularization_to_hours)
        if settings.enable_regularization:
            if now >= shift_end + frappe.utils.timedelta(hours=settings.regularization_to_hours):
                if float(att_doc.working_hours or 0) >= float(settings.min_working_hours) or has_approved_regularization(att_doc.employee, att_doc.attendance_date):
                    return True
        return False
    except Exception as e:
        log_error(e, "can_auto_submit")
        return False
