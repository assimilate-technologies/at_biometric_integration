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
from .helpers import get_leave_status, is_holiday, is_weekend, calculate_working_hours, determine_attendance_status, get_employee_shift, time_to_hours
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


def sync_checkin_child_table(attendance_name, employee, attendance_date):
    """Sync the 'employee_checkin' child table (doctype 'checkin') on an
    Attendance record so it contains ALL Employee Checkin rows for that
    employee on that date.

    Safe to call on both draft and submitted Attendance docs — uses direct
    DB inserts/deletes on the child table without touching the parent doc.
    """
    attendance_date = getdate(attendance_date)

    # All Employee Checkins for this employee on this date
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [f"{attendance_date} 00:00:00", f"{attendance_date} 23:59:59"]],
        },
        fields=["name", "time"],
        order_by="time asc",
        limit_page_length=500,
    )
    new_names = {c.name for c in checkins}

    # Existing child rows
    existing_rows = frappe.get_all(
        "checkin",
        filters={
            "parent": attendance_name,
            "parenttype": "Attendance",
            "parentfield": "employee_checkin",
        },
        fields=["name", "checkin"],
        limit_page_length=0,
    )
    existing_names = {r.checkin for r in existing_rows}

    # Remove stale rows (checkin record deleted / no longer for this day)
    for row in existing_rows:
        if row.checkin not in new_names:
            frappe.db.delete("checkin", {"name": row.name})

    # Add missing rows
    idx = len(existing_rows)
    for c in checkins:
        if c.name not in existing_names:
            idx += 1
            child = frappe.new_doc("checkin")
            child.parent = attendance_name
            child.parenttype = "Attendance"
            child.parentfield = "employee_checkin"
            child.idx = idx
            child.checkin = c.name
            child.db_insert()

    # Rule: Take first record time as in_time, last record time as out_time.
    # When only one record, in_time and out_time show the same.
    valid_times = [c.time for c in checkins if c.get("time")]
    if valid_times:
        in_t = valid_times[0]
        out_t = valid_times[-1]
        hrs = "00:00:00"
        if in_t != out_t:
            from at_biometric_integration.utils.helpers import calculate_working_hours
            hrs = calculate_working_hours(in_t, out_t)

        frappe.db.set_value("Attendance", attendance_name, {
            "in_time": in_t,
            "out_time": out_t,
            "working_hours": hrs,
        }, update_modified=False)


def is_employee_wfh(employee):
    """Check if employee has custom_work_type = 'Work From Home'."""
    if not employee:
        return False
    work_type = frappe.db.get_value("Employee", employee, "custom_work_type", cache=True)
    return (work_type or "").strip().lower() == "work from home"


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

        # Rule: First record time as in_time, last record time as out_time.
        # When only one record, in_time and out_time show the same.
        all_times = [c.get("time") for c in checkins if c.get("time")]
        first_time = all_times[0] if all_times else None
        last_time = all_times[-1] if all_times else None

        hours = "00:00:00"
        if first_time and last_time and first_time != last_time:
            hours = calculate_working_hours(first_time, last_time)

        leave_status = get_leave_status(employee, checkin_date)
        holiday_flag = is_holiday(employee, checkin_date)

        # Saturday and Sunday are holidays: do not create attendance if punches are missing
        if is_weekend(checkin_date) and (not first_time or not last_time):
            existing_draft_check = frappe.db.get_value(
                "Attendance",
                {"employee": employee, "attendance_date": checkin_date, "docstatus": 0},
                "name"
            )
            existing_sub_check = frappe.db.get_value(
                "Attendance",
                {"employee": employee, "attendance_date": checkin_date, "docstatus": 1},
                "name"
            )
            if not existing_draft_check and not existing_sub_check:
                return

        if not first_time or not last_time:
            if leave_status and leave_status[0]:
                status = leave_status[0]
            elif holiday_flag:
                status = "Holiday"
            else:
                status = "Absent"
        else:
            status = determine_attendance_status(hours, leave_status, holiday_flag, in_time=first_time, out_time=last_time)

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

            frappe.db.set_value("Attendance", existing_draft, update_data, update_modified=True)

            # Sync checkin child table with ALL checkins for this employee/date
            sync_checkin_child_table(existing_draft, employee, checkin_date)

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

            # Sync checkin child table
            sync_checkin_child_table(existing_submitted, employee, checkin_date)
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

            # Sync checkin child table with ALL checkins for this employee/date
            sync_checkin_child_table(new_att.name, employee, checkin_date)

            for c in checkins:
                frappe.db.set_value("Employee Checkin", c.name, "attendance", new_att.name, update_modified=False)

    except Exception:
        frappe.log_error(title=f"Live Attendance Update Error: {doc.get('employee')}", message=frappe.get_traceback())


