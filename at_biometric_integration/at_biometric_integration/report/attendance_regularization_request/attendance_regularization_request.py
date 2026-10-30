# Attendance Regularization Request Report - Enhanced Logic
import frappe
from datetime import datetime, timedelta, date, time
from frappe.utils import getdate, format_time, get_datetime
from at_biometric_integration.utils.helpers import (
    calculate_working_hours, 
    determine_attendance_status, 
    get_leave_status, 
    is_holiday
)


def execute(filters=None):
    filters = frappe._dict(filters or {})
    
    # ---------------- Load Settings ----------------
    settings = frappe.get_single("Attendance Settings") if frappe.db.exists("DocType", "Attendance Settings") else None

    enable_feature = getattr(settings, "enable_regularization", True)
    min_delay_hours = getattr(settings, "regularization_from_hours", 24) or 24
    max_delay_hours = getattr(settings, "regularization_to_hours", 48) or 48
    max_requests_per_month = getattr(settings, "max_requests_per_month", 3) or 3
    checkin_grace_start = getattr(settings, "checkin_grace_start_minutes", 60) or 60
    checkout_grace_end = getattr(settings, "checkout_grace_end_minutes", 30) or 30
    min_working_hours = getattr(settings, "min_working_hours", 8) or 8
    enable_notifications = getattr(settings, "enable_notifications", True)
    notification_template = getattr(settings, "notification_message_template", "You are eligible for Attendance Regularization on {date}")

    # Convert numeric fields
    min_delay_hours = int(min_delay_hours)
    max_delay_hours = int(max_delay_hours)
    max_requests_per_month = int(max_requests_per_month)
    checkin_grace_start = int(checkin_grace_start)
    checkout_grace_end = int(checkout_grace_end)
    min_working_hours = float(min_working_hours)

    # ---------------- Define Columns ----------------
    columns = [
        {"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"fieldname": "employee_name", "label": "Employee Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "attendance_date", "label": "Attendance Date", "fieldtype": "Date", "width": 120},
        {"fieldname": "shift_start", "label": "Shift Start", "fieldtype": "Data", "width": 100},
        {"fieldname": "shift_end", "label": "Shift End", "fieldtype": "Data", "width": 100},
        {"fieldname": "in_time", "label": "In Time", "fieldtype": "Data", "width": 130},
        {"fieldname": "out_time", "label": "Out Time", "fieldtype": "Data", "width": 130},
        {"fieldname": "working_hours", "label": "Working Hours (HH:MM)", "fieldtype": "Data", "width": 140},
        {"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Present\nAbsent\nOn Leave\nHalf Day\nMissed Punch", "width": 120},
        {"fieldname": "missed_punch", "label": "Missed Punch", "fieldtype": "Data", "width": 100},
        {"fieldname": "regularization_count", "label": "Regularization Count (Month)", "fieldtype": "Int", "width": 160},
        {"fieldname": "regularization_eligible", "label": "Regularization Eligible", "fieldtype": "Data", "width": 140},
        {"fieldname": "action", "label": "Action", "fieldtype": "Data", "width": 160},
        {"fieldname": "remarks", "label": "Remarks", "fieldtype": "Data", "width": 300},
    ]

    data = []

    # ---------------- Build Filters ----------------
    conditions = []
    if filters.get("employee"):
        conditions.append(["employee", "=", filters.employee])

    # Date range from filters. When NO dates are provided the report
    # shows ALL data (no date condition is applied).
    from_date = getdate(filters.from_date) if filters.get("from_date") else None
    to_date = getdate(filters.to_date) if filters.get("to_date") else None

    if from_date and to_date:
        conditions.append(["attendance_date", "between", [from_date, to_date]])
    elif from_date:
        conditions.append(["attendance_date", ">=", from_date])
    elif to_date:
        conditions.append(["attendance_date", "<=", to_date])

    # ---------------- Fetch Attendance ----------------
    attendance_records = frappe.get_all(
        "Attendance",
        filters=conditions,
        fields=["name", "employee", "attendance_date", "in_time", "out_time", "working_hours", "status"],
        order_by="attendance_date asc"
    )

    # Also fetch dates that have check-ins but may not have attendance records
    # Uses the same date range as above; with no dates it fetches ALL check-in dates.
    checkin_where = []
    checkin_params = []

    if from_date:
        checkin_where.append("DATE(time) >= %s")
        checkin_params.append(from_date)
    if to_date:
        checkin_where.append("DATE(time) <= %s")
        checkin_params.append(to_date)

    checkin_sql = """
        SELECT DISTINCT employee, DATE(time) as checkin_date
        FROM `tabEmployee Checkin`
    """
    if checkin_where:
        checkin_sql += " WHERE " + " AND ".join(checkin_where)
    checkin_sql += " ORDER BY checkin_date ASC"

    checkin_dates = frappe.db.sql(checkin_sql, tuple(checkin_params), as_dict=True)
    
    # Create a set of (employee, date) tuples from attendance records
    attendance_keys = {(r.employee, getdate(r.attendance_date)) for r in attendance_records}
    
    # Add missing dates that have check-ins but no attendance records
    for checkin in checkin_dates:
        emp = checkin.employee
        checkin_date = getdate(checkin.checkin_date)
        key = (emp, checkin_date)
        
        # Apply employee filter if specified
        if filters.get("employee") and emp != filters.employee:
            continue
            
        if key not in attendance_keys:
            # Create a dummy record for dates with check-ins but no attendance
            attendance_records.append(frappe._dict({
                "name": None,
                "employee": emp,
                "attendance_date": checkin_date,
                "in_time": None,
                "out_time": None,
                "working_hours": None,
                "status": None,
                "latitude": "0.0",
                "longitude": "0.0",
            }))

    today_dt = datetime.now()

    for record in attendance_records:
        emp = record.employee
        employee_name = frappe.get_value("Employee", emp, "employee_name") or ""
        att_date = getdate(record.attendance_date)
        shift_start, shift_end = get_shift_from_default_shift(emp)

        # ---------------- ALWAYS Fetch Check-in/Check-out Dynamically from Employee Checkin ----------------
        # Fetch FIRST IN punch and LAST OUT punch from Employee Checkin table
        # This ensures we always show the correct, up-to-date data from actual check-ins
        cin_datetime, cout_datetime = get_checkin_times_dynamic(emp, att_date)
        
        # Format times for display
        in_time = format_time_only(cin_datetime) if cin_datetime else ""
        out_time = format_time_only(cout_datetime) if cout_datetime else ""

        # Missed punch detection based on dynamically fetched check-ins
        missed_punch = "-"
        if not cin_datetime and not cout_datetime:
            missed_punch = "BOTH"
        elif not cin_datetime:
            missed_punch = "IN"
        elif not cout_datetime:
            missed_punch = "OUT"

        # ---------------- Calculate Total Working Duration Dynamically ----------------
        # Calculate Total Working Duration: difference between first check-in and last check-out
        # This is the same as "Total Work Duration" in attendance summary
        working_hours_value = 0.0
        formatted_working_hours = "-"
        
        if cin_datetime and cout_datetime:
            try:
                # Calculate difference between first check-in and last check-out
                diff = cout_datetime - cin_datetime
                working_hours_value = diff.total_seconds() / 3600.0
                
                if working_hours_value > 0:
                    hours = int(working_hours_value)
                    minutes = int(round((working_hours_value - hours) * 60))
                    formatted_working_hours = f"{hours:02d}:{minutes:02d}"
                else:
                    formatted_working_hours = "00:00"
            except Exception as e:
                frappe.log_error(f"Error calculating total working duration for {emp} on {att_date}: {str(e)}", "Total Working Duration Error")
                formatted_working_hours = "00:00"
        elif cin_datetime or cout_datetime:
            # If only one punch exists, working hours is 0
            formatted_working_hours = "00:00"
            working_hours_value = 0.0

        # ---------------- Get Leave & Holiday Info ----------------
        leave_info = get_leave_status(emp, att_date) # (status, type, name)
        holiday_flag = is_holiday(emp, att_date)
        
        # ---------------- Determine Status Dynamically ----------------
        # Always determine status based on dynamically calculated working hours
        status = determine_attendance_status(working_hours_value, leave_info, holiday_flag)
        
        # Override status for missed punches if no check-ins at all
        if missed_punch == "BOTH" and not leave_info[0] and not holiday_flag:
            status = "Absent"

        remarks = []
        eligible = False
        disable_action = False

        # ---------------- Regularization Logic ----------------
        if not enable_feature:
            remarks.append("Regularization Disabled")

        # Check for leave (using result from helper above)
        has_leave = bool(leave_info[0])

        # Calculate hours since attendance date
        hours_passed = calculate_hours_excluding_weekends(att_date, today_dt)


        # Monthly approved requests
        month_start = att_date.replace(day=1)
        month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        completed_requests = frappe.db.count("Attendance Regularization", {
            "employee": emp,
            "date": ["between", [month_start, month_end]],
            "workflow_state": "Approved"
        })

        # ---- New Regularization Rules ----
        if enable_feature and not has_leave:
            # (1) Within regularization time window
            if min_delay_hours <= hours_passed <= max_delay_hours:
                # (2) Missing check-in or out
                if missed_punch in ["IN", "OUT", "BOTH"]:
                    eligible = True
                    remarks.append("Eligible: Missing check-in/out")
                # (3) Working hours below threshold
                elif working_hours_value > 0 and working_hours_value < min_working_hours:
                    eligible = True
                    remarks.append(f"Eligible: Working hours below {min_working_hours} hours")
                # (4) Grace time logic for check-in window
                elif cin_datetime and check_shift_checkin_grace(cin_datetime, att_date, shift_start, shift_end, checkin_grace_start, checkout_grace_end):
                    eligible = True
                    remarks.append("Eligible: Check-in outside grace window")
            else:
                if hours_passed < min_delay_hours:
                    remarks.append(f"Wait for {min_delay_hours} hours to regularize")
                elif hours_passed > max_delay_hours:
                    remarks.append(f"{max_delay_hours} hours exceeded - not allowed")

            # Monthly limit
            if completed_requests >= max_requests_per_month:
                remarks.append(f"Monthly limit reached ({max_requests_per_month})")
                eligible = False

        # Set action button and notification
        action_label = "Create Regularization Request" if eligible else ""
        cache_key = f"reg_notif::{emp}::{att_date}"
        if eligible and enable_notifications and not frappe.cache().get_value(cache_key):
            send_regularization_notification(emp, att_date, notification_template)
            frappe.cache().set_value(cache_key, 1, expires_in_sec=86400)

        data.append({
            "employee": emp,
            "employee_name": employee_name,
            "attendance_date": att_date,
            "shift_start": shift_start or "-",
            "shift_end": shift_end or "-",
            "in_time": in_time or "-",
            "out_time": out_time or "-",
            "working_hours": formatted_working_hours,
            "status": status,
            "missed_punch": missed_punch,
            "regularization_count": completed_requests,
            "regularization_eligible": "Yes" if eligible else "No",
            "action": action_label,
            "remarks": "; ".join(remarks)
        })

    # Sort data by attendance_date to ensure chronological order
    data.sort(key=lambda x: x.get("attendance_date", date.min))

    # ---------------- Apply Status Filter ----------------
    status_filter = filters.get("status")
    if status_filter:
        data = [row for row in data if row.get("status") == status_filter]
        # Re-sort by status then attendance_date
        data.sort(key=lambda x: (x.get("status") or "", x.get("attendance_date", date.min)))

    return columns, data

