import frappe
from frappe.utils import getdate

from at_biometric_integration.utils.attendance_links import pick_checkin


def execute():
    create_employee_checkin_field()
    backfill_employee_checkin()
    frappe.db.commit()


def create_employee_checkin_field():
    """Add Employee Checkin link field on Attendance."""
    if frappe.db.exists("Custom Field", {"dt": "Attendance", "fieldname": "employee_checkin"}):
        return

    frappe.get_doc(
        {
            "doctype": "Custom Field",
            "dt": "Attendance",
            "fieldname": "employee_checkin",
            "label": "Employee Checkin",
            "fieldtype": "Link",
            "options": "Employee Checkin",
            "insert_after": "out_time",
            "description": "First Employee Checkin of the employee on the attendance date",
        }
    ).insert(ignore_permissions=True)

    frappe.clear_cache(doctype="Attendance")


def backfill_employee_checkin():
    """Link Employee Checkin for existing Attendance records (employee + date)."""
    attendances = frappe.get_all(
        "Attendance",
        filters=[["employee_checkin", "is", "not set"]],
        fields=["name", "employee", "attendance_date", "in_time"],
        order_by="attendance_date asc",
        limit_page_length=0,
    )
    if not attendances:
        return

    employees = sorted({a.employee for a in attendances if a.employee})
    if not employees:
        return

    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"employee": ["in", employees]},
        fields=["name", "employee", "time", "attendance"],
        order_by="time asc",
        limit_page_length=0,
    )

    by_day = {}
    for c in checkins:
        by_day.setdefault((c.employee, getdate(c.time)), []).append(c)

    updated = 0
    for att in attendances:
        candidates = by_day.get((att.employee, getdate(att.attendance_date)))
        checkin = pick_checkin(candidates, attendance_name=att.name, in_time=att.in_time)
        if not checkin:
            continue
        frappe.db.set_value(
            "Attendance", att.name, "employee_checkin", checkin, update_modified=False
        )
        updated += 1

    frappe.logger().info(f"employee_checkin backfill: linked {updated} Attendance records")
