# # at_biometric_integration/utils/helpers.py
# import frappe
# from datetime import timedelta
# from frappe.utils import (
#     get_datetime,
#     now_datetime,
#     time_diff_in_hours,
#     add_days,
#     cint,
#     getdate,
# )

# # ------------------------------------------------
# # Logging helper
# # ------------------------------------------------
# def log_error(msg, title="Biometric Integration Error"):
#     try:
#         frappe.log_error(str(msg), title)
#     except Exception:
#         frappe.logger().error(f"{title}: {msg}")

# # ------------------------------------------------
# # Attendance Settings (central)
# # ------------------------------------------------
# def get_attendance_settings():
#     try:
#         s = frappe.get_single("Attendance Settings")
#         return frappe._dict({
#             "enable_regularization": bool(getattr(s, "enable_regularization", False)),
#             "regularization_from_hours": float(getattr(s, "regularization_from_hours", 0) or 0),
#             "regularization_to_hours": float(getattr(s, "regularization_to_hours", 24) or 24),
#             "min_working_hours": float(getattr(s, "min_working_hours", 4) or 4),
#             "auto_submit_hours_after_shift": float(getattr(s, "auto_submit_hours_after_shift", 4) or 4),
#             "max_regularization_days": int(getattr(s, "max_regularization_days", 3) or 3)
#         })
#     except Exception as e:
#         log_error(e, "Load Attendance Settings")
#         # sensible defaults
#         return frappe._dict({
#             "enable_regularization": False,
#             "regularization_from_hours": 0,
#             "regularization_to_hours": 24,
#             "min_working_hours": 4,
#             "auto_submit_hours_after_shift": 4,
#             "max_regularization_days": 3
#         })

# # ------------------------------------------------
# # Holidays & Leave
# # ------------------------------------------------
# def is_holiday(employee, date):
#     try:
#         holiday_list = frappe.get_value("Employee", employee, "holiday_list")
#         if not holiday_list:
#             return False
#         return frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": date})
#     except Exception as e:
#         log_error(e, "is_holiday")
#         return False

# def is_weekend(date):
#     """Check if date is Saturday (5) or Sunday (6)"""
#     return date.weekday() >= 5

# def is_working_day(employee, date):
#     """Check if date is a working day (not holiday and not weekend)"""
#     return not is_holiday(employee, date) and not is_weekend(date)

# def get_last_checkout_from_previous_days(employee, current_date, max_lookback_days=7):
#     """
#     Find the last checkout from previous working days.
#     Looks back up to max_lookback_days to find the most recent checkout.
#     Skips holidays and weekends.
#     Returns: dict with 'time' key or None
#     """
#     check_date = getdate(current_date) - timedelta(days=1)
#     end_date = getdate(current_date) - timedelta(days=max_lookback_days)
    
#     while check_date >= end_date:
#         # Skip if it's a holiday or weekend
#         if is_holiday(employee, check_date) or is_weekend(check_date):
#             check_date = check_date - timedelta(days=1)
#             continue
        
#         # Look for checkouts on this date - get all checkins first
#         all_checkins = frappe.get_all(
#             "Employee Checkin",
#             filters={
#                 "employee": employee,
#                 "time": ["between", [f"{check_date} 00:00:00", f"{check_date} 23:59:59"]]
#             },
#             fields=["name", "time", "log_type"],
#             order_by="time desc"
#         )
        
#         if all_checkins:
#             # Look for OUT type checkins first
#             out_checkins = [c for c in all_checkins if (c.get("log_type") or "").upper() == "OUT"]
#             if out_checkins:
#                 return out_checkins[0]  # Return the last OUT checkout
            
#             # If no OUT found, check if last checkin is not IN (treat as checkout)
#             last_checkin = all_checkins[0]
#             log_type = (last_checkin.get("log_type") or "").upper()
#             if log_type != "IN":
#                 return last_checkin
            
#             # If last checkin is IN, but there are multiple checkins, 
#             # the second-to-last might be a checkout
#             if len(all_checkins) > 1:
#                 return all_checkins[1]  # Return second-to-last as potential checkout
        
#         check_date = check_date - timedelta(days=1)
    
#     return None

