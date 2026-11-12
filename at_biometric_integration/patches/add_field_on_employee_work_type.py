import frappe


def execute():
    if not frappe.db.exists(
        "Custom Field",
        {"dt": "Employee", "fieldname": "custom_work_type"}
    ):
        custom_field = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Employee",
            "label": "Work Type",
            "fieldname": "custom_work_type",
            "fieldtype": "Link",
            "options": "Work Type",
            "insert_after": "status",
            "in_list_view": 1
        })

        custom_field.insert(ignore_permissions=True)

    frappe.clear_cache(doctype="Employee")