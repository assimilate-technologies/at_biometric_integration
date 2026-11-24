import frappe
from frappe.utils import getdate


def update_existing_wfh_and_half_day_attendance():
    """
    Backfill / sync existing Attendance records:
    1. Work From Home:
       - Find Attendance records linked to an approved WFH Attendance Regularization.
       - Also find Attendance records for an employee that fall within the date range
         (from_date to date) of an approved WFH Attendance Regularization.
       - Update status to 'Work From Home' and link attendance_regularization if not set.
    2. Half Day Leave:
       - Find Attendance records linked to a Leave Application with half_day = 1.
       - Also find Attendance records where an approved half-day Leave Application exists
         for the employee on that attendance_date.
       - Update status to 'Half Day' and link leave_application / leave_type if not set.
    """
    wfh_updated = 0
    half_day_updated = 0

    print("--- 1. Updating Work From Home Attendance records ---")

    # A) All approved WFH Attendance Regularizations
    wfh_regs = frappe.get_all(
        "Attendance Regularization",
        filters={
            "is_work_from_home": 1,
            "docstatus": ["!=", 2],
            "workflow_state": ["in", ["Approved By HR", "Approved", "HR Approve"]],
        },
        fields=["name", "employee", "from_date", "date"],
    )

    # Also include any with docstatus=1 regardless of workflow_state
    submitted_wfh_regs = frappe.get_all(
        "Attendance Regularization",
        filters={
            "is_work_from_home": 1,
            "docstatus": 1,
        },
        fields=["name", "employee", "from_date", "date"],
    )
    all_wfh_regs = {r["name"]: r for r in (wfh_regs + submitted_wfh_regs)}

    for reg_name, reg in all_wfh_regs.items():
        start_date = reg.get("from_date") or reg.get("date")
        end_date = reg.get("date")
        if not start_date or not end_date or not reg.get("employee"):
            continue

        # Find all attendance records in this date range for this employee
        attendances = frappe.get_all(
            "Attendance",
            filters={
                "employee": reg["employee"],
                "attendance_date": ["between", [start_date, end_date]],
                "docstatus": ["!=", 2],
            },
            fields=["name", "status", "attendance_regularization"],
        )

        for att in attendances:
            needs_update = False
            update_data = {}

            if att.get("status") != "Work From Home":
                update_data["status"] = "Work From Home"
                needs_update = True

            if att.get("attendance_regularization") != reg_name:
                update_data["attendance_regularization"] = reg_name
                needs_update = True

            if needs_update:
                frappe.db.set_value("Attendance", att["name"], update_data, update_modified=False)
                wfh_updated += 1
                print(f"  [WFH] Updated Attendance {att['name']} ({reg['employee']} on {start_date}..{end_date}) -> Work From Home")

    # B) Any attendance that already has attendance_regularization linked where regularization is WFH
    already_linked_wfh = frappe.db.sql(
        """
        SELECT a.name, a.status, a.attendance_regularization
        FROM `tabAttendance` a
        INNER JOIN `tabAttendance Regularization` ar ON ar.name = a.attendance_regularization
        WHERE ar.is_work_from_home = 1
          AND a.status != 'Work From Home'
          AND a.docstatus != 2
        """,
        as_dict=True,
    )
    for row in already_linked_wfh:
        frappe.db.set_value("Attendance", row["name"], "status", "Work From Home", update_modified=False)
        wfh_updated += 1
        print(f"  [WFH-Linked] Updated Attendance {row['name']} -> Work From Home")

    print(f"Total Work From Home Attendance records updated: {wfh_updated}")

    print("\n--- 2. Updating Half Day Leave Attendance records ---")

    # A) All approved Leave Applications with half_day = 1
    half_day_leaves = frappe.get_all(
        "Leave Application",
        filters={
            "half_day": 1,
            "docstatus": 1,
            "status": "Approved",
        },
        fields=["name", "employee", "from_date", "to_date", "half_day_date", "leave_type"],
    )

    for leave in half_day_leaves:
        # Determine the target date of the half day
        target_date = leave.get("half_day_date") or leave.get("from_date")
        if not target_date or not leave.get("employee"):
            continue

        attendances = frappe.get_all(
            "Attendance",
            filters={
                "employee": leave["employee"],
                "attendance_date": target_date,
                "docstatus": ["!=", 2],
            },
            fields=["name", "status", "leave_application", "leave_type"],
        )

        for att in attendances:
            needs_update = False
            update_data = {}

            if att.get("status") != "Half Day":
                update_data["status"] = "Half Day"
                needs_update = True

            if att.get("leave_application") != leave["name"]:
                update_data["leave_application"] = leave["name"]
                needs_update = True

            if leave.get("leave_type") and att.get("leave_type") != leave["leave_type"]:
                update_data["leave_type"] = leave["leave_type"]
                needs_update = True

            if needs_update:
                frappe.db.set_value("Attendance", att["name"], update_data, update_modified=False)
                half_day_updated += 1
                print(f"  [Half Day] Updated Attendance {att['name']} ({leave['employee']} on {target_date}) -> Half Day")

    # B) Any attendance that has leave_application linked where the leave application is half_day = 1
    already_linked_half_day = frappe.db.sql(
        """
        SELECT a.name, a.status, a.leave_application
        FROM `tabAttendance` a
        INNER JOIN `tabLeave Application` la ON la.name = a.leave_application
        WHERE la.half_day = 1
          AND a.status != 'Half Day'
          AND a.docstatus != 2
        """,
        as_dict=True,
    )
    for row in already_linked_half_day:
        frappe.db.set_value("Attendance", row["name"], "status", "Half Day", update_modified=False)
        half_day_updated += 1
        print(f"  [HalfDay-Linked] Updated Attendance {row['name']} -> Half Day")

    print(f"Total Half Day Attendance records updated: {half_day_updated}")

    frappe.db.commit()
    print("\nDatabase changes committed successfully!")
    return {
        "wfh_updated": wfh_updated,
        "half_day_updated": half_day_updated,
    }


def execute():
    """For patch execution via bench migrate"""
    update_existing_wfh_and_half_day_attendance()


if __name__ == "__main__":
    import sys, os
    site = sys.argv[1] if len(sys.argv) > 1 else "version15.localhost"
    sites_path = os.environ.get("SITES_PATH") or "/home/rahul/frappe-bench-v15/sites"
    frappe.init(site=site, sites_path=sites_path)
    frappe.connect()
    try:
        update_existing_wfh_and_half_day_attendance()
    finally:
        frappe.destroy()
