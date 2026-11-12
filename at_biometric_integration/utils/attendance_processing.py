# at_biometric_integration/utils/attendance_processing.py

# import frappe
# from datetime import timedelta
# from frappe.utils import getdate, get_datetime, now_datetime, time_diff_in_hours

#     """
#     Resolve shift end datetime safely.
#     Priority:
#     1. Shift Type end_time
#     2. Attendance out_time
#     3. Fallback 18:30
#     """
#     try:
#         if shift:
#             shift_doc = frappe.get_doc("Shift Type", shift)
#             if shift_doc.end_time:
#                 return get_datetime(f"{attendance_date} {shift_doc.end_time}")
#     except Exception:
#         pass

#     out_time = frappe.db.get_value(
#         "Attendance",
#         {"employee": employee, "attendance_date": attendance_date},
#         "out_time"
#     )
#     if out_time:
#         return get_datetime(out_time)

#     return get_datetime(f"{attendance_date} 18:30:00")

# # ------------------------------------------------
# # Link Checkins
# # ------------------------------------------------
# def link_checkins_to_attendance(attendance_name, employee, attendance_date):
#     try:
#         checkins = frappe.get_all(
#             "Employee Checkin",
#             filters={
#                 "employee": employee,
#                 "time": ["between", [f"{attendance_date} 00:00:00", f"{attendance_date} 23:59:59"]]
#             },
#             fields=["name", "time"],
#             order_by="time asc"
#         )

#         if not checkins:
#             return

#         first = checkins[0]
#         last = checkins[-1]

#         for c in checkins:
#             update = {"attendance": attendance_name}
#             if c.name == first.name:
#                 update["log_type"] = "IN"
#             if c.name == last.name:
#                 update["log_type"] = "OUT"
#             frappe.db.set_value("Employee Checkin", c.name, update)

#     except Exception as e:
#         log_error(e, "link_checkins_to_attendance")

# # ------------------------------------------------
# # Realtime Processing
# # ------------------------------------------------
# def process_attendance_realtime(date=None):
#     processed = []
#     date = date or getdate()

#     try:
#         employees = frappe.db.sql_list("""
#             SELECT DISTINCT employee
#             FROM `tabEmployee Checkin`
#             WHERE DATE(time) = %s
#         """, (date,))

#         for emp in employees:
#             name = create_or_update_attendance(emp, date)
#             if name:
#                 processed.append(name)

#         frappe.db.commit()
#         return processed

#     except Exception as e:
#         log_error(e, "process_attendance_realtime")
#         return processed

# # ------------------------------------------------
# # Create / Update Attendance
# # ------------------------------------------------
# def create_or_update_attendance(employee, date):
#     try:
#         first = frappe.db.sql("""
#             SELECT time FROM `tabEmployee Checkin`
#             WHERE employee=%s AND DATE(time)=%s
#             ORDER BY time ASC LIMIT 1
#         """, (employee, date), as_dict=True)

#         last = frappe.db.sql("""
#             SELECT time FROM `tabEmployee Checkin`
#             WHERE employee=%s AND DATE(time)=%s
#             ORDER BY time DESC LIMIT 1
#         """, (employee, date), as_dict=True)

#         first = first[0]["time"] if first else None
#         last = last[0]["time"] if last else None

#         leave_status = get_leave_status(employee, date)
#         holiday_flag = is_holiday(employee, date)
#         shift = get_employee_shift(employee, date)

#         working_hours = 0.0
#         if first and last:
#             working_hours = calculate_working_hours(
#                 {"time": first},
#                 {"time": last}
#             )

#         status = determine_attendance_status(
#             working_hours,
#             leave_status,
#             holiday_flag
#         )

#         emp = frappe.get_doc("Employee", employee)
#         existing = frappe.db.get_value(
#             "Attendance",
#             {"employee": employee, "attendance_date": date},
#             "name"
#         )

