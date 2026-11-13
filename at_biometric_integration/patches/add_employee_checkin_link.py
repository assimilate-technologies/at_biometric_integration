import frappe
from frappe.utils import getdate


def execute():
    fix_checkin_table_schema()
    update_employee_checkin_field()
    backfill_employee_checkins()
    frappe.db.commit()


def fix_checkin_table_schema():
    """Ensure tabcheckin table has all child table columns: parent, parentfield, parenttype."""
    if frappe.db.exists("DocType", "checkin"):
        frappe.db.set_value("DocType", "checkin", "istable", 1, update_modified=False)

    frappe.db.commit()

    if frappe.db.table_exists("checkin"):
        columns = frappe.db.get_table_columns("checkin")

        if "parent" not in columns:
            frappe.db.sql_ddl("ALTER TABLE `tabcheckin` ADD COLUMN `parent` VARCHAR(140) DEFAULT NULL")
            try:
                frappe.db.sql_ddl("ALTER TABLE `tabcheckin` ADD INDEX `parent` (`parent`)")
            except Exception:
                pass

        if "parentfield" not in columns:
            frappe.db.sql_ddl("ALTER TABLE `tabcheckin` ADD COLUMN `parentfield` VARCHAR(140) DEFAULT NULL")

        if "parenttype" not in columns:
            frappe.db.sql_ddl("ALTER TABLE `tabcheckin` ADD COLUMN `parenttype` VARCHAR(140) DEFAULT NULL")

        frappe.db.commit()

    try:
        frappe.reload_doc("at_biometric_integration", "doctype", "checkin", force=True)
    except Exception:
        pass


def update_employee_checkin_field():
    """Change employee_checkin from Link to Table field on Attendance,
    linked to the 'checkin' child doctype."""

    existing = frappe.db.get_value(
        "Custom Field",
        {"dt": "Attendance", "fieldname": "employee_checkin"},
        ["name", "fieldtype", "options"],
        as_dict=True,
    )

    if existing:
        cf = frappe.get_doc("Custom Field", existing.name)
        cf.fieldtype = "Table"
        cf.options = "checkin"
        cf.label = "Employee Checkins"
        cf.insert_after = "out_time"
        cf.hidden = 0
        cf.read_only = 0
        cf.save(ignore_permissions=True)
    else:
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "Attendance",
                "fieldname": "employee_checkin",
                "label": "Employee Checkins",
                "fieldtype": "Table",
                "options": "checkin",
                "insert_after": "out_time",
                "hidden": 0,
                "read_only": 0,
            }
        ).insert(ignore_permissions=True)

    frappe.clear_cache(doctype="Attendance")
    frappe.clear_cache(doctype="checkin")


def backfill_employee_checkins():
    """Populate the checkin child table for every existing Attendance record
    with ALL Employee Checkin rows for that employee + date, and set
    the 'attendance' link on Employee Checkin for the Connection tab count."""

    attendances = frappe.get_all(
        "Attendance",
        fields=["name", "employee", "attendance_date", "status"],
        order_by="attendance_date asc",
        limit_page_length=0,
    )
    if not attendances:
        return

    # Collect all employees to batch-fetch checkins
    employees = sorted({a.employee for a in attendances if a.employee})
    if not employees:
        return

    # Fetch ALL Employee Checkins for these employees in one query
    all_checkins = frappe.get_all(
        "Employee Checkin",
        filters={"employee": ["in", employees]},
        fields=["name", "employee", "time", "attendance"],
        order_by="time asc",
        limit_page_length=0,
    )

    # Group by (employee, date)
    by_day = {}
    for c in all_checkins:
        if c.get("time"):
            key = (c.employee, getdate(c.time))
            by_day.setdefault(key, []).append(c)

    # Fetch existing child rows to avoid duplicates
    existing_children = frappe.get_all(
        "checkin",
        filters={"parenttype": "Attendance", "parentfield": "employee_checkin"},
        fields=["parent", "checkin"],
        limit_page_length=0,
    )
    existing_set = {(r.parent, r.checkin) for r in existing_children}

    updated = 0
    for att in attendances:
        candidates = by_day.get((att.employee, getdate(att.attendance_date)), [])
        if not candidates:
            continue

        added = 0
        for idx, c in enumerate(candidates, start=1):
            # 1. Update reverse link on Employee Checkin for Connection tab count
            if c.attendance != att.name:
                frappe.db.set_value("Employee Checkin", c.name, "attendance", att.name, update_modified=False)

            # 2. Add child table row if not already present
            if (att.name, c.name) in existing_set:
                continue

            child = frappe.new_doc("checkin")
            child.parent = att.name
            child.parenttype = "Attendance"
            child.parentfield = "employee_checkin"
            child.idx = idx
            child.checkin = c.name
            child.db_insert()
            existing_set.add((att.name, c.name))
            added += 1

        if added:
            updated += 1

        # Rule: First record time as in_time, last record time as out_time.
        # When only one record, in_time and out_time show the same.
        valid_times = [c.time for c in candidates if c.get("time")]
        if valid_times:
            in_t = valid_times[0]
            out_t = valid_times[-1]
            hrs = "00:00:00"
            if in_t != out_t:
                from at_biometric_integration.utils.helpers import calculate_working_hours
                hrs = calculate_working_hours(in_t, out_t)

            from at_biometric_integration.utils.attendance_processing import get_working_hours_seconds, get_status_by_working_hours
            is_on_leave = (att.status == "On Leave")

            if is_on_leave:
                new_status = att.status
            elif in_t == out_t:
                new_status = "Absent"
            else:
                work_seconds = get_working_hours_seconds(hrs)
                new_status = get_status_by_working_hours(work_seconds, in_t, out_t)

            update_data = {
                "in_time": in_t,
                "out_time": out_t,
                "working_hours": hrs,
            }
            if att.status != "Holiday":
                update_data["status"] = new_status

            frappe.db.set_value("Attendance", att.name, update_data, update_modified=False)

    frappe.logger().info(
        f"employee_checkin backfill: populated checkin table for {updated} Attendance records"
    )