# def get_leave_status(employee, date):
#     """
#     returns tuple: (status_str_or_None, leave_type_or_None, leave_app_name_or_None)
#     status_str: "On Leave" / "Half Day"
#     """
#     try:
#         leaves = frappe.get_all(
#             "Leave Application",
#             filters={
#                 "employee": employee,
#                 "from_date": ["<=", date],
#                 "to_date": [">=", date],
#                 "status": "Approved"
#             },
#             fields=["name", "leave_type", "half_day"],
#             limit_page_length=1
#         )
#         if leaves:
#             half = bool(leaves[0].get("half_day"))
#             return ("Half Day" if half else "On Leave", leaves[0].leave_type, leaves[0].name)
#         return (None, None, None)
#     except Exception as e:
#         log_error(e, "get_leave_status")
#         return (None, None, None)

# # ------------------------------------------------
# # Shift helpers
# # ------------------------------------------------
# def get_employee_shift(employee, attendance_date):
#     # Try Shift Assignment then Employee.default_shift then None
#     try:
#         shift_type = frappe.db.get_value("Shift Assignment", {"employee": employee, "date": attendance_date}, "shift_type")
#         if not shift_type:
#             shift_type = frappe.db.get_value("Employee", employee, "default_shift")
#         if not shift_type:
#             return None
#         return frappe.get_doc("Shift Type", shift_type)
#     except Exception as e:
#         log_error(e, "get_employee_shift")
#         return None

# def get_shift_end_datetime(shift_doc, attendance_date):
#     try:
#         if not shift_doc:
#             return get_datetime(f"{attendance_date} 18:30:00")
#         start_time = getattr(shift_doc, "start_time", None)
#         end_time = getattr(shift_doc, "end_time", None)
#         if not end_time:
#             return get_datetime(f"{attendance_date} 18:30:00")
#         end_dt = get_datetime(f"{attendance_date} {end_time}")
#         # if overnight
#         if start_time and end_dt < get_datetime(f"{attendance_date} {start_time}"):
#             end_dt = end_dt + add_days(end_dt, 1)  # shift to next day
#         return end_dt
#     except Exception as e:
#         log_error(e, "get_shift_end_datetime")
#         return get_datetime(f"{attendance_date} 18:30:00")

# # ------------------------------------------------
# # Regularization checks
# # ------------------------------------------------
# def has_pending_regularization(employee, attendance_date):
#     try:
#         regs = frappe.get_all("Attendance Regularization", filters={
#             "employee": employee, "attendance_date": attendance_date, "status": "Pending"
#         }, fields=["name"], limit_page_length=1)
#         if regs:
#             return True
#         # Also check Attendance Request doctype if used in your setup
#         reqs = frappe.get_all("Attendance Request", filters={
#             "employee": employee, "attendance_date": attendance_date, "status": "Pending"
#         }, fields=["name"], limit_page_length=1)
#         return bool(reqs)
#     except Exception as e:
#         log_error(e, "has_pending_regularization")
#         return False

# def has_approved_regularization(employee, attendance_date):
#     try:
#         regs = frappe.get_all("Attendance Regularization", filters={
#             "employee": employee, "attendance_date": attendance_date, "status": "Approved"
#         }, fields=["name"], limit_page_length=1)
#         if regs:
#             return True
#         reqs = frappe.get_all("Attendance Request", filters={
#             "employee": employee, "attendance_date": attendance_date, "status": "Approved"
#         }, fields=["name"], limit_page_length=1)
#         return bool(reqs)
#     except Exception as e:
#         log_error(e, "has_approved_regularization")
#         return False

# # ------------------------------------------------
# # Working hours
# # ------------------------------------------------
# def calculate_working_hours_from_times(in_time, out_time):
#     try:
#         if not in_time or not out_time:
#             return 0.0
#         return round(time_diff_in_hours(out_time, in_time), 2)
#     except Exception as e:
#         log_error(e, "calculate_working_hours_from_times")
#         return 0.0

# # Expecting checkin objects or dicts with 'time' key
# def calculate_working_hours(first_checkin, last_checkin):
#     try:
#         if not first_checkin or not last_checkin:
#             return 0.0

#         # CASE 1: already datetime (your current usage)
#         if isinstance(first_checkin, (str,)) or not hasattr(first_checkin, "get"):
#             in_t = get_datetime(first_checkin)
#             out_t = get_datetime(last_checkin)
#             return calculate_working_hours_from_times(in_t, out_t)