#         if existing:
#             frappe.db.set_value("Attendance", existing, {
#                 "in_time": first,
#                 "out_time": last,
#                 "working_hours": working_hours,
#                 "status": status,
#                 "shift": shift
#             })
#             attendance_name = existing
#         else:
#             att = frappe.get_doc({
#                 "doctype": "Attendance",
#                 "employee": employee,
#                 "employee_name": emp.employee_name,
#                 "attendance_date": date,
#                 "company": emp.company,
#                 "shift": shift,
#                 "status": status,
#                 "working_hours": working_hours,
#                 "in_time": first,
#                 "out_time": last
#             })
#             att.insert(ignore_permissions=True)
#             attendance_name = att.name

#         link_checkins_to_attendance(attendance_name, employee, date)

#         attempt_auto_submit(attendance_name)

#         return attendance_name

#     except Exception as e:
#         log_error(f"{employee} {date}: {e}", "create_or_update_attendance")
#         return None

# # ------------------------------------------------
# # Auto Submit Logic (RESTORED)
# # ------------------------------------------------
# def attempt_auto_submit(attendance_name):
#     try:
#         settings = get_attendance_settings()
#         att = frappe.get_doc("Attendance", attendance_name)

#         if att.docstatus == 1:
#             return

#         if has_pending_regularization(att):
#             return

#         shift_end = get_shift_end_datetime(
#             att.employee,
#             att.attendance_date,
#             att.shift
#         )

#         now = now_datetime()

#         # Rule 1: Shift End + 4 hours
#         if now >= (shift_end + timedelta(hours=4)):
#             if can_auto_submit(att):
#                 att.submit(ignore_permissions=True)
#                 return

#         # Rule 2: Regularization window expired
#         if settings.enable_regularization:
#             reg_to = float(settings.regularization_to_hours or 0)
#             if now >= (shift_end + timedelta(hours=reg_to)):
#                 if can_auto_submit(att):
#                     att.submit(ignore_permissions=True)
#                     return

#     except Exception as e:
#         log_error(e, "attempt_auto_submit")

# # ------------------------------------------------
# # Absent Marking
# # ------------------------------------------------
# def mark_absent_for_date(employee, date):
#     try:
#         has_checkin = frappe.db.exists(
#             "Employee Checkin",
#             {
#                 "employee": employee,
#                 "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
#             }
#         )

#         has_att = frappe.db.exists(
#             "Attendance",
#             {"employee": employee, "attendance_date": date}
#         )

#         leave_status = get_leave_status(employee, date)
#         holiday_flag = is_holiday(employee, date)

#         if not has_checkin and not has_att and not holiday_flag:
#             emp = frappe.get_doc("Employee", employee)
#             att = frappe.get_doc({
#                 "doctype": "Attendance",
#                 "employee": employee,
#                 "employee_name": emp.employee_name,
#                 "attendance_date": date,
#                 "company": emp.company,
#                 "status": leave_status[0] or "Absent",
#                 "leave_type": leave_status[1],
#                 "leave_application": leave_status[2]
#             })
#             att.insert(ignore_permissions=True)
#             frappe.db.commit()

#     except Exception as e:
#         log_error(e, "mark_absent_for_date")

import frappe
from datetime import datetime, timedelta
from frappe.utils import get_datetime, now_datetime, getdate, add_days

# helpers expected to exist in your repo (you referenced them before)
from .helpers import get_leave_status, is_holiday, calculate_working_hours, determine_attendance_status, get_employee_shift, time_to_hours
from .attendance_links import pick_checkin

# ------------------
# ASSUMPTIONS / TODO
# - Attendance doc has fields: employee, attendance_date (date), in_time (datetime/time), out_time (datetime/time),
#   working_hours (float), status (Present/Half Day/etc.), shift (name of Shift Type or string).
# - Shift information (if used) is in a doctype called "Shift Type" with fields start_time and end_time (HH:MM or time)
#   If your shift model differs, change get_shift_end_datetime().
# - Attendance Settings single doctype contains the keys you listed (names used exactly as fields).
# - calculate_working_hours(first_checkin, last_checkin) returns float hours.
# ------------------