def get_status_by_working_hours(work_seconds, in_time=None, out_time=None):
    """
    Status rules based on in_time, out_time, and working_hours:
      If in_time or out_time not present   → 'Absent'
      working_hours < 5 hr                 ( < 18,000 sec)  → 'Absent'
      working_hours in between 5 to 8.44 hr (18,000 to 31,499) → 'Half Day'
      working_hours >= 8:45 hr             (>= 31,500 sec)  → 'Present'
    """
    if in_time is not None or out_time is not None:
        if not in_time or not out_time:
            return "Absent"

    FIVE_HOURS = 5 * 3600                     # 18,000 seconds (5:00:00)
    EIGHT_FORTY_FIVE = 8 * 3600 + 45 * 60     # 31,500 seconds (8:45:00)

    if work_seconds < FIVE_HOURS:
        return "Absent"
    elif work_seconds < EIGHT_FORTY_FIVE:
        return "Half Day"
    else:
        return "Present"


def check_min_working_hours_on_submit(doc, method=None):
    """
    before_submit hook on Attendance.
    Rules:
      If in_time and out_time not present → status = 'Absent'
      working_hours < 5 hr               → status = 'Absent'
      working_hours in between 5 to 8.44 → status = 'Half Day'
      working_hours >= 8:45 hr           → status = 'Present'
    Approved Leave records are preserved as-is.
    """
    # Preserve approved leave applications
    if doc.status == "On Leave" and (doc.get("leave_application") or doc.get("leave_type")):
        return

    # If in_time or out_time not present -> status = 'Absent'
    if not doc.get("in_time") or not doc.get("out_time"):
        doc.status = "Absent"
        if not doc.get("working_hours"):
            doc.working_hours = "00:00:00"
        return

    # Recalculate working_hours if missing
    if not doc.get("working_hours") or doc.get("working_hours") == "00:00:00":
        doc.working_hours = calculate_working_hours(doc.in_time, doc.out_time)

    work_seconds = get_working_hours_seconds(doc.get("working_hours"))
    doc.status = get_status_by_working_hours(work_seconds, doc.get("in_time"), doc.get("out_time"))


def auto_submit_attendance_doc(att_doc, settings=None):
    """
    Submit a single attendance document if it meets submission criteria.
    Accepts Attendance doc object, dict, or document name string.
    Returns True if submitted.
    """
    try:
        if isinstance(att_doc, str):
            doc_name = att_doc
        elif hasattr(att_doc, "name"):
            doc_name = att_doc.name
        elif isinstance(att_doc, dict):
            doc_name = att_doc.get("name")
        else:
            doc_name = None

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

        # 3. Ensure working_hours is calculated if in_time and out_time exist
        if doc.in_time and doc.out_time:
            doc.working_hours = calculate_working_hours(doc.in_time, doc.out_time)
        else:
            doc.working_hours = "00:00:00"

        # 4. Status rule:
        #    If On Leave: preserved
        #    If in_time or out_time not present   → 'Absent'
        #    working_hours < 5 hr                 → 'Absent'
        #    working_hours in between 5 to 8.44 hr → 'Half Day'
        #    working_hours >= 8:45 hr             → 'Present'
        is_on_leave = (doc.status == "On Leave" and (doc.get("leave_application") or doc.get("leave_type")))

        if is_on_leave:
            pass
        elif not doc.in_time or not doc.out_time:
            doc.status = "Absent"
        else:
            work_seconds = get_working_hours_seconds(doc.working_hours)
            doc.status = get_status_by_working_hours(work_seconds, doc.in_time, doc.out_time)

        # 5. Final safety check — Frappe HRMS valid statuses
        valid_statuses = ["Present", "Absent", "On Leave", "Half Day", "Work From Home"]
        if doc.status not in valid_statuses:
            doc.status = "Absent"

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
            title=f"Attendance Auto Submit Error: {doc_name if 'doc_name' in locals() else getattr(att_doc, 'name', '')}",
            message=frappe.get_traceback()
        )
        return False