#         # CASE 2: dict or doc with time key
#         in_t = first_checkin.get("time") if isinstance(first_checkin, dict) else getattr(first_checkin, "time", None)
#         out_t = last_checkin.get("time") if isinstance(last_checkin, dict) else getattr(last_checkin, "time", None)

#         return calculate_working_hours_from_times(get_datetime(in_t), get_datetime(out_t))
#     except Exception as e:
#         log_error(e, "calculate_working_hours")
#         return 0.0


# # ------------------------------------------------
# # Status determination (Option B)
# # ------------------------------------------------
# def determine_attendance_status(working_hours, leave_status, is_holiday_flag, min_hours=None):
#     settings = get_attendance_settings()
#     min_h = min_hours if min_hours is not None else settings.min_working_hours
    
#     # Priority 1: Actual Work
#     if working_hours >= float(min_h):
#         return "Present"
        
#     # Priority 2: Holiday
#     if is_holiday_flag:
#         return "Holiday"
        
#     # Priority 3: Leave
#     if leave_status and leave_status[0]:
#         return leave_status[0] # "On Leave" or "Half Day"
        
#     # Priority 4: Short work or Absent
#     return "Half Day" if working_hours > 0 else "Absent"

# # ------------------------------------------------
# # Auto-submit eligibility (central)
# # ------------------------------------------------
# def can_auto_submit(att_doc):
#     """
#     att_doc: Attendance doc
#     Uses Attendance Settings and Shift end to decide.
#     Also respects pending regularization.
#     """
#     settings = get_attendance_settings()
#     try:
#         if att_doc.docstatus == 1:
#             return False
#         # skip holidays and On Leave
#         if att_doc.status in ("Holiday", "On Leave"):
#             return False
#         # pending regularization prevents auto submit
#         if has_pending_regularization(att_doc.employee, att_doc.attendance_date):
#             return False

#         shift = get_employee_shift(att_doc.employee, att_doc.attendance_date)
#         shift_end = get_shift_end_datetime(shift, att_doc.attendance_date)
#         now = now_datetime()
#         # condition 1: after fixed buffer (auto_submit_hours_after_shift)
#         if now >= shift_end + frappe.utils.timedelta(hours=settings.auto_submit_hours_after_shift):
#             # if working hours meet min OR approved regularization exists
#             if float(att_doc.working_hours or 0) >= float(settings.min_working_hours) or has_approved_regularization(att_doc.employee, att_doc.attendance_date):
#                 return True
#         # condition 2: if regularization window expired (regularization_to_hours)
#         if settings.enable_regularization:
#             if now >= shift_end + frappe.utils.timedelta(hours=settings.regularization_to_hours):
#                 if float(att_doc.working_hours or 0) >= float(settings.min_working_hours) or has_approved_regularization(att_doc.employee, att_doc.attendance_date):
#                     return True
#         return False
#     except Exception as e:
#         log_error(e, "can_auto_submit")
#         return False





# at_biometric_integration/utils/helpers.py

import frappe
from datetime import timedelta
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
        frappe.log_error(
            message=str(msg),
            title=str(title)
        )
    except Exception:
        frappe.logger().error(f"{title}: {msg}")


def time_to_hours(val):
    """Convert time (str 'HH:MM:SS', timedelta, int, or float) to decimal hours."""
    if not val:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, timedelta):
        return round(val.total_seconds() / 3600.0, 2)
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return 0.0
        try:
            return float(val)
        except ValueError:
            pass
        parts = val.split(":")
        if len(parts) >= 2:
            try:
                h = float(parts[0])
                m = float(parts[1])
                s = float(parts[2]) if len(parts) > 2 else 0.0
                return round(h + (m / 60.0) + (s / 3600.0), 2)
            except ValueError:
                return 0.0
    return 0.0