def get_attendance_settings():
    """Fetch settings from single doctype. Provide defaults when missing."""
    try:
        s = frappe.get_single("Attendance Settings")
    except Exception:
        # Return sensible defaults if the doctype doesn't exist
        return frappe._dict({
            "enable_regularization": False,
            "regularization_from_hours": 0,
            "regularization_to_hours": 24,
            "min_working_hours": 0,
            "checkin_grace_start_minutes": 0,
            "checkout_grace_end_minutes": 0,
            "attendance_grace_start_mins": 0,
            "attendance_grace_end_mins": 0,
            "auto_submit_after_shift_hours": 0,
        })

    return frappe._dict({
        "enable_regularization": getattr(s, "enable_regularization", False),
        "regularization_from_hours": getattr(s, "regularization_from_hours", 0),
        "regularization_to_hours": getattr(s, "regularization_to_hours", 0),
        "min_working_hours": time_to_hours(getattr(s, "min_working_hours", 0)),
        "checkin_grace_start_minutes": getattr(s, "checkin_grace_start_minutes", 0),
        "checkout_grace_end_minutes": getattr(s, "checkout_grace_end_minutes", 0),
        "attendance_grace_start_mins": getattr(s, "attendance_grace_start_mins", 0),
        "attendance_grace_end_mins": getattr(s, "attendance_grace_end_mins", 0),
        "auto_submit_after_shift_hours": float(getattr(s, "auto_submit_after_shift_hours", 0) or 0),
    })


def get_shift_end_datetime(employee, attendance_date, shift_name=None):
    """
    Determine the expected shift end datetime for this employee on attendance_date.
    Priority:
    1. Shift passed in argument or on Attendance doc
    2. Employee's assigned shift (Shift Assignment active for attendance_date, or Employee.default_shift)
    3. Fallback 18:30:00
    """
    end_time = None
    start_time = None

    # 1. Try explicit shift_name
    if shift_name:
        try:
            shift = frappe.get_doc("Shift Type", shift_name)
            end_time = getattr(shift, "end_time", None) or getattr(shift, "end", None)
            start_time = getattr(shift, "start_time", None) or getattr(shift, "start", None)
        except Exception:
            pass

    # 2. Try employee shift assignment or default_shift
    if not end_time and employee:
        try:
            shift_doc = get_employee_shift(employee, attendance_date)
            if shift_doc:
                end_time = getattr(shift_doc, "end_time", None) or getattr(shift_doc, "end", None)
                start_time = getattr(shift_doc, "start_time", None) or getattr(shift_doc, "start", None)
        except Exception:
            pass

    # 3. Fallback default 18:30:00
    if not end_time:
        end_time = "18:30:00"

    # Combine date + end_time
    end_dt = get_datetime(f"{attendance_date} {str(end_time)}")
    if start_time:
        start_dt = get_datetime(f"{attendance_date} {str(start_time)}")
        if end_dt < start_dt:
            # Overnight shift: shift end is on the following day
            end_dt += timedelta(days=1)

    return end_dt


def get_working_hours_seconds(val):
    """Convert working_hours (str 'HH:MM:SS', timedelta, time, float) to total seconds."""
    if not val:
        return 0
    if isinstance(val, timedelta):
        return int(val.total_seconds())
    if hasattr(val, "hour") and hasattr(val, "minute"):
        return val.hour * 3600 + val.minute * 60 + getattr(val, "second", 0)
    if isinstance(val, (int, float)):
        return int(float(val) * 3600)
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return 0
        parts = val.split(":")
        if len(parts) >= 2:
            try:
                h = int(float(parts[0]))
                m = int(float(parts[1]))
                s = int(float(parts[2])) if len(parts) > 2 else 0
                return h * 3600 + m * 60 + s
            except ValueError:
                return 0
        try:
            return int(float(val) * 3600)
        except ValueError:
            return 0
    return 0


