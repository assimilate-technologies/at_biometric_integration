import frappe
from frappe.utils import get_datetime, time_diff_in_hours  # keep your imports above

def auto_submit_attendance():
    """
    Auto submit Attendance records that are in Draft (docstatus = 0)
    once working_hours >= 8
    """
    frappe.logger().info("🔁 auto_submit_attendance triggered")

    attendance_docs = frappe.get_all(
        "Attendance",
        filters={"docstatus": 0},
        fields=["name", "working_hours"]
    )

    frappe.logger().info(f"Found {len(attendance_docs)} draft attendance docs")

    for att in attendance_docs:
        try:
            wh = att.get("working_hours") or 0
            # make safe conversion
            wh_val = float(wh)
        except Exception:
            wh_val = 0.0

        frappe.logger().info(f"Checking {att['name']} working_hours={wh_val}")

        if wh_val >= 8.0:
            try:
                doc = frappe.get_doc("Attendance", att["name"])
                # double check docstatus to avoid double submit
                if doc.docstatus == 0:
                    doc.submit()
                    frappe.db.commit()
                    frappe.logger().info(f"✅ Auto-submitted Attendance: {att['name']}")
            except Exception as e:
                frappe.log_error(message=f"Auto-submit failed for {att['name']}: {str(e)}",
                                 title="Auto Submit Attendance Error")