@frappe.whitelist()
def update_attendance_statuses_backend(date=None):
    """
    Direct Backend Execution Command:
    Updates attendance records to match the rules:
      If in_time or out_time not present   → status = 'Absent', working_hours = '00:00:00'
      working_hours < 5 hr                 → status = 'Absent'
      working_hours in between 5 to 8.44 hr → status = 'Half Day'
      working_hours >= 8:45 hr             → status = 'Present'
    """
    filters = {"status": ["!=", "Holiday"]}
    if date:
        filters["attendance_date"] = date
    else:
        filters["attendance_date"] = getdate()

    records = frappe.get_all(
        "Attendance",
        filters=filters,
        fields=["name", "employee", "attendance_date", "in_time", "out_time", "working_hours", "status", "leave_application", "leave_type", "docstatus"]
    )

    updated_count = 0
    for r in records:
        if r.status == "On Leave" and (r.leave_application or r.leave_type):
            continue

        if not r.in_time or not r.out_time:
            work_hrs = "00:00:00"
            new_status = "Absent"
        else:
            work_hrs = calculate_working_hours(r.in_time, r.out_time)
            work_seconds = get_working_hours_seconds(work_hrs)
            new_status = get_status_by_working_hours(work_seconds, r.in_time, r.out_time)

        if r.status != new_status or r.working_hours != work_hrs:
            frappe.db.set_value("Attendance", r.name, {
                "working_hours": work_hrs or "00:00:00",
                "status": new_status
            }, update_modified=False)
            updated_count += 1

    frappe.db.commit()
    return {"updated": updated_count, "total": len(records)}


def auto_submit_due_attendances(force=False, date=None):
    """
    Find attendance records that are due for auto-submission and submit them.

    Trigger:
      Current time >= (shift_end_datetime + auto_submit_after_shift_hours)

    Args:
      force (bool): If True, bypass the cutoff time check and auto_submit_after_shift_hours == 0 check (for manual testing).
      date (str/date): Specific attendance date to process. Defaults to all open draft records.

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

    # Feature is disabled when field is 0 or not configured, unless force=True for manual testing
    if not auto_submit_hours and not force:
        print("[Auto-Submit] auto_submit_after_shift_hours is 0 or not configured in Attendance Settings. Pass force=True to test manually.")
        return []

    filters = {"docstatus": 0, "status": ["!=", "Holiday"]}
    if date:
        filters["attendance_date"] = getdate(date)

    # Query all open (draft) attendance records excluding Holiday status
    open_att = frappe.get_all("Attendance", filters=filters, fields=[
        "name", "employee", "attendance_date", "in_time", "out_time", "working_hours", "status", "shift"
    ], limit_page_length=50000)

    print(f"[Auto-Submit] Found {len(open_att)} draft attendance records (force={force}, cutoff_hours={auto_submit_hours}).")

    submitted_any = []
    for a in open_att:
        try:
            shift_end_dt = get_shift_end_datetime(a.employee, a.attendance_date, a.get("shift"))
            cutoff_dt = shift_end_dt + timedelta(hours=auto_submit_hours)

            # Once current time passes the cutoff (or if force=True), submit record
            if force or now >= cutoff_dt:
                success = auto_submit_attendance_doc(a.name, settings)
                if success:
                    submitted_any.append(a.name)
                    print(f"  [Auto-Submit] Submitted: {a.name} (Employee: {a.employee})")
                else:
                    print(f"  [Auto-Submit] Not submitted: {a.name} (Employee: {a.employee})")
            else:
                print(f"  [Auto-Submit] Pending cutoff: {a.name} ({a.employee}) - cutoff: {cutoff_dt}, now: {now}")

        except Exception as e:
            frappe.log_error(
                title=f"Error evaluating auto-submit for attendance {a.get('name')}",
                message=frappe.get_traceback()
            )

    if submitted_any:
        frappe.db.commit()

    print(f"[Auto-Submit] Completed. Total submitted: {len(submitted_any)}")
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

        # Saturday and Sunday are holidays - do not create attendance records when there are no checkins
        if is_weekend(curr_date) and not daily:
            curr_date = add_days(curr_date, 1)
            continue
        
        hours = "00:00:00"
        first_time = None
        last_time = None
        
        if daily:
            # Rule: First record time as in_time, last record time as out_time.
            # When only one record, in_time and out_time show the same.
            daily_times = [c.get("time") for c in daily if c.get("time")]
            first_time = daily_times[0] if daily_times else None
            last_time = daily_times[-1] if daily_times else None

            if first_time and last_time and first_time != last_time:
                hours = calculate_working_hours(first_time, last_time)
            else:
                hours = "00:00:00"

        leave_status = get_leave_status(employee, curr_date)
        holiday_flag = is_holiday(employee, curr_date)

        # Saturday and Sunday are holidays: do not create attendance record if employee did not complete in & out punches
        if is_weekend(curr_date) and (not first_time or not last_time):
            existing_draft_temp = frappe.db.exists("Attendance", {
                "employee": employee,
                "attendance_date": curr_date,
                "docstatus": 0
            })
            existing_sub_temp = frappe.db.exists("Attendance", {
                "employee": employee,
                "attendance_date": curr_date,
                "docstatus": 1
            })
            if not existing_draft_temp and not existing_sub_temp:
                curr_date = add_days(curr_date, 1)
                continue

        # If in_time or out_time not present -> status = Absent (unless On Leave or Holiday)
        if not first_time or not last_time:
            if leave_status and leave_status[0]:
                status = leave_status[0]
            elif holiday_flag:
                status = "Holiday"
            else:
                status = "Absent"
        else:
            status = determine_attendance_status(hours, leave_status, holiday_flag, in_time=first_time, out_time=last_time)

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

            # Sync checkin child table
            sync_checkin_child_table(existing_draft, employee, curr_date)
            
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

            if update_fields:
                frappe.db.set_value("Attendance", existing_submitted, update_fields, update_modified=False)

            # Sync checkin child table
            sync_checkin_child_table(existing_submitted, employee, curr_date)
            
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

                # Sync checkin child table with ALL checkins
                sync_checkin_child_table(doc.name, employee, curr_date)

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

    Saturday and Sunday are holidays: do NOT create Saturday and Sunday attendance records.
    On Leave employees get their corresponding status.
    Holidays are skipped as holidays do not use Attendance records in Frappe HRMS.
    """
    today = getdate()

    # Saturday and Sunday are holidays: do NOT create Saturday and Sunday attendance records
    if is_weekend(today):
        return []

    # Fetch only Active employees
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "company", "default_shift", "custom_work_type"],
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

            # Skip weekends and holidays (Frappe HRMS uses Holiday List, 'Holiday' is not a valid Attendance status)
            if is_weekend(today) or is_holiday(emp.name, today):
                continue

            leave_status = get_leave_status(emp.name, today)

            if leave_status and leave_status[0]:
                status = leave_status[0]       # "On Leave" or "Half Day"
                leave_type = leave_status[1]
                leave_application = leave_status[2]
            else:
                # All employees (including Work From Home) start as Absent at midnight
                # When a WFH employee creates a check-in record, status updates to Work From Home
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