def update_attendance_on_checkin(doc, method=None):
    """
    Live Attendance Updater:
    Triggered immediately when an Employee Checkin is inserted or deleted.
    Instantly recalculates and updates in_time, out_time, and working_hours on Attendance
    for that specific employee and date without waiting for the batch scheduler.
    """
    if not doc.get("employee") or not doc.get("time"):
        return

    try:
        employee = doc.employee
        checkin_date = getdate(doc.time)

        # Get all checkins for this employee on this date
        checkins = frappe.get_all(
            "Employee Checkin",
            filters={
                "employee": employee,
                "time": ["between", [f"{checkin_date} 00:00:00", f"{checkin_date} 23:59:59"]]
            },
            fields=["name", "time", "log_type"],
            order_by="time asc",
            limit_page_length=500
        )

        in_punches = []
        out_punches = []
        all_punches = []

        for c in checkins:
            t = c.get("time")
            if not t:
                continue
            dt = get_datetime(t)
            all_punches.append(dt)
            ltype = (c.get("log_type") or "").strip().upper()
            if ltype == "IN":
                in_punches.append(dt)
            elif ltype == "OUT":
                out_punches.append(dt)

        first_time = min(in_punches) if in_punches else (min(all_punches) if all_punches else None)
        last_time = max(out_punches) if out_punches else (max(all_punches) if all_punches else None)

        hours = "00:00:00"
        if first_time and last_time and first_time != last_time:
            hours = calculate_working_hours(first_time, last_time)

        leave_status = get_leave_status(employee, checkin_date)
        holiday_flag = is_holiday(employee, checkin_date)
        status = determine_attendance_status(hours, leave_status, holiday_flag)

        existing_draft = frappe.db.get_value(
            "Attendance",
            {"employee": employee, "attendance_date": checkin_date, "docstatus": 0},
            "name"
        )
        existing_submitted = frappe.db.get_value(
            "Attendance",
            {"employee": employee, "attendance_date": checkin_date, "docstatus": 1},
            "name"
        )

        if existing_draft:
            update_data = {
                "in_time": first_time,
                "out_time": last_time,
                "working_hours": hours,
            }
            if status != "Holiday":
                update_data["status"] = status

            if checkins:
                first_chk = pick_checkin(checkins, attendance_name=existing_draft, in_time=first_time)
                if first_chk:
                    update_data["employee_checkin"] = first_chk

            frappe.db.set_value("Attendance", existing_draft, update_data, update_modified=True)

            for c in checkins:
                frappe.db.set_value("Employee Checkin", c.name, "attendance", existing_draft, update_modified=False)

        elif existing_submitted:
            update_data = {}
            if first_time:
                update_data["in_time"] = first_time
            if last_time:
                update_data["out_time"] = last_time
            if hours:
                update_data["working_hours"] = hours

            if update_data:
                frappe.db.set_value("Attendance", existing_submitted, update_data, update_modified=False)
        else:
            shift_doc = get_employee_shift(employee, checkin_date)
            shift_name = shift_doc.name if shift_doc else frappe.db.get_value("Employee", employee, "default_shift")
            company = frappe.db.get_value("Employee", employee, "company")
            emp_name = frappe.db.get_value("Employee", employee, "employee_name")

            doc_args = {
                "doctype": "Attendance",
                "employee": employee,
                "employee_name": emp_name,
                "attendance_date": checkin_date,
                "company": company,
                "shift": shift_name,
                "in_time": first_time,
                "out_time": last_time,
                "working_hours": hours,
                "status": "Absent" if status == "Holiday" else status,
            }
            if leave_status and leave_status[0]:
                doc_args["leave_type"] = leave_status[1]
                doc_args["leave_application"] = leave_status[2]

            new_att = frappe.get_doc(doc_args)
            new_att.flags.ignore_permissions = True
            new_att.insert()

            for c in checkins:
                frappe.db.set_value("Employee Checkin", c.name, "attendance", new_att.name, update_modified=False)

    except Exception:
        frappe.log_error(title=f"Live Attendance Update Error: {doc.get('employee')}", message=frappe.get_traceback())


