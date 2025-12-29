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
from frappe.utils import get_datetime, now_datetime

# helpers expected to exist in your repo (you referenced them before)
from .helpers import (
    get_leave_status, 
    is_holiday, 
    calculate_working_hours, 
    determine_attendance_status,
    get_last_checkout_from_previous_days,
    is_working_day
)

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
            "min_working_hours": 4,
            "checkin_grace_start_minutes": 0,
            "checkout_grace_end_minutes": 0,
            "attendance_grace_start_mins": 0,
            "attendance_grace_end_mins": 0,
        })

    return frappe._dict({
        "enable_regularization": getattr(s, "enable_regularization", False),
        "regularization_from_hours": getattr(s, "regularization_from_hours", 0),
        "regularization_to_hours": getattr(s, "regularization_to_hours", 24),
        "min_working_hours": getattr(s, "min_working_hours", 4),
        "checkin_grace_start_minutes": getattr(s, "checkin_grace_start_minutes", 0),
        "checkout_grace_end_minutes": getattr(s, "checkout_grace_end_minutes", 0),
        "attendance_grace_start_mins": getattr(s, "attendance_grace_start_mins", 0),
        "attendance_grace_end_mins": getattr(s, "attendance_grace_end_mins", 0),
    })


def get_shift_end_datetime(employee, attendance_date, shift_name):
    """
    Try to determine the expected shift end datetime for this employee on attendance_date.
    - First try to read Shift Type (end_time) by name
    - If shift_name absent or Shift Type missing, fall back to using attendance.out_time (if exists)
    - If still missing, assume a default shift end at 18:30 (6:30pm) local date (adjustable)
    """
    # try Shift Type
    try:
        if shift_name:
            # Shift Type might store times as strings or time objects; we try common fields
            shift = frappe.get_doc("Shift Type", shift_name)
            end_time = getattr(shift, "end_time", None) or getattr(shift, "end", None)
            start_time = getattr(shift, "start_time", None) or getattr(shift, "start", None)
            if end_time:
                # combine date + end_time
                dt = get_datetime(f"{attendance_date} {str(end_time)}")
                return dt
    except Exception:
        # no shift found, continue to fallback
        pass

    # fallback: try to use any existing attendance out_time
    att = frappe.get_all("Attendance",
                         filters={"employee": employee, "attendance_date": attendance_date},
                         fields=["out_time"], limit_page_length=1)
    if att and att[0].get("out_time"):
        return get_datetime(att[0].out_time)

    # final fallback: assume 18:30 local time
    fallback = get_datetime(f"{attendance_date} 18:30:00")
    return fallback


def auto_submit_attendance_doc(att_doc, settings):
    """
    Submit a single attendance document if it meets submission criteria.
    Returns True if submitted.
    """
    try:
        # Skip already submitted
        if att_doc.docstatus == 1:
            return False

        # compute working_hours if missing
        working_hours = getattr(att_doc, "working_hours", None)
        if working_hours is None:
            # try to compute from in_time/out_time if available
            if att_doc.in_time and att_doc.out_time:
                working_hours = calculate_working_hours(att_doc.in_time, att_doc.out_time)
            else:
                working_hours = 0.0

        # Rule: require at least min_working_hours
        if working_hours < settings.min_working_hours:
            # Not enough hours to be auto-submitted as Present / Half-day
            return False

        # If reached here, submit
        doc = frappe.get_doc("Attendance", att_doc.name)
        # update working_hours and status to reflect calculation (defensive)
        doc.working_hours = working_hours
        # choose status based on hours (same logic you used earlier)
        doc.status = "Present" if working_hours >= settings.min_working_hours else "Half Day"

        # Submit with ignore permissions to allow scheduler/whitelisted calls to submit
        doc.flags.ignore_permissions = True
        doc.submit()
        frappe.db.commit()
        frappe.publish_realtime(event="attendance_auto_submitted", message={"name": doc.name})
        return True
    except Exception as e:
        frappe.log_error(f"Auto-submit error for {getattr(att_doc, 'name', '')}: {e}", "Attendance Auto Submit")
        return False