# ------------------------------------------------
# Attendance Settings (central)
# ------------------------------------------------
def get_attendance_settings():
    try:
        s = frappe.get_single("Attendance Settings")
        # Read auto_submit_after_shift_hours directly from Attendance Settings
        auto_hours = float(getattr(s, "auto_submit_after_shift_hours", 0) or 0)
        return frappe._dict({
            "enable_regularization": bool(
                getattr(s, "enable_regularization", False)
            ),
            "regularization_from_hours": float(
                getattr(s, "regularization_from_hours", 0) or 0
            ),
            "regularization_to_hours": float(
                getattr(s, "regularization_to_hours", 0) or 0
            ),
            "min_working_hours": time_to_hours(
                getattr(s, "min_working_hours", 0)
            ),
            "min_working_hour_for_half_day": time_to_hours(
                getattr(s, "min_working_hour_for_half_day", 0)
            ),
            # Both keys point to the same field — no hardcoded default
            "auto_submit_after_shift_hours": auto_hours,
            "auto_submit_hours_after_shift": auto_hours,
            "max_regularization_days": int(
                getattr(s, "max_regularization_days", 0) or 0
            ),
        })
    except Exception as e:
        log_error(frappe.get_traceback(), "Load Attendance Settings")

        return frappe._dict({
            "enable_regularization": False,
            "regularization_from_hours": 0,
            "regularization_to_hours": 0,
            "min_working_hours": 0,
            "min_working_hour_for_half_day": 0,
            "auto_submit_after_shift_hours": 0,
            "auto_submit_hours_after_shift": 0,
            "max_regularization_days": 0,
        })


# ------------------------------------------------
# Holidays & Leave
# ------------------------------------------------
def is_holiday(employee, date):
    try:
        holiday_list = frappe.get_value(
            "Employee", employee, "holiday_list"
        )

        if not holiday_list:
            return False

        return frappe.db.exists(
            "Holiday",
            {
                "parent": holiday_list,
                "holiday_date": date,
            },
        )

    except Exception as e:
        log_error(frappe.get_traceback(), "is_holiday")
        return False


def is_weekend(date):
    """Check if date is Saturday (5) or Sunday (6)."""
    return getdate(date).weekday() >= 5


def is_working_day(employee, date):
    """Check if the date is not a holiday and not a weekend."""
    return not is_holiday(employee, date) and not is_weekend(date)


def get_last_checkout_from_previous_days(
    employee, current_date, max_lookback_days=7
):
    """
    Find the last checkout from previous working days.
    Looks back up to max_lookback_days.
    Skips holidays and weekends.
    Returns a dict with a 'time' key or None.
    """
    check_date = getdate(current_date) - timedelta(days=1)
    end_date = getdate(current_date) - timedelta(
        days=max_lookback_days
    )

    while check_date >= end_date:
        if is_holiday(employee, check_date) or is_weekend(check_date):
            check_date -= timedelta(days=1)
            continue

        all_checkins = frappe.get_all(
            "Employee Checkin",
            filters={
                "employee": employee,
                "time": [
                    "between",
                    [
                        f"{check_date} 00:00:00",
                        f"{check_date} 23:59:59",
                    ],
                ],
            },
            fields=["name", "time", "log_type"],
            order_by="time desc",
        )

        if all_checkins:
            out_checkins = [
                c for c in all_checkins
                if (c.get("log_type") or "").upper() == "OUT"
            ]

            if out_checkins:
                return out_checkins[0]

            last_checkin = all_checkins[0]
            log_type = (last_checkin.get("log_type") or "").upper()

            if log_type != "IN":
                return last_checkin

            if len(all_checkins) > 1:
                return all_checkins[1]

        check_date -= timedelta(days=1)

    return None


def get_leave_status(employee, date):
    """
    Returns:
        (status_str_or_None, leave_type_or_None, leave_app_name_or_None)

    Status can be 'On Leave' or 'Half Day'.
    """
    try:
        leaves = frappe.get_all(
            "Leave Application",
            filters={
                "employee": employee,
                "from_date": ["<=", date],
                "to_date": [">=", date],
                "status": "Approved",
            },
            fields=["name", "leave_type", "half_day"],
            limit_page_length=1,
        )

        if leaves:
            half = bool(leaves[0].get("half_day"))

            return (
                "Half Day" if half else "On Leave",
                leaves[0].leave_type,
                leaves[0].name,
            )

        return (None, None, None)

    except Exception as e:
        log_error(frappe.get_traceback(), "get_leave_status")
        return (None, None, None)