def check_min_working_hours_on_submit(doc, method=None):
    """
    Validation on Attendance submit:
    Check if 'working_hours' < 8:45:00 (31,500 seconds) -> update status = 'Work From Home'.
    (Approved leaves with leave application are preserved).
    """
    # Do not override approved leave applications
    if doc.status == "On Leave" and (doc.get("leave_application") or doc.get("leave_type")):
        return

    # Calculate working_hours from in_time and out_time if available
    if doc.get("in_time") and doc.get("out_time") and (not doc.get("working_hours") or doc.get("working_hours") == "00:00:00"):
        doc.working_hours = calculate_working_hours(doc.in_time, doc.out_time)

    work_seconds = get_working_hours_seconds(doc.get("working_hours"))
    REQUIRED_SECONDS = 8 * 3600 + 45 * 60  # 8:45:00 = 31,500 seconds

    if work_seconds < REQUIRED_SECONDS:
        doc.status = "Work From Home"
    elif doc.status not in ["Present", "On Leave", "Work From Home"]:
        doc.status = "Present"


def auto_submit_attendance_doc(att_doc, settings=None):
    """
    Submit a single attendance document if it meets submission criteria.
    Returns True if submitted.
    """
    try:
        doc_name = att_doc.name if hasattr(att_doc, "name") else att_doc.get("name")
        if not doc_name:
            return False

        doc = frappe.get_doc("Attendance", doc_name)
        if doc.docstatus == 1:
            return False

        # 1. Skip Holiday status - Frappe HRMS Attendance does not allow 'Holiday' status
        if doc.status == "Holiday":
            return False

        # Note: Do not wait for Attendance Regularization - submit immediately per policy

        # 2. Check for duplicates: if another submitted attendance exists, don't throw DuplicateAttendanceError
        duplicate_submitted = frappe.db.get_value(
            "Attendance",
            {
                "employee": doc.employee,
                "attendance_date": doc.attendance_date,
                "docstatus": 1,
                "name": ["!=", doc.name]
            },
            "name"
        )
        if duplicate_submitted:
            frappe.logger().info(f"Duplicate submitted attendance {duplicate_submitted} already exists for {doc.employee} on {doc.attendance_date}. Skipping draft {doc.name}.")
            return False

        # 3. Ensure working_hours is formatted properly if in_time and out_time exist
        if doc.in_time and doc.out_time:
            doc.working_hours = calculate_working_hours(doc.in_time, doc.out_time)
        elif not doc.working_hours:
            doc.working_hours = "00:00:00"

        # 4. Check if working_hours < 8:45:00 -> update status = 'Work From Home'
        is_on_leave = (doc.status == "On Leave" and (doc.get("leave_application") or doc.get("leave_type")))
        if not is_on_leave:
            work_seconds = get_working_hours_seconds(doc.working_hours)
            REQUIRED_SECONDS = 8 * 3600 + 45 * 60  # 8:45:00 = 31,500 seconds
            if work_seconds < REQUIRED_SECONDS:
                doc.status = "Work From Home"
            else:
                doc.status = "Present"

        # 5. Standard Frappe HRMS status validation check before submitting
        valid_statuses = ["Present", "Absent", "On Leave", "Half Day", "Work From Home"]
        if doc.status not in valid_statuses:
            doc.status = "Work From Home"

        # 6. Check employee status
        emp_status = frappe.db.get_value("Employee", doc.employee, "status")
        if emp_status != "Active":
            return False

        doc.flags.ignore_permissions = True
        doc.submit()
        frappe.publish_realtime(event="attendance_auto_submitted", message={"name": doc.name})
        return True
    except Exception as e:
        frappe.log_error(
            title=f"Attendance Auto Submit Error: {getattr(att_doc, 'name', '')}",
            message=frappe.get_traceback()
        )
        return False