# ---------------- Helper Functions ----------------
def get_shift_from_default_shift(employee):
    try:
        default_shift = frappe.db.get_value("Employee", employee, "default_shift")
        if default_shift:
            st = frappe.get_doc("Shift Type", default_shift)
            return st.start_time or "-", st.end_time or "-"
    except:
        pass
    return "-", "-"

def format_time_only(dt_value):
    if not dt_value:
        return ""
    try:
        dt_obj = frappe.utils.get_datetime(dt_value)
        return format_time(dt_obj.time(), "HH:mm")
    except:
        return str(dt_value)

def check_shift_checkin_grace(in_time_dt, attendance_date, shift_start, shift_end, grace_start, grace_end):
    """Check if check-in was outside grace window."""
    if not shift_start or not shift_end or not in_time_dt or shift_start == "-" or shift_end == "-":
        return False
    try:
        # Handle time objects or time strings
        if isinstance(shift_start, str) and shift_start != "-":
            from frappe.utils import get_time
            shift_start = get_time(shift_start)
        if isinstance(shift_end, str) and shift_end != "-":
            from frappe.utils import get_time
            shift_end = get_time(shift_end)
        
        shift_start_dt = datetime.combine(getdate(attendance_date), shift_start)
        shift_end_dt = datetime.combine(getdate(attendance_date), shift_end)
        if in_time_dt < (shift_start_dt - timedelta(minutes=grace_start)) or in_time_dt > (shift_end_dt + timedelta(minutes=grace_end)):
            return True
    except:
        pass
    return False