def create_attendance_for_new_employee(doc, method=None):
    """
    Hook on Employee after_insert:
    When a new Active employee is added, create today's draft Attendance record
    immediately (with status 'Absent') so they don't have to wait until midnight.
    """
    try:
        if getattr(doc, "status", None) != "Active":
            return

        today = getdate()
        if is_weekend(today) or is_holiday(doc.name, today):
            return

        if frappe.db.exists("Attendance", {"employee": doc.name, "attendance_date": today}):
            return

        shift_doc = get_employee_shift(doc.name, today)
        shift_name = shift_doc.name if shift_doc else (doc.default_shift or None)

        leave_status = get_leave_status(doc.name, today)
        status = leave_status[0] if (leave_status and leave_status[0]) else "Absent"

        att = frappe.get_doc({
            "doctype": "Attendance",
            "employee": doc.name,
            "employee_name": doc.employee_name,
            "attendance_date": today,
            "company": doc.company,
            "status": status,
            "shift": shift_name,
            "working_hours": "00:00:00",
        })
        att.flags.ignore_permissions = True
        att.insert()
    except Exception:
        frappe.log_error(
            title=f"create_attendance_for_new_employee Error: {getattr(doc, 'name', '')}",
            message=frappe.get_traceback()
        )


# ------------------------
# Work From Home Checkin Permission Helpers
# ------------------------
@frappe.whitelist()
def check_user_wfh_status(user=None):
    """
    Check if the user is Administrator or linked to an Employee with custom_work_type = 'Work From Home'.
    Used to determine if 'Add Employee Checkin' button should be shown.
    """
    user = user or frappe.session.user
    if user == "Administrator":
        return {
            "can_add": True,
            "is_admin": True,
            "is_wfh": False,
            "employee": None,
            "employee_name": None,
            "custom_work_type": None
        }

    emp = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        ["name", "employee_name", "custom_work_type", "status"],
        as_dict=True
    )

    if not emp:
        return {
            "can_add": False,
            "is_admin": False,
            "is_wfh": False,
            "employee": None,
            "employee_name": None,
            "custom_work_type": None
        }

    work_type = (emp.get("custom_work_type") or "").strip().lower()
    is_wfh = (work_type == "work from home")

    return {
        "can_add": is_wfh,
        "is_admin": False,
        "is_wfh": is_wfh,
        "employee": emp.name,
        "employee_name": emp.employee_name,
        "custom_work_type": emp.custom_work_type
    }


