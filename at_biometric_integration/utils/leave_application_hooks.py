import frappe


def unlink_attendance_on_leave_cancel(doc, method=None):
    """
    When a Leave Application is cancelled, do NOT cascade-cancel linked Attendance records.
    Instead:
      1. Find all Attendance records linked to this leave application.
      2. If HRMS already set docstatus=2 on them (via cancel_attendance), restore them
         to their previous docstatus (1 = submitted, 0 = draft).
      3. Clear leave_application and leave_type fields.
      4. Reset status to 'Absent' if it was 'On Leave' or 'Half Day'.
    """
    if doc.docstatus != 2:
        return

    # Find attendance records linked to this leave application by leave_application field
    attendance_records = frappe.get_all(
        "Attendance",
        filters={
            "employee": doc.employee,
            "attendance_date": ["between", [doc.from_date, doc.to_date]],
            "leave_application": doc.name,
        },
        fields=["name", "docstatus", "status"],
    )

    # Also find records that HRMS may have already cancelled (docstatus=2) but were submitted before
    # HRMS cancel_attendance does: db.set_value("Attendance", name, "docstatus", 2) for On Leave/Half Day
    # So we look for docstatus=2 records linked to this leave app that were previously submitted
    cancelled_by_hrms = frappe.get_all(
        "Attendance",
        filters={
            "employee": doc.employee,
            "attendance_date": ["between", [doc.from_date, doc.to_date]],
            "leave_application": doc.name,
            "docstatus": 2,
        },
        fields=["name", "docstatus", "status"],
    )

    # Merge both lists (deduplicate by name)
    all_records = {r["name"]: r for r in attendance_records}
    for r in cancelled_by_hrms:
        all_records[r["name"]] = r

    for att in all_records.values():
        update_fields = {
            "leave_application": None,
            "leave_type": None,
        }

        # Determine what docstatus to restore to
        # If HRMS cancelled it (docstatus=2), restore to submitted (1)
        # Attendance records that were draft (0) stay draft
        restore_docstatus = None
        if att["docstatus"] == 2:
            restore_docstatus = 1  # restore to submitted

        # Reset status to Absent if it was leave-related
        if att["status"] in ("On Leave", "Half Day"):
            update_fields["status"] = "Absent"

        frappe.db.set_value(
            "Attendance",
            att["name"],
            update_fields,
            update_modified=True,
        )

        # Restore docstatus separately to avoid conflicts
        if restore_docstatus is not None:
            frappe.db.set_value(
                "Attendance",
                att["name"],
                "docstatus",
                restore_docstatus,
                update_modified=False,
            )

    if all_records:
        frappe.logger().info(
            f"Unlinked Leave Application {doc.name} from {len(all_records)} Attendance record(s); "
            f"status reset to Absent where applicable."
        )
