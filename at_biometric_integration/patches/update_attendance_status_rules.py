import frappe


def execute():
    """Recompute status on all existing Attendance records using the current rules:
         < half_day_from (5 hr default)              -> 'Absent'
         half_day_from to half_day_to (9 hr default) -> 'Absent-Half Day'
           (8:40-9:00 grace window -> 'Present', max 3 per employee per month)
         >= half_day_to                              -> 'Present'

    On Leave / Holiday / Work From Home records are left untouched.
    Safe to re-run (idempotent).
    """
    from at_biometric_integration.utils.attendance_processing import (
        update_existing_attendance_status,
    )

    result = update_existing_attendance_status()
    frappe.logger().info(
        f"update_attendance_status_rules patch: updated {result.get('updated')} "
        f"of {result.get('total')} Attendance records"
    )
