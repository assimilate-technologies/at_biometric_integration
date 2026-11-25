import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
    """
    Add 'Absent-Half Day' option to status field of Attendance DocType via Property Setter.
    """
    current_options = frappe.db.get_value(
        "Property Setter",
        {"doc_type": "Attendance", "field_name": "status", "property": "options"},
        "value",
    )

    if not current_options:
        meta = frappe.get_meta("Attendance")
        field = meta.get_field("status")
        current_options = (field.options if field else "") or "Present\nAbsent\nOn Leave\nHalf Day\nWork From Home"

    options_list = [opt.strip() for opt in current_options.split("\n") if opt.strip()]

    if "Absent-Half Day" not in options_list:
        if "Absent" in options_list:
            idx = options_list.index("Absent") + 1
            options_list.insert(idx, "Absent-Half Day")
        else:
            options_list.append("Absent-Half Day")

    new_options = "\n" + "\n".join(options_list)

    make_property_setter(
        "Attendance",
        "status",
        "options",
        new_options,
        "Text",
        validate_fields_for_doctype=False,
    )

    frappe.clear_cache(doctype="Attendance")
    frappe.db.commit()
    print(f"Attendance status options updated to:\n{new_options}")