# ------------------------------------------------
# Shift helpers
# ------------------------------------------------
def get_employee_shift(employee, attendance_date):
    """
    Get the employee's shift for the attendance date.

    First checks submitted Shift Assignments whose date range
    includes attendance_date. Falls back to Employee.default_shift.
    """
    try:
        attendance_date = getdate(attendance_date)

        assignments = frappe.get_all(
            "Shift Assignment",
            filters={
                "employee": employee,
                "start_date": ["<=", attendance_date],
                "docstatus": 1,
            },
            or_filters=[
                [
                    "Shift Assignment",
                    "end_date",
                    ">=",
                    attendance_date,
                ],
                [
                    "Shift Assignment",
                    "end_date",
                    "is",
                    "not set",
                ],
            ],
            fields=["shift_type", "start_date"],
            order_by="start_date desc",
            limit_page_length=1,
        )

        shift_type = (
            assignments[0].get("shift_type")
            if assignments
            else None
        )

        # Fall back to Employee.default_shift.
        if not shift_type:
            shift_type = frappe.db.get_value(
                "Employee",
                employee,
                "default_shift",
            )

        if not shift_type:
            return None

        return frappe.get_doc("Shift Type", shift_type)

    except Exception:
        log_error(
            frappe.get_traceback(),
            "get_employee_shift",
        )
        return None


def get_shift_end_datetime(shift_doc, attendance_date):
    try:
        start_time = None
        end_time = None

        if shift_doc:
            if isinstance(shift_doc, str):
                try:
                    shift_doc = frappe.get_doc("Shift Type", shift_doc)
                except Exception:
                    shift_doc = None

            if shift_doc:
                start_time = getattr(shift_doc, "start_time", None)
                end_time = getattr(shift_doc, "end_time", None)

        if not end_time:
            # Check any shift type in system
            shift_types = frappe.get_all("Shift Type", fields=["name", "start_time", "end_time"], limit_page_length=1)
            if shift_types:
                end_time = shift_types[0].end_time
                start_time = shift_types[0].start_time

        if not end_time:
            end_time = "18:30:00"

        end_dt = get_datetime(f"{attendance_date} {str(end_time)}")

        # Handle overnight shifts.
        if start_time:
            start_dt = get_datetime(
                f"{attendance_date} {str(start_time)}"
            )

            if end_dt < start_dt:
                end_dt += timedelta(days=1)

        return end_dt

    except Exception:
        log_error(
            frappe.get_traceback(),
            "get_shift_end_datetime",
        )
        return get_datetime(f"{attendance_date} 18:30:00")


# ------------------------------------------------
# Regularization checks
# ------------------------------------------------
def has_pending_regularization(employee, attendance_date):
    try:
        regs = frappe.get_all(
            "Attendance Regularization",
            filters={
                "employee": employee,
                "attendance_date": attendance_date,
                "status": "Pending",
            },
            fields=["name"],
            limit_page_length=1,
        )

        if regs:
            return True

        reqs = frappe.get_all(
            "Attendance Request",
            filters={
                "employee": employee,
                "attendance_date": attendance_date,
                "status": "Pending",
            },
            fields=["name"],
            limit_page_length=1,
        )

        return bool(reqs)

    except Exception:
        log_error(
            frappe.get_traceback(),
            "has_pending_regularization",
        )
        return False


def has_approved_regularization(employee, attendance_date):
    try:
        regs = frappe.get_all(
            "Attendance Regularization",
            filters={
                "employee": employee,
                "attendance_date": attendance_date,
                "status": "Approved",
            },
            fields=["name"],
            limit_page_length=1,
        )

        if regs:
            return True

        reqs = frappe.get_all(
            "Attendance Request",
            filters={
                "employee": employee,
                "attendance_date": attendance_date,
                "status": "Approved",
            },
            fields=["name"],
            limit_page_length=1,
        )

        return bool(reqs)

    except Exception:
        log_error(
            frappe.get_traceback(),
            "has_approved_regularization",
        )
        return False


# ------------------------------------------------
# Working hours
# ------------------------------------------------
def calculate_working_hours_from_times(in_time, out_time):
    """Calculate time difference between in_time and out_time as HH:MM:SS string.

    Calculates gap between time of day (hours, minutes, seconds).
    Example:
        in_time = 09-11-2026 13:23:54
        out_time = 09-11-2026 18:23:41
        gap = 04:59:47 -> returns "04:59:47"
    """
    try:
        if not in_time or not out_time:
            return "00:00:00"

        in_dt = get_datetime(in_time)
        out_dt = get_datetime(out_time)

        # Extract only the time components
        in_t = in_dt.time()
        out_t = out_dt.time()

        # Convert time of day to total seconds from midnight
        in_seconds = int((in_t.hour * 3600) + (in_t.minute * 60) + in_t.second)
        out_seconds = int((out_t.hour * 3600) + (out_t.minute * 60) + out_t.second)

        diff_seconds = out_seconds - in_seconds
        # If out_time is earlier than in_time (e.g. overnight 22:00 -> 06:00)
        if diff_seconds < 0:
            diff_seconds += 24 * 3600

        hours = diff_seconds // 3600
        minutes = (diff_seconds % 3600) // 60
        seconds = diff_seconds % 60

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    except Exception:
        log_error(
            frappe.get_traceback(),
            "calculate_working_hours_from_times",
        )
        return "00:00:00"