def validate_employee_checkin_wfh(doc, method=None):
    """
    Backend validation hook on Employee Checkin validate:
    Ensures manual check-ins in Frappe Desk can only be added by:
      - Administrator
      - Employees with custom_work_type = 'Work From Home'

    Biometric hardware sync / automated imports (device_ip, device_id, ignore_permissions) are exempted.
    """
    # 1. Exempt biometric sync / automated tasks / ignore_permissions
    if (
        doc.get("device_ip")
        or doc.flags.get("from_biometric_device")
        or doc.flags.get("ignore_permissions")
        or getattr(frappe.flags, "in_migrate", False)
        or getattr(frappe.flags, "in_install", False)
    ):
        return

    # 2. Administrator is always allowed
    if frappe.session.user in ("Administrator", "Guest"):
        return

    # 3. Check current logged-in user
    status = check_user_wfh_status(frappe.session.user)
    if not status.get("can_add"):
        frappe.throw(
            frappe._("Manual check-in creation is only allowed for Work From Home employees and Administrator. Office employees must punch via biometric devices."),
            title=frappe._("Checkin Not Allowed")
        )

    # 4. A WFH employee can only check-in for themselves
    if status.get("employee") and doc.get("employee") and doc.employee != status.get("employee"):
        frappe.throw(
            frappe._("You can only create check-in records for yourself ({0}).").format(status.get("employee")),
            title=frappe._("Invalid Employee")
        )


@frappe.whitelist()
def sync_all_attendance_checkin_times(date=None):
    """
    Sync in_time, out_time, working_hours, and status for all previous Attendance records:
      - First record time as in_time
      - Last record time as out_time
      - When only one record, in_time and out_time show the exact same
      - working_hours = calculate_working_hours(in_time, out_time)
      - Work From Home employees with check-ins -> 'Work From Home'
      - Work From Home employees with NO check-ins -> 'Absent'
      - Office employees -> 'Absent' / 'Half Day' / 'Present' per working_hours rules
      - On Leave preserved
    """
    filters = {}
    if date:
        filters["attendance_date"] = getdate(date)

    attendances = frappe.get_all(
        "Attendance",
        filters=filters,
        fields=["name", "employee", "attendance_date", "docstatus", "status"],
        order_by="attendance_date desc",
        limit_page_length=0,
    )

    updated = 0
    for att in attendances:
        is_on_leave = (att.status == "On Leave")
        is_wfh = is_employee_wfh(att.employee)

        checkins = frappe.get_all(
            "Employee Checkin",
            filters={
                "employee": att.employee,
                "time": ["between", [f"{att.attendance_date} 00:00:00", f"{att.attendance_date} 23:59:59"]],
            },
            fields=["name", "time"],
            order_by="time asc",
            limit_page_length=500,
        )

        if not checkins:
            if not is_on_leave and att.status != "Holiday":
                frappe.db.set_value("Attendance", att.name, {
                    "in_time": None,
                    "out_time": None,
                    "working_hours": "00:00:00",
                    "status": "Absent",
                }, update_modified=False)
                updated += 1
            continue

        valid_times = [c.time for c in checkins if c.get("time")]
        if not valid_times:
            continue

        in_t = valid_times[0]
        out_t = valid_times[-1]
        hrs = "00:00:00"
        if in_t != out_t:
            from at_biometric_integration.utils.helpers import calculate_working_hours
            hrs = calculate_working_hours(in_t, out_t)

        if is_on_leave:
            new_status = att.status
        elif in_t == out_t:
            new_status = "Absent"
        else:
            work_seconds = get_working_hours_seconds(hrs)
            new_status = get_status_by_working_hours(work_seconds, in_t, out_t)

        update_dict = {
            "in_time": in_t,
            "out_time": out_t,
            "working_hours": hrs,
        }
        if att.status != "Holiday":
            update_dict["status"] = new_status

        frappe.db.set_value("Attendance", att.name, update_dict, update_modified=False)

        # Sync child table checkin rows and reverse link
        sync_checkin_child_table(att.name, att.employee, att.attendance_date)
        for c in checkins:
            frappe.db.set_value("Employee Checkin", c.name, "attendance", att.name, update_modified=False)

        updated += 1

    frappe.db.commit()
    print(f"Successfully updated in_time, out_time, working_hours and status for {updated} Attendance records.")
    return {"updated": updated, "total": len(attendances)}