def auto_submit_due_attendances():
    """
    Find attendance records that are due for auto-submission and submit them.

    Trigger:
      Current time >= (shift_end_datetime + auto_submit_after_shift_hours)

    Example:
      shift end = 18:30, auto_submit_after_shift_hours = 4  →  cutoff = 22:30
      At 22:30 or later ALL draft Attendance records for that day are submitted.

    The value of auto_submit_after_shift_hours is read directly from
    Attendance Settings — nothing is hardcoded here.

    This function is invoked from the scheduler every 10 minutes (*/10 * * * *).
    """
    settings = get_attendance_settings()
    now = now_datetime()

    # Read straight from Attendance Settings — no hardcoded fallback
    auto_submit_hours = float(settings.auto_submit_after_shift_hours or 0)

    # Feature is disabled when field is 0 or not configured
    if not auto_submit_hours:
        return []

    # Query all open (draft) attendance records excluding Holiday status
    open_att = frappe.get_all("Attendance", filters={"docstatus": 0, "status": ["!=", "Holiday"]}, fields=[
        "name", "employee", "attendance_date", "in_time", "out_time", "working_hours", "status", "shift"
    ], limit_page_length=50000)

    submitted_any = []
    for a in open_att:
        try:
            shift_end_dt = get_shift_end_datetime(a.employee, a.attendance_date, a.get("shift"))
            cutoff_dt = shift_end_dt + timedelta(hours=auto_submit_hours)

            # Once current time passes the cutoff, submit ALL records for that day
            if now >= cutoff_dt:
                if auto_submit_attendance_doc(frappe._dict(a), settings):
                    submitted_any.append(a.name)

        except Exception as e:
            frappe.log_error(
                title=f"Error evaluating auto-submit for attendance {a.get('name')}",
                message=frappe.get_traceback()
            )

    if submitted_any:
        frappe.db.commit()

    return submitted_any


# ------------------------
# Realtime processing (when checkins exist)
# ------------------------
def process_attendance_realtime(from_date=None, to_date=None):
    """
    Recreates the attendance records from Employee Checkin table per employee per date.
    Supports date ranges and ensures all active employees have records.
    Also dynamically re-processes all existing DRAFT attendance records.
    """
    from frappe.utils import getdate, add_days
    
    # If dates not provided, look at last 2 days by default to be safe
    if not to_date:
        to_date = getdate()
    if not from_date:
        from_date = add_days(to_date, -1)
    
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    created_or_updated = []

    # 1. Process for the specific date range (Active Employees)
    employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "default_shift"])
    for emp in employees:
        try:
            process_employee_attendance_realtime(emp.name, emp.default_shift or "", created_or_updated, from_date, to_date)
        except Exception as e:
            frappe.log_error(f"{emp.name} attendance error: {e}", "Realtime Attendance Error")

    # 2. Dynamically re-process all existing DRAFT attendance records (even if older)
    draft_attendances = frappe.get_all("Attendance", filters={"docstatus": 0}, fields=["employee", "attendance_date", "shift"])
    for att in draft_attendances:
        try:
            # Skip if already processed in step 1 (to avoid redundant DB hits)
            if from_date <= getdate(att.attendance_date) <= to_date:
                continue
                
            process_employee_attendance_realtime(
                att.employee, 
                att.shift or "", 
                created_or_updated, 
                att.attendance_date, 
                att.attendance_date
            )
        except Exception as e:
            frappe.log_error(f"Draft re-process error: {att.employee} on {att.attendance_date}: {e}", "Draft Re-process Error")

    frappe.db.commit()
    return created_or_updated


