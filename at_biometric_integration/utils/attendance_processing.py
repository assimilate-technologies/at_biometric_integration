import frappe
from datetime import timedelta
from frappe.utils import get_datetime, now_datetime

# Your provided helpers
from .helpers import calculate_working_hours, get_leave_status, is_holiday


# =========================================================
# ATTENDANCE SETTINGS
# =========================================================
def get_attendance_settings():
    try:
        s = frappe.get_single("Attendance Settings")
        return frappe._dict({
            "enable_regularization": s.enable_regularization,
            "regularization_from_hours": s.regularization_from_hours or 0,
            "regularization_to_hours": s.regularization_to_hours or 24,
            "min_working_hours": s.min_working_hours or 4,
            "checkin_grace_start_minutes": s.checkin_grace_start_minutes or 0,
            "checkout_grace_end_minutes": s.checkout_grace_end_minutes or 0,
            "attendance_grace_start_mins": s.attendance_grace_start_mins or 0,
            "attendance_grace_end_mins": s.attendance_grace_end_mins or 0,
        })
    except Exception:
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


# =========================================================
# SHIFT END DATETIME
# =========================================================
def get_shift_end_datetime(employee, attendance_date, shift_name):
    """Returns final shift end datetime, always."""
    # Try shift type
    try:
        if shift_name:
            shift = frappe.get_doc("Shift Type", shift_name)
            end_t = getattr(shift, "end_time", None)
            if end_t:
                return get_datetime(f"{attendance_date} {end_t}")
    except Exception:
        pass

    # Fallback: out_time on attendance
    out_time = frappe.db.get_value("Attendance",
                                   {"employee": employee, "attendance_date": attendance_date},
                                   "out_time")
    if out_time:
        return get_datetime(out_time)

    # Final fallback 18:30
    return get_datetime(f"{attendance_date} 18:30:00")


# =========================================================
# AUTO SUBMIT ONE ATTENDANCE
# =========================================================
def auto_submit_attendance_doc(att):
    try:
        doc = frappe.get_doc("Attendance", att.name)

        if doc.docstatus == 1:
            return False

        # ALWAYS compute working hours fresh
        doc.working_hours = 0
        if doc.in_time and doc.out_time:
            doc.working_hours = calculate_working_hours(doc.in_time, doc.out_time)

        settings = get_attendance_settings()

        if doc.working_hours < float(settings.min_working_hours):
            return False

        doc.status = "Present" if doc.working_hours >= settings.min_working_hours else "Half Day"
        doc.submit(ignore_permissions=True)
        return True

    except Exception as e:
        frappe.log_error(f"Auto submit error {att.name}: {e}", "Attendance Auto Submit")
        return False


# =========================================================
# AUTO SUBMIT DUE ATTENDANCES
# =========================================================
@frappe.whitelist()
def auto_submit_due_attendances():
    settings = get_attendance_settings()
    now = now_datetime()

    attendances = frappe.get_all("Attendance",
                                 filters={"docstatus": 0},
                                 fields=["name", "employee", "attendance_date", "shift"])

    submitted = []

    for att in attendances:
        try:
            doc = frappe.get_doc("Attendance", att.name)

            # Calculate working hours fresh
            doc.working_hours = 0
            if doc.in_time and doc.out_time:
                doc.working_hours = calculate_working_hours(doc.in_time, doc.out_time)

            shift_end = get_shift_end_datetime(doc.employee, doc.attendance_date, doc.shift)

            # Condition 1: 4 hours after shift end
            if now >= shift_end + timedelta(hours=4):
                if doc.working_hours >= settings.min_working_hours:
                    if auto_submit_attendance_doc(att):
                        submitted.append(att.name)
                continue

            # Condition 2: Regularization window
            if settings.enable_regularization:
                reg_hours = float(settings.regularization_to_hours or 0)
                if now >= shift_end + timedelta(hours=reg_hours):
                    if doc.working_hours >= settings.min_working_hours:
                        if auto_submit_attendance_doc(att):
                            submitted.append(att.name)
        except Exception as e:
            frappe.log_error(f"auto_submit_due_attendances error {att.name}: {e}")

    if submitted:
        frappe.db.commit()

    return submitted


# =========================================================
# REALTIME PROCESSING - BUILD/UPDATE ATTENDANCE
# =========================================================
def process_attendance_realtime():
    employees = frappe.get_all("Employee",
                               filters={"status": "Active"},
                               fields=["name", "default_shift"])

    updated = []

    for emp in employees:
        try:
            process_employee_attendance_realtime(emp.name, emp.default_shift or "", updated)
        except Exception as e:
            frappe.log_error(f"{emp.name} realtime error: {e}", "Realtime Attendance")

    frappe.db.commit()
    return updated


def process_employee_attendance_realtime(employee, shift, updated_list=None):
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee},
        fields=["name", "time"],
        order_by="time asc"
    )

    if not checkins:
        return

    grouped = {}

    for c in checkins:
        d = get_datetime(c.time).date()
        grouped.setdefault(d, []).append(c)

    for date, row_list in grouped.items():
        first = row_list[0]
        last = row_list[-1]

        # FIXED: Helper requires FIRST + LAST objects, not .time passed twice
        working_hours = calculate_working_hours(first, last)

        status = "Present" if working_hours >= 4 else "Half Day"

        existing = frappe.db.exists("Attendance",
                                    {"employee": employee, "attendance_date": date})

        if existing:
            # UPDATE
            frappe.db.set_value("Attendance", existing, {
                "in_time": first.time,
                "out_time": last.time,
                "working_hours": working_hours,
                "status": status,
                "shift": shift
            })
            if updated_list is not None:
                updated_list.append(existing)
        else:
            # INSERT
            doc = frappe.get_doc({
                "doctype": "Attendance",
                "employee": employee,
                "attendance_date": date,
                "shift": shift,
                "in_time": first.time,
                "out_time": last.time,
                "working_hours": working_hours,
                "status": status
            })
            doc.insert(ignore_permissions=True)
            if updated_list:
                updated_list.append(doc.name)


# =========================================================
# AUTO SUBMIT NEW ATTENDANCES
# =========================================================
def auto_submit_new_attendances(names):
    if not names:
        return []

    settings = get_attendance_settings()
    now = now_datetime()

    submitted = []

    for name in names:
        try:
            doc = frappe.get_doc("Attendance", name)

            # Always fresh calculation
            doc.working_hours = 0
            if doc.in_time and doc.out_time:
                doc.working_hours = calculate_working_hours(doc.in_time, doc.out_time)

            shift_end = get_shift_end_datetime(doc.employee, doc.attendance_date, doc.shift)

            if now >= shift_end + timedelta(hours=4):
                if doc.working_hours >= settings.min_working_hours:
                    doc.submit(ignore_permissions=True)
                    submitted.append(name)
                continue

            if settings.enable_regularization:
                reg_hours = float(settings.regularization_to_hours)
                if now >= shift_end + timedelta(hours=reg_hours):
                    if doc.working_hours >= settings.min_working_hours:
                        doc.submit(ignore_permissions=True)
                        submitted.append(name)

        except Exception as e:
            frappe.log_error(f"auto_submit_new_attendances error for {name}: {e}")

    if submitted:
        frappe.db.commit()

    return submitted
