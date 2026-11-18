
import frappe


def execute():
    doctype = "Attendance Settings"

    if not frappe.db.exists("DocType", doctype):
        return

    fields = [
        {
            "fieldname": "maximum_allowed_grace_instances_in_month",
            "label": "Maximum Allowed Grace Instances (In Month)",
            "fieldtype": "Int",
            "insert_after": "max_requests_per_month",
        },
        {
            "fieldname": "grace_time_limit_in_minutes",
            "label": "Grace Time Limit (In Minutes)",
            "fieldtype": "Int",
            "insert_after": "maximum_allowed_grace_instances_in_month",
        },
    ]

    meta = frappe.get_meta(doctype)

    for field in fields:
        if not meta.get_field(field["fieldname"]):
            docfield = frappe.get_doc({
                "doctype": "Custom Field",
                "dt": doctype,
                **field,
            })
            docfield.insert(ignore_permissions=True)

    frappe.clear_cache(doctype=doctype)
