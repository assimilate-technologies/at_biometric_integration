import frappe


def execute():
    doctype = "Attendance Regularization"

    if not frappe.db.exists("DocType", doctype):
        return

    # Add from_date field — mandatory by default
    if not frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": "from_date"}):
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": doctype,
                "fieldname": "from_date",
                "label": "From Date",
                "fieldtype": "Date",
                "insert_after": "employee_name",
                "reqd": 1,
                "hidden": 0,
            }
        ).insert(ignore_permissions=True)
    else:
        # Update existing field settings to be mandatory by default
        frappe.db.set_value(
            "Custom Field",
            {"dt": doctype, "fieldname": "from_date"},
            {
                "reqd": 1,
                "hidden": 0,
                "read_only": 0,
                "depends_on": "",
                "mandatory_depends_on": "",
                "insert_after": "employee_name",
                "description": "",
            },
        )

    # Ensure field_order property setter includes from_date if present
    import json
    ps = frappe.db.get_value("Property Setter", {"doc_type": doctype, "property": "field_order"}, "value")
    if ps:
        order = json.loads(ps)
        if "from_date" not in order:
            idx = order.index("date") if "date" in order else 3
            order.insert(idx, "from_date")
            frappe.db.set_value("Property Setter", {"doc_type": doctype, "property": "field_order"}, "value", json.dumps(order))

    frappe.clear_cache(doctype=doctype)