def auto_submit_due_attendances():
    """
    Find attendance records that are due for auto-submission and submit them.
    Two triggers:
    1) shift end + 4 hours have passed
    2) regularization period ended (using regularization_to_hours from settings)
    This function can be invoked from scheduler periodically (eg: every 30 minutes).
    """
    settings = get_attendance_settings()
    now = now_datetime()

    # query open attendance records (docstatus = 0)
    open_att = frappe.get_all("Attendance", filters={"docstatus": 0}, fields=[
        "name", "employee", "attendance_date", "in_time", "out_time", "working_hours", "shift"
    ], limit_page_length=50000)

    submitted_any = []
    for a in open_att:
        try:
            # compute expected shift end datetime
            shift_end_dt = get_shift_end_datetime(a.employee, a.attendance_date, a.get("shift"))

            # condition 1: 4 hours after shift end
            if now >= (shift_end_dt + timedelta(hours=4)):
                # submit if meets working hours rule
                if (a.working_hours or 0) >= settings.min_working_hours:
                    if auto_submit_attendance_doc(frappe._dict(a), settings):
                        submitted_any.append(a.name)
                    continue

            # condition 2: regularization window passed
            if settings.enable_regularization:
                # Interpret regularization_to_hours as hours after shift_end allowed for regularization.
                # Once that window expires, auto-submit if working_hours >= min_working_hours.
                reg_to = float(settings.regularization_to_hours or 0)
                if now >= (shift_end_dt + timedelta(hours=reg_to)):
                    if (a.working_hours or 0) >= settings.min_working_hours:
                        if auto_submit_attendance_doc(frappe._dict(a), settings):
                            submitted_any.append(a.name)
                        continue
        except Exception as e:
            frappe.log_error(f"Error evaluating auto-submit for attendance {a.get('name')}: {e}", "Attendance Auto Submit")

    return submitted_any


