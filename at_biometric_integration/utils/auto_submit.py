# at_biometric_integration/utils/auto_submit.py
import frappe
from .helpers import can_auto_submit, log_error

def auto_submit_due_attendances():
    submitted = []
    try:
        drafts = frappe.get_all("Attendance", filters={"docstatus": 0}, fields=["name"])
        for d in drafts:
            try:
                doc = frappe.get_doc("Attendance", d.name)
                if can_auto_submit(doc):
                    doc.submit()
                    submitted.append(d.name)
            except Exception as e:
                log_error(f"Failed to submit {d.name}: {e}", "auto_submit")
        if submitted:
            frappe.db.commit()
        return submitted
    except Exception as e:
        log_error(e, "auto_submit_due_attendances")
        return []
