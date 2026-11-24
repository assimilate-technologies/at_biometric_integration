import frappe
from at_biometric_integration.utils.sync_existing_records import update_existing_wfh_and_half_day_attendance


def execute():
    """Sync existing Attendance records to Work From Home or Half Day based on approved WFH regularizations and half-day leaves."""
    update_existing_wfh_and_half_day_attendance()