def process_employee_attendance_realtime(employee, shift, created_list=None, from_date=None, to_date=None):
    from frappe.utils import getdate, add_days
    
    if not from_date or not to_date:
        # Fallback if range not provided
        to_date = getdate()
        from_date = to_date
    
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    # Fetch all checkins for the range at once
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]]
        },
        fields=["name", "time", "log_type", "attendance"],
        order_by="time asc", 
        limit_page_length=50000
    )

    by_date = {}
    for c in checkins:
        d = get_datetime(c.get('time')).date()
        by_date.setdefault(d, []).append(c)

    # Iterate through every single day in the range
    curr_date = from_date
    while curr_date <= to_date:
        daily = by_date.get(curr_date, [])
        
        hours = "00:00:00"
        first_time = None
        last_time = None
        
        if daily:
            # Find FIRST IN punch and LAST OUT punch (matching get_checkin_times_dynamic logic)
            in_punches = []
            out_punches = []
            all_punches = []
            
            for checkin in daily:
                log_type = (checkin.get('log_type') or '').strip().upper()
                checkin_time = checkin.get('time')
                
                # Ensure we have a datetime object for comparison
                if checkin_time:
                    checkin_dt = get_datetime(checkin_time)
                    all_punches.append(checkin_dt)
                    
                    if log_type == "IN":
                        in_punches.append(checkin_dt)
                    elif log_type == "OUT":
                        out_punches.append(checkin_dt)
            
            # Use FIRST IN punch if available, otherwise use earliest punch
            if in_punches:
                first_time = min(in_punches)  # First IN punch
            elif all_punches:
                first_time = min(all_punches)  # Fallback to earliest
            
            # Use LAST OUT punch if available, otherwise use latest punch
            if out_punches:
                last_time = max(out_punches)  # Last OUT punch
            elif all_punches:
                last_time = max(all_punches)  # Fallback to latest
            
            if first_time and last_time:
                hours = calculate_working_hours(first_time, last_time)

        leave_status = get_leave_status(employee, curr_date)
        holiday_flag = is_holiday(employee, curr_date)
        
        # determine_attendance_status handles 0 hours as Absent unless holiday/leave
        status = determine_attendance_status(hours, leave_status, holiday_flag)

        # Check for existing attendance (both draft and submitted)
        existing_draft = frappe.db.exists("Attendance", {
            "employee": employee, 
            "attendance_date": curr_date,
            "docstatus": 0
        })
        
        existing_submitted = frappe.db.exists("Attendance", {
            "employee": employee, 
            "attendance_date": curr_date,
            "docstatus": 1
        })

        if existing_draft:
            # Update draft attendance
            doc = frappe.get_doc("Attendance", existing_draft)
            doc.in_time = first_time
            doc.out_time = last_time
            doc.working_hours = hours
            
            # BYPASS: controller prevents "Holiday" status
            actual_status = status
            if status == "Holiday":
                doc.status = "Absent"
            else:
                doc.status = status
                
            doc.shift = shift
            
            # Link leave if applicable
            if leave_status and leave_status[0]:
                doc.leave_type = leave_status[1]
                doc.leave_application = leave_status[2]
            else:
                doc.leave_type = None
                doc.leave_application = None

            doc.flags.ignore_permissions = True
            doc.save()
            
            if actual_status == "Holiday":
                doc.db_set("status", "Holiday")
            
            if created_list is not None:
                created_list.append(existing_draft)
        elif existing_submitted:
            # Update submitted attendance - use db_set to update fields directly
            # This ensures we update the out_time even if attendance is submitted
            update_fields = {}
            if first_time:
                update_fields["in_time"] = first_time
            if last_time:
                update_fields["out_time"] = last_time
            if hours is not None:
                update_fields["working_hours"] = hours

            # Link Employee Checkin (validate hook does not run on db_set)
            if daily and not frappe.db.get_value(
                "Attendance", existing_submitted, "employee_checkin", cache=False
            ):
                checkin = pick_checkin(daily, attendance_name=existing_submitted, in_time=first_time)
                if checkin:
                    update_fields["employee_checkin"] = checkin

            if update_fields:
                frappe.db.set_value("Attendance", existing_submitted, update_fields, update_modified=False)
            
            if created_list is not None:
                created_list.append(existing_submitted)
        else:
            # Create new attendance record
            if not existing_submitted:
                actual_status = status
                doc_args = {
                    "doctype": "Attendance",
                    "employee": employee,
                    "attendance_date": curr_date,
                    "shift": shift,
                    "in_time": first_time,
                    "out_time": last_time,
                    "working_hours": hours,
                    "status": "Absent" if status == "Holiday" else status,
                    "company": frappe.db.get_value("Employee", employee, "company")
                }
                if leave_status and leave_status[0]:
                    doc_args["leave_type"] = leave_status[1]
                    doc_args["leave_application"] = leave_status[2]

                doc = frappe.get_doc(doc_args)
                doc.flags.ignore_permissions = True
                doc.insert()
                
                if actual_status == "Holiday":
                    doc.db_set("status", "Holiday")

                if created_list is not None:
                    created_list.append(doc.name)
        
        curr_date = add_days(curr_date, 1)

    # no commit here: caller should commit once for batch operations