# ------------------------
# Realtime processing (when checkins exist)
# ------------------------
def process_attendance_realtime(from_date=None, to_date=None):
    """
    Dynamically recreates attendance records from Employee Checkin table.
    Automatically finds all dates with checkins and ensures attendance exists.
    Works dynamically without requiring specific date ranges.
    """
    from frappe.utils import getdate, add_days
    
    created_or_updated = []
    
    # If specific dates provided, use them; otherwise find dates dynamically
    if from_date and to_date:
        from_date = getdate(from_date)
        to_date = getdate(to_date)
        
        # Process for the specific date range (Active Employees)
        employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "default_shift"])
        for emp in employees:
            try:
                process_employee_attendance_realtime(emp.name, emp.default_shift or "", created_or_updated, from_date, to_date)
            except Exception as e:
                frappe.log_error(f"{emp.name} attendance error: {e}", "Realtime Attendance Error")
    else:
        # DYNAMIC MODE: Find all dates with checkins and process them
        # This ensures no dates are missed, regardless of holidays/weekends
        
        # Step 1: Find all unique employee-date combinations that have checkins
        # This query is optimized and will work for any dataset size in production
        checkin_dates = frappe.db.sql("""
            SELECT DISTINCT 
                employee,
                DATE(time) as checkin_date
            FROM `tabEmployee Checkin`
            ORDER BY checkin_date DESC, employee
        """, as_dict=True)
        
        # Log for monitoring in production
        if checkin_dates:
            frappe.logger().info(f"Dynamic attendance processing: Found {len(checkin_dates)} employee-date combinations with checkins")
        
        if not checkin_dates:
            frappe.db.commit()
            return created_or_updated
        
        # Step 2: Group by employee and find date ranges to process
        employee_dates = {}
        for row in checkin_dates:
            emp = row.employee
            date = getdate(row.checkin_date)
            if emp not in employee_dates:
                employee_dates[emp] = []
            employee_dates[emp].append(date)
        
        # Step 3: Process each employee's dates
        employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "default_shift"])
        employee_dict = {e.name: e.default_shift or "" for e in employees}
        
        for emp, dates in employee_dates.items():
            if emp not in employee_dict:
                continue  # Skip inactive employees
            
            try:
                # Get unique sorted dates for this employee
                unique_dates = sorted(set(dates))
                if not unique_dates:
                    continue
                
                # Process from earliest to latest date
                # This ensures ALL dates with checkins are processed, including Dec 26th
                min_date = min(unique_dates)
                max_date = max(unique_dates)
                
                # Additional check: Find dates with checkins but missing attendance
                # This catches edge cases where attendance wasn't created
                dates_with_checkins = set(unique_dates)
                existing_attendance = frappe.db.sql("""
                    SELECT DISTINCT attendance_date 
                    FROM `tabAttendance` 
                    WHERE employee = %s 
                    AND attendance_date IN %s
                """, (emp, tuple(unique_dates)), as_dict=True)
                
                existing_dates = {getdate(a.attendance_date) for a in existing_attendance}
                missing_dates = dates_with_checkins - existing_dates
                
                # Process the full range (handles all dates including missing ones)
                process_employee_attendance_realtime(
                    emp, 
                    employee_dict[emp], 
                    created_or_updated, 
                    min_date, 
                    max_date
                )
                
                # Log if we found missing dates
                if missing_dates:
                    frappe.logger().info(f"Found {len(missing_dates)} missing attendance dates for {emp}: {sorted(missing_dates)}")
                    
            except Exception as e:
                frappe.log_error(f"{emp} dynamic attendance error: {e}", "Dynamic Attendance Error")

    # Step 4: Dynamically re-process all existing DRAFT attendance records
    draft_attendances = frappe.get_all("Attendance", filters={"docstatus": 0}, fields=["employee", "attendance_date", "shift"])
    processed_dates = set()  # Track already processed dates to avoid duplicates
    
    for att in draft_attendances:
        try:
            att_date = getdate(att.attendance_date)
            key = (att.employee, att_date)
            
            # Skip if already processed
            if key in processed_dates:
                continue
            
            # Check if this date was already processed in step 1 or 3
            if from_date and to_date:
                if from_date <= att_date <= to_date:
                    continue
            
            process_employee_attendance_realtime(
                att.employee, 
                att.shift or "", 
                created_or_updated, 
                att_date, 
                att_date
            )
            processed_dates.add(key)
        except Exception as e:
            frappe.log_error(f"Draft re-process error: {att.employee} on {att.attendance_date}: {e}", "Draft Re-process Error")

    frappe.db.commit()
    return created_or_updated


def backfill_all_missing_attendance():
    """
    Comprehensive backfill function to ensure ALL dates with checkins have attendance records.
    This function finds every date that has checkins but no attendance (or only submitted attendance),
    and creates/updates attendance records for them.
    """
    from frappe.utils import getdate
    
    frappe.logger().info("Starting comprehensive attendance backfill...")
    created_or_updated = []
    
    # Find all employee-date combinations with checkins
    checkin_dates = frappe.db.sql("""
        SELECT DISTINCT 
            employee,
            DATE(time) as checkin_date
        FROM `tabEmployee Checkin`
        ORDER BY checkin_date ASC, employee
    """, as_dict=True)
    
    if not checkin_dates:
        frappe.logger().info("No checkins found for backfill")
        return created_or_updated
    
    frappe.logger().info(f"Found {len(checkin_dates)} employee-date combinations with checkins")
    
    # Get all existing attendance records
    existing_attendance = frappe.db.sql("""
        SELECT DISTINCT employee, attendance_date
        FROM `tabAttendance`
    """, as_dict=True)
    
    existing_keys = {(a.employee, getdate(a.attendance_date)) for a in existing_attendance}
    
    # Find missing dates
    missing_dates = []
    for row in checkin_dates:
        emp = row.employee
        date = getdate(row.checkin_date)
        key = (emp, date)
        if key not in existing_keys:
            missing_dates.append((emp, date))
    
    frappe.logger().info(f"Found {len(missing_dates)} dates with checkins but no attendance")
    
    # Get employee shifts
    employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "default_shift"])
    employee_dict = {e.name: e.default_shift or "" for e in employees}
    
    # Process missing dates
    processed_count = 0
    for emp, date in missing_dates:
        if emp not in employee_dict:
            continue  # Skip inactive employees
        
        try:
            # Process this specific date
            process_employee_attendance_realtime(
                emp,
                employee_dict[emp],
                created_or_updated,
                date,
                date
            )
            processed_count += 1
            
            # Commit every 100 records to avoid long transactions
            if processed_count % 100 == 0:
                frappe.db.commit()
                frappe.logger().info(f"Processed {processed_count} dates so far...")
                
        except Exception as e:
            frappe.log_error(f"Error processing {emp} on {date}: {e}", "Backfill Attendance Error")
    
    frappe.db.commit()
    frappe.logger().info(f"Backfill completed. Processed {processed_count} dates. Created/Updated {len(created_or_updated)} attendance records")
    
    return created_or_updated


