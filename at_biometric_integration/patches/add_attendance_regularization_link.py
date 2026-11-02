import frappe
from frappe.utils import getdate


def execute():
    create_attendance_regularization_field()
    backfill_attendance_regularization()
    frappe.db.commit()


def create_attendance_regularization_field():
    """Add Attendance Regularization link field on Attendance."""
    if frappe.db.exists("Custom Field", {"dt": "Attendance", "fieldname": "attendance_regularization"}):
        return

    frappe.get_doc(
        {
            "doctype": "Custom Field",
            "dt": "Attendance",
            "fieldname": "attendance_regularization",
            "label": "Attendance Regularization",
            "fieldtype": "Link",
            "options": "Attendance Regularization",
            "insert_after": "attendance_request",
            "description": "Attendance Regularization of the employee on the attendance date",
        }
    ).insert(ignore_permissions=True)

    frappe.clear_cache(doctype="Attendance")


def backfill_attendance_regularization():
    """Link submitted Attendance Regularization for existing Attendance records."""
    attendances = frappe.get_all(
        "Attendance",
        filters=[["attendance_regularization", "is", "not set"]],
        fields=["name", "employee", "attendance_date"],
        limit_page_length=0,
    )
    if not attendances:
        return

    regularizations = frappe.get_all(
        "Attendance Regularization",
        filters={"docstatus": 1},
        fields=["name", "employee", "date", "workflow_state"],
        order_by="creation desc",
        limit_page_length=0,
    )

    # latest submitted regularization wins, unless an older one is approved
    by_day = {}
    for reg in regularizations:
        key = (reg.employee, getdate(reg.date))
        state = reg.get("workflow_state") or ""
        approved = "Approved" in state and "Rejected" not in state
        if key not in by_day:
            by_day[key] = (reg.name, approved)
        elif approved and not by_day[key][1]:
            by_day[key] = (reg.name, True)

    updated = 0
    for att in attendances:
        match = by_day.get((att.employee, getdate(att.attendance_date)))
        if not match:
            continue
        frappe.db.set_value(
            "Attendance",
            att.name,
            "attendance_regularization",
            match[0],
            update_modified=False,
        )
        updated += 1

    frappe.logger().info(f"attendance_regularization backfill: linked {updated} Attendance records")