def auto_submit_new_attendances(attendance_names):
    """
    Called after new Attendance docs are created. This checks each new attendance doc
    and auto-submits immediately if shift_end + auto_submit_after_shift_hours has already passed.
    """
    if not attendance_names:
        return []

    settings = get_attendance_settings()
    submitted = []
    auto_submit_hours = float(settings.auto_submit_after_shift_hours or 0)
    if not auto_submit_hours:
        return []
    now = now_datetime()

    for name in attendance_names:
        try:
            doc = frappe.get_doc("Attendance", name)
            if doc.docstatus == 1:
                continue

            shift_end_dt = get_shift_end_datetime(doc.employee, doc.attendance_date, doc.shift)
            cutoff_dt = shift_end_dt + timedelta(hours=auto_submit_hours)

            if now >= cutoff_dt:
                if auto_submit_attendance_doc(doc, settings):
                    submitted.append(name)
        except Exception as e:
            frappe.log_error(title=f"Error in auto_submit_new_attendances for {name}", message=frappe.get_traceback())

    if submitted:
        frappe.db.commit()
    return submitted


# ------------------------
# Daily midnight: generate Absent records for Active employees
# ------------------------
def generate_daily_absent():
    """
    Called at 12:00 AM every day via cron scheduler.
    Creates a draft Attendance record with status = 'Absent' for every
    Active employee that does NOT already have an Attendance record for today.

    On Leave employees get their corresponding status.
    Holidays are skipped as holidays do not use Attendance records in Frappe HRMS.
    """
    today = getdate()

    # Fetch only Active employees
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "company", "default_shift"],
    )

    created = []
    for emp in employees:
        try:
            # Skip if an attendance record already exists (draft or submitted)
            if frappe.db.exists(
                "Attendance",
                {"employee": emp.name, "attendance_date": today},
            ):
                continue

            # Skip holidays (Frappe HRMS uses Holiday List, 'Holiday' is not a valid Attendance status)
            if is_holiday(emp.name, today):
                continue

            leave_status = get_leave_status(emp.name, today)

            if leave_status and leave_status[0]:
                status = leave_status[0]       # "On Leave" or "Half Day"
                leave_type = leave_status[1]
                leave_application = leave_status[2]
            else:
                status = "Absent"
                leave_type = None
                leave_application = None

            # Resolve employee's shift for today
            shift_doc = get_employee_shift(emp.name, today)
            shift_name = shift_doc.name if shift_doc else (emp.default_shift or None)

            att = frappe.get_doc({
                "doctype": "Attendance",
                "employee": emp.name,
                "employee_name": emp.employee_name,
                "attendance_date": today,
                "company": emp.company,
                "status": status,
                "shift": shift_name,
                "leave_type": leave_type,
                "leave_application": leave_application,
            })
            att.flags.ignore_permissions = True
            att.insert()
            created.append(att.name)

        except Exception:
            frappe.log_error(
                title="generate_daily_absent Error",
                message=frappe.get_traceback(),
            )

    if created:
        frappe.db.commit()

    return created