def send_regularization_notification(employee, att_date, template):
    """Send in-app notification to employee when eligible."""
    try:
        user = frappe.db.get_value("Employee", employee, "user_id")
        if user:
            message = template.format(date=att_date.strftime("%Y-%m-%d"))
            frappe.publish_realtime(event="msgprint", message=message, user=user)
            frappe.create_log("Attendance Regularization Notification", message)
    except Exception as e:
        frappe.log_error(str(e), "Regularization Notification Error")
        
# Calculate hours since attendance date (excluding weekends)
def calculate_hours_excluding_weekends(start_date, end_datetime):
    """Return total hours difference excluding weekends (Saturday/Sunday)."""
    total_hours = 0
    current_date = start_date

    while current_date <= end_datetime.date():
        if current_date.weekday() < 5:  # Monday–Friday
            if current_date == start_date:
                start_dt = datetime.combine(start_date, time.min)
            else:
                start_dt = datetime.combine(current_date, time.min)

            if current_date == end_datetime.date():
                end_dt = end_datetime
            else:
                end_dt = datetime.combine(current_date, time.max)

            total_hours += (end_dt - start_dt).total_seconds() / 3600

        current_date += timedelta(days=1)

    return total_hours


def actual_working_duration(employee, date):
    """
    Calculate actual working hours based on alternating IN/OUT checkins (same as attendance summary).
    This pairs check-ins: times[0] with times[1], times[2] with times[3], etc.
    Returns working hours in HH:MM format.
    """
    try:
        # Ensure date is in string format for the query
        from datetime import date as date_type
        if isinstance(date, date_type):
            date_str = date.strftime("%Y-%m-%d")
        elif hasattr(date, 'strftime'):
            date_str = date.strftime("%Y-%m-%d")
        else:
            date_str = str(getdate(date))
        
        checkins = frappe.get_all("Employee Checkin",
            filters={
                "employee": employee,
                "time": ["between", [f"{date_str} 00:00:00", f"{date_str} 23:59:59"]]
            },
            fields=["time"],
            order_by="time asc"
        )
        
        if not checkins:
            return "-"
        
        total_duration = 0.0
        times = [get_datetime(c.time) for c in checkins]
        
        # Pair alternating check-ins: 0-1, 2-3, 4-5, etc.
        for i in range(0, len(times) - 1, 2):
            in_time = times[i]
            out_time = times[i + 1]
            if out_time > in_time:
                total_duration += (out_time - in_time).total_seconds()
        
        if total_duration > 0:
            hours = int(total_duration // 3600)
            minutes = int((total_duration % 3600) // 60)
            return f"{hours:02d}:{minutes:02d}"
        
        return "-"
    except Exception as e:
        frappe.log_error(f"Error calculating actual working duration for {employee} on {date}: {str(e)}", "Actual Working Duration Error")
        return "-"


def get_checkin_times_dynamic(employee, date):
    """
    Dynamically fetch check-in and check-out times from Employee Checkin table.

    Strategy (in priority order):
    1. If explicit IN / OUT log_types exist → use them strictly (no cross-fallback).
       This correctly surfaces missed IN or missed OUT punches.
    2. If NO log_type is set on any punch:
       - Multiple punches  → first punch = IN, last punch = OUT.
       - Single punch      → compare against shift midpoint to guess direction:
             Before midpoint → treat as IN punch  → OUT is missing.
             At/After midpoint → treat as OUT punch → IN is missing.

    Returns: (in_time_datetime, out_time_datetime)
             Either value can be None, meaning that punch is missing.
    """
    try:
        from datetime import date as date_type
        if isinstance(date, date_type):
            date_str = date.strftime("%Y-%m-%d")
        elif hasattr(date, "strftime"):
            date_str = date.strftime("%Y-%m-%d")
        else:
            date_str = str(getdate(date))

        checkins = frappe.get_all(
            "Employee Checkin",
            filters={
                "employee": employee,
                "time": ["between", [f"{date_str} 00:00:00", f"{date_str} 23:59:59"]],
                "latitude": "0.0",
                "longitude": "0.0",
            },
            fields=["time", "log_type"],
            order_by="time asc",
        )

        if not checkins:
            return None, None

        in_punches    = []
        out_punches   = []
        no_type_punches = []

        for checkin in checkins:
            log_type = (checkin.get("log_type") or "").strip().upper()
            checkin_time = get_datetime(checkin.time)

            if log_type == "IN":
                in_punches.append(checkin_time)
            elif log_type == "OUT":
                out_punches.append(checkin_time)
            else:
                no_type_punches.append(checkin_time)

        # ── Case 1: Explicit log_type present (at least one IN or OUT) ──────────
        # Use each list strictly — a missing list means that punch is absent.
        # Do NOT fall back to the other list; that would hide the missed punch.
        if in_punches or out_punches:
            in_time_dt  = min(in_punches)  if in_punches  else None   # None → missed IN
            out_time_dt = max(out_punches) if out_punches else None   # None → missed OUT

        # ── Case 2: No log_type set on any punch ─────────────────────────────────
        elif no_type_punches:
            sorted_punches = sorted(no_type_punches)

            if len(sorted_punches) == 1:
                # Single ambiguous punch — guess direction via shift midpoint.
                single = sorted_punches[0]
                shift_mid = _get_shift_midpoint(employee, date)

                if shift_mid and single >= shift_mid:
                    # Punch falls in second half of shift → likely OUT → IN missing
                    in_time_dt  = None
                    out_time_dt = single
                else:
                    # Punch falls in first half (or no shift info) → likely IN → OUT missing
                    in_time_dt  = single
                    out_time_dt = None
            else:
                # Multiple no-type punches → positional pairing: first = IN, last = OUT
                in_time_dt  = sorted_punches[0]
                out_time_dt = sorted_punches[-1]

        else:
            return None, None

        return in_time_dt, out_time_dt

    except Exception as e:
        frappe.log_error(
            f"Error fetching checkin times for {employee} on {date}: {str(e)}",
            "Get Checkin Times Error",
        )
        return None, None


def _get_shift_midpoint(employee, att_date):
    """
    Return a datetime representing the midpoint of the employee's default shift on att_date.
    Used as a heuristic to classify a single no-log-type punch as IN or OUT.
    Returns None if shift information is unavailable.
    """
    try:
        default_shift = frappe.db.get_value("Employee", employee, "default_shift")
        if not default_shift:
            return None
        st = frappe.get_doc("Shift Type", default_shift)
        if not st.start_time or not st.end_time:
            return None

        ref_date = getdate(att_date)
        # st.start_time / st.end_time are timedelta objects in Frappe
        shift_start_dt = datetime.combine(ref_date, (datetime.min + st.start_time).time())
        shift_end_dt   = datetime.combine(ref_date, (datetime.min + st.end_time).time())
        return shift_start_dt + (shift_end_dt - shift_start_dt) / 2
    except Exception:
        return None
