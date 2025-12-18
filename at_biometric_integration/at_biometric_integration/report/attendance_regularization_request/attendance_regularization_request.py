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

    if filters.get("from_date") and filters.get("to_date"):
        conditions.append(["attendance_date", "between", [filters.from_date, filters.to_date]])
    else:
        to_date = date.today()
        from_date = to_date - timedelta(days=7)
        conditions.append(["attendance_date", "between", [from_date, to_date]])

    # ---------------- Fetch Attendance ----------------
    attendance_records = frappe.get_all(
        "Attendance",
        filters=conditions,
        fields=["name", "employee", "attendance_date", "in_time", "out_time", "working_hours", "status"],
        order_by="attendance_date asc"
    )

    today_dt = datetime.now()

    for record in attendance_records:
        emp = record.employee
        employee_name = frappe.get_value("Employee", emp, "employee_name") or ""
        att_date = getdate(record.attendance_date)
        shift_start, shift_end = get_shift_from_default_shift(emp)

        in_time = format_time_only(record.in_time)
        out_time = format_time_only(record.out_time)

        formatted_working_hours = "-"
        if record.working_hours:
            try:
                wh = float(record.working_hours)
                hrs = int(wh)
                mins = int(round((wh - hrs) * 60))
                formatted_working_hours = f"{hrs:02d}:{mins:02d}"
            except:
                formatted_working_hours = str(record.working_hours)

        # Missed punch detection
        missed_punch = "-"
        if not in_time and not out_time:
            missed_punch = "BOTH"
        elif not in_time:
            missed_punch = "IN"
        elif not out_time:
            missed_punch = "OUT"

        # ---------------- Dynamic Hours & Status ----------------
        # 1. Fetch Checkins if missing (Fix for historical data)
        # If DB says invalid (None or 0) for hours, AND we lack time data, try to fetch from checkins
        if (not record.working_hours or record.working_hours == 0) and (not record.in_time or not record.out_time):
            cin, cout = get_checkin_times(emp, att_date)
            if cin:
                record.in_time = cin
                record.in_time_fetched = True  # marker
                in_time = format_time_only(cin)
            if cout:
                record.out_time = cout
                record.out_time_fetched = True
                out_time = format_time_only(cout)

        # 2. Calculate Working Hours if missing
        # Now we might have times from DB or fetched above
        if (not record.working_hours or record.working_hours == 0) and record.in_time and record.out_time:
            w_hours = calculate_working_hours(record.in_time, record.out_time)
            if w_hours > 0:
                record.working_hours = w_hours
                formatted_working_hours = f"{int(w_hours):02d}:{int(round((w_hours - int(w_hours)) * 60)):02d}"

        # 3. Get Leave & Holiday Info (using helpers to enable dynamic status)
        leave_info = get_leave_status(emp, att_date) # (status, type, name)
        holiday_flag = is_holiday(emp, att_date)
        
        # 3. Determine Status dynamically based on (new) hours
        # Only override if we have calculated hours or if status is not finalized
        if record.working_hours or not record.status:
            # pass 0.0 if None
            wh_val = float(record.working_hours or 0.0)
            status = determine_attendance_status(wh_val, leave_info, holiday_flag)
        else:
            status = record.status or ("Missed Punch" if missed_punch != "-" else "Present")

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
                elif record.working_hours and float(record.working_hours) < min_working_hours:
                    eligible = True
                    remarks.append(f"Eligible: Working hours below {min_working_hours} hours")
                # (4) Grace time logic for check-in window
                elif check_shift_checkin_grace(record, shift_start, shift_end, checkin_grace_start, checkout_grace_end):
                    eligible = True
                    remarks.append("Eligible: Check-in missing within grace window")
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
        if eligible and enable_notifications:
            send_regularization_notification(emp, att_date, notification_template)

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

def check_shift_checkin_grace(record, shift_start, shift_end, grace_start, grace_end):
    """Check if no check-in was found between (shift_start - grace_start) and (shift_end - grace_end)."""
    if not shift_start or not shift_end:
        return False
    try:
        if not record.in_time:
            return True
        in_dt = get_datetime(record.in_time)
        shift_start_dt = datetime.combine(getdate(record.attendance_date), shift_start)
        shift_end_dt = datetime.combine(getdate(record.attendance_date), shift_end)
        if in_dt < (shift_start_dt + timedelta(minutes=grace_start)) or in_dt > (shift_end_dt - timedelta(minutes=grace_end)):
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
    current_date = start_date    return total_hours

def get_checkin_times(employee, date):
    """Return earliest and latest checkin times for the employee on the given date (from summary report logic)."""
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
    return min(times), max(times)    total_hours = 0

    while current_date <= end_datetime.date():
        if current_date.weekday() < 5:  # 0 = Monday, 6 = Sunday
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

