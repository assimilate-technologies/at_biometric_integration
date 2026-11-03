
import frappe


def execute():
    doctype = "Attendance Setting"

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
        if not frappe.db.exists(
            "Custom Field",
            {"dt": doctype, "fieldname": field["fieldname"]}
        ):
            frappe.get_doc({
                "doctype": "Custom Field",
                "dt": doctype,
                **field,
            }).insert()

    frappe.clear_cache(doctype=doctype)
