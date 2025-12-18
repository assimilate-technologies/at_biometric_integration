# at_biometric_integration/utils/auto_submit.py
import frappe
from .helpers import can_auto_submit, log_error

def auto_submit_due_attendances():
    submitted = []

    for d in frappe.get_all("Attendance", filters={"docstatus": 0}, pluck="name"):
        try:
            doc = frappe.get_doc("Attendance", d)
            if can_auto_submit(doc):
                doc.submit()
                submitted.append(d)
        except Exception as e:
            log_error(e, "Auto Submit")

    if submitted:
        frappe.db.commit()
    return submitted