def process_employee_attendance_realtime(employee, shift, created_list=None, from_date=None, to_date=None):
    from frappe.utils import getdate, add_days
    
    if not from_date or not to_date:
        # Fallback if range not provided
        to_date = getdate()
        from_date = to_date
    
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    
    # Expand the date range to include previous days (up to 7 days back)
    # This helps find last checkout from previous working days
    extended_from_date = from_date - timedelta(days=7)

    # Fetch all checkins for the extended range at once
    # Using high limit to handle large datasets in production
    # If an employee has more than 50k checkins in a date range, they'll need to process in batches
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [f"{extended_from_date} 00:00:00", f"{to_date} 23:59:59"]]
        },
        fields=["name", "time", "log_type"],
        order_by="time asc", 
        limit_page_length=50000  # Sufficient for most cases (years of data)
    )
    
    # Log warning if we hit the limit (rare case)
    if len(checkins) == 50000:
        frappe.logger().warning(
            f"Employee {employee} has 50k+ checkins between {extended_from_date} and {to_date}. "
            f"Consider processing in smaller date ranges for optimal performance."
        )

    by_date = {}
    for c in checkins:
        d = get_datetime(c.get('time')).date()
        by_date.setdefault(d, []).append(c)

    # Iterate through every single day in the range
    curr_date = from_date
    while curr_date <= to_date:
        daily = by_date.get(curr_date, [])
        
        hours = 0.0
        first_time = None
        last_time = None
        
        # Process checkins for current date
        if daily:
            # Get first checkin on current date (this is the IN time)
            first_checkin_on_date = daily[0]
            first_time = first_checkin_on_date.get('time')
            
            # Find last checkout on current date
            # Priority: 1) OUT type checkins, 2) Last checkin if multiple, 3) Same as first if only one
            out_checkins = [c for c in daily if (c.get('log_type') or '').upper() == 'OUT']
            if out_checkins:
                last_time = out_checkins[-1].get('time')
            elif len(daily) > 1:
                # Multiple checkins - use last one as checkout
                last_time = daily[-1].get('time')
            else:
                # Only one checkin on current date
                # For working days, check if there was a checkout on previous working days
                # This handles: logout on Dec 24, holiday Dec 25, login on Dec 26
                if is_working_day(employee, curr_date):
                    last_checkout_prev = get_last_checkout_from_previous_days(employee, curr_date, max_lookback_days=7)
                    if last_checkout_prev:
                        # There was a checkout on previous day, but for attendance calculation
                        # we still need OUT time. Use first checkin as both for now, 
                        # or leave OUT as None to be updated later
                        last_time = first_time  # Will be updated when actual checkout happens
                    else:
                        last_time = first_time
                else:
                    last_time = first_time
            
            # Calculate working hours
            hours = calculate_working_hours(first_time, last_time) if last_time else 0.0

        leave_status = get_leave_status(employee, curr_date)
        holiday_flag = is_holiday(employee, curr_date)
        
        # If there are checkins on this date, ensure attendance is created/updated
        has_checkins = bool(daily)
        
        # determine_attendance_status handles 0 hours as Absent unless holiday/leave
        status = determine_attendance_status(hours, leave_status, holiday_flag)
        
        # If there are checkins but status would be Absent (due to 0 hours or single checkin),
        # still create attendance record - it will be updated when checkout happens
        # This ensures attendance exists for dates with checkins, even if incomplete
        if has_checkins and status == "Absent" and not holiday_flag and not (leave_status and leave_status[0]):
            # If there's at least one checkin, mark as Present (will be updated when checkout happens)
            status = "Present"

        # CRITICAL: Always create/update attendance if checkins exist, regardless of existing attendance status
        # This ensures no dates are missed, even if attendance was submitted incorrectly
        
        # Check for any existing attendance (draft or submitted)
        existing_attendance = frappe.db.get_value(
            "Attendance",
            {
                "employee": employee,
                "attendance_date": curr_date
            },
            ["name", "docstatus", "in_time", "out_time"],
            as_dict=True
        )

        if existing_attendance:
            existing_name = existing_attendance.name
            existing_docstatus = existing_attendance.docstatus
            
            # If checkins exist, always update attendance to match checkins
            # This handles cases where checkins were added after attendance was submitted
            if has_checkins:
                # Check if attendance needs update (different times or missing times)
                needs_update = False
                if not existing_attendance.in_time or not existing_attendance.out_time:
                    needs_update = True
                elif existing_attendance.in_time != first_time or existing_attendance.out_time != last_time:
                    needs_update = True
                
                if needs_update:
                    if existing_docstatus == 0:
                        # Draft attendance - update it
                        doc = frappe.get_doc("Attendance", existing_name)
                        doc.in_time = first_time
                        doc.out_time = last_time
                        doc.working_hours = hours
                        
                        actual_status = status
                        if status == "Holiday":
                            doc.status = "Absent"
                        else:
                            doc.status = status
                            
                        doc.shift = shift
                        
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
                            created_list.append(existing_name)
                    else:
                        # Submitted attendance with different checkins - log for review
                        # Don't cancel submitted attendance, but log the mismatch
                        frappe.logger().info(
                            f"Submitted attendance {existing_name} for {employee} on {curr_date} "
                            f"has checkins that don't match. Existing: IN={existing_attendance.in_time}, OUT={existing_attendance.out_time}. "
                            f"Checkin times: IN={first_time}, OUT={last_time}. "
                            f"Consider creating Attendance Regularization if correction needed."
                        )
                        # Don't create duplicate - submitted attendance takes precedence
                        # User can create regularization request if needed
                else:
                    # Attendance exists and matches checkins - just track it
                    if created_list is not None and existing_docstatus == 0:
                        created_list.append(existing_name)
            else:
                # No checkins but attendance exists - track draft attendance
                if created_list is not None and existing_docstatus == 0:
                    created_list.append(existing_name)
        else:
            # No existing attendance - create new one if checkins exist
            if has_checkins:
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
    and auto-submits immediately if it meets the rules (e.g. created after checkins and already
    has enough working hours AND either shift_end+4h already passed or regularization window expired).
    """
    if not attendance_names:
        return []

    settings = get_attendance_settings()
    submitted = []
    for name in attendance_names:
        try:
            doc = frappe.get_doc("Attendance", name)
            # re-use the logic in auto_submit_due_attendances by wrapping doc into a dict
            # We'll check: if now >= shift_end+4h or regularization expired, submit.
            shift_end_dt = get_shift_end_datetime(doc.employee, doc.attendance_date, doc.shift)
            now = now_datetime()

            if now >= (shift_end_dt + timedelta(hours=4)):
                if (doc.working_hours or 0) >= settings.min_working_hours:
                    doc.flags.ignore_permissions = True
                    doc.submit()
                    submitted.append(name)
                    continue

            if settings.enable_regularization:
                reg_to = float(settings.regularization_to_hours or 0)
                if now >= (shift_end_dt + timedelta(hours=reg_to)):
                    if (doc.working_hours or 0) >= settings.min_working_hours:
                        doc.flags.ignore_permissions = True
                        doc.submit()
                        submitted.append(name)
                        continue
        except Exception as e:
            frappe.log_error(f"Error in auto_submit_new_attendances for {name}: {e}", "Attendance Auto Submit")

    if submitted:
        frappe.db.commit()
    return submitted