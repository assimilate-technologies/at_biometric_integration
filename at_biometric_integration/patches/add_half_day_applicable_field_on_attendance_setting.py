import frappe


def execute():
    fields = [
        {
            "fieldname": "half_day_from",
            "label": "Half Day From",
            "fieldtype": "Time",
            "insert_after": "attendance_grace_start_mins",
        },
        {
            "fieldname": "half_day_to",
            "label": "Half Day To",
            "fieldtype": "Time",
            "insert_after": "half_day_from",
        },
    ]

    for field in fields:
        # Check both Custom Field and standard DocField
        has_custom = frappe.db.exists(
            "Custom Field",
            {
                "dt": "Attendance Settings",
                "fieldname": field["fieldname"],
            },
        )
        meta = frappe.get_meta("Attendance Settings")
        has_docfield = meta.has_field(field["fieldname"])

        if has_custom or has_docfield:
            print(f"Skipping existing field: {field['fieldname']}")
            continue

        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Attendance Settings",
            **field,
        }).insert()

        print(f"Created field: {field['fieldname']}")

    frappe.clear_cache(doctype="Attendance Settings")