def calculate_working_hours(first_checkin, last_checkin):
    """Accepts datetime/string values or check-in objects/dicts containing 'time'.

    Returns 'HH:MM:SS' string.
    """
    try:
        if not first_checkin or not last_checkin:
            return "00:00:00"

        # CASE 1: datetime or string values.
        if (
            isinstance(first_checkin, str)
            or not hasattr(first_checkin, "get")
        ):
            in_t = get_datetime(first_checkin)
            out_t = get_datetime(last_checkin)

            return calculate_working_hours_from_times(
                in_t, out_t
            )

        # CASE 2: dictionaries or documents containing time.
        in_t = (
            first_checkin.get("time")
            if isinstance(first_checkin, dict)
            else getattr(first_checkin, "time", None)
        )

        out_t = (
            last_checkin.get("time")
            if isinstance(last_checkin, dict)
            else getattr(last_checkin, "time", None)
        )

        return calculate_working_hours_from_times(
            get_datetime(in_t),
            get_datetime(out_t),
        )

    except Exception:
        log_error(
            frappe.get_traceback(),
            "calculate_working_hours",
        )
        return "00:00:00"


# ------------------------------------------------
# Status determination (Option B)
# ------------------------------------------------
def determine_attendance_status(
    working_hours,
    leave_status=None,
    is_holiday_flag=False,
    min_hours=None,
    in_time=None,
    out_time=None,
):
    # Priority 1: Holiday
    if is_holiday_flag:
        return "Holiday"

    # Priority 2: Leave
    if leave_status and leave_status[0]:
        return leave_status[0]

    # Priority 3: If in_time or out_time not present -> Absent
    if in_time is not None or out_time is not None:
        if not in_time or not out_time:
            return "Absent"

    # Priority 4: Working hours rules:
    #   < 5 hr         → 'Absent'
    #   5 to 8.44 hr   → 'Half Day'
    #   >= 8:45 hr     → 'Present'
    work_h = time_to_hours(working_hours)
    FIVE_HOURS = 5.0
    EIGHT_FORTY_FIVE = 8.75  # 8 hours 45 mins

    if work_h < FIVE_HOURS:
        return "Absent"
    elif work_h < EIGHT_FORTY_FIVE:
        return "Half Day"
    else:
        return "Present"


# ------------------------------------------------
# Auto-submit eligibility (central)
# ------------------------------------------------
def can_auto_submit(att_doc):
    """
    Check whether an Attendance document is eligible for auto-submission.

    Rule: current time >= shift_end + auto_submit_after_shift_hours
    e.g. shift end 18:30 + 4 hours = 22:30 -> submit ALL draft Attendance
    records for that day regardless of working_hours or status.

    auto_submit_after_shift_hours is read from Attendance Settings doctype.
    """
    settings = get_attendance_settings()

    try:
        if att_doc.docstatus == 1:
            return False

        # Pending regularization prevents auto-submit.
        if has_pending_regularization(
            att_doc.employee,
            att_doc.attendance_date,
        ):
            return False

        shift = get_employee_shift(
            att_doc.employee,
            att_doc.attendance_date,
        )

        shift_end = get_shift_end_datetime(
            shift,
            att_doc.attendance_date,
        )

        now = now_datetime()
        # Read directly from Attendance Settings — no hardcoded fallback
        auto_submit_hours = float(settings.get("auto_submit_after_shift_hours") or 0)

        # Feature is disabled when field is 0
        if not auto_submit_hours:
            return False

        # Condition: shift_end + auto_submit_after_shift_hours has passed
        # e.g. shift end 18:30 + value from Attendance Settings = cutoff time
        # At or after cutoff → submit ALL attendance records for that day
        cutoff = shift_end + timedelta(hours=auto_submit_hours)
        if now >= cutoff:
            return True

        return False

    except Exception:
        log_error(
            frappe.get_traceback(),
            "can_auto_submit",
        )
        return False
