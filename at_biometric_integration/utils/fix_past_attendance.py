import frappe
from at_biometric_integration.utils.attendance_processing import process_attendance_realtime, auto_submit_due_attendances

def run_fix():
    print("Starting Attendance Fix...")
    from frappe.utils import getdate, add_days
    
    # DEBUG: Check counts
    emp_count = frappe.db.count("Employee", {"status": "Active"})
    chk_count = frappe.db.count("Employee Checkin")
    att_count = frappe.db.count("Attendance")
    print(f"DEBUG: Found {emp_count} Active Employees, {chk_count} Checkins, {att_count} Attendance records.")

    # 1. Recalculate Attendance (First-In Last-Out)
    # Defaulting to last 30 days for a thorough fix
    to_date = getdate()
    from_date = add_days(to_date, -30)
    
    print(f"Recalculating attendance for all active employees from {from_date} to {to_date}...")
    try:
        updated = process_attendance_realtime(from_date, to_date)
        print(f"Processed {len(updated)} attendance records entries (Created/Updated).")
    except Exception as e:
        print(f"Error during recalculation: {e}")
        frappe.log_error(e, "Fix Past Attendance Recalculation")

    # 2. Auto Submit Past Attendance
    print("Attempting to auto-submit due attendances...")
    try:
        submitted = auto_submit_due_attendances()
        print(f"Auto-submitted {len(submitted)} attendance records.")
    except Exception as e:
        print(f"Error during auto-submit: {e}")
        frappe.log_error(e, "Fix Past Attendance Auto-Submit")

    print("Fix completed.")

if __name__ == "__main__":
    frappe.connect()
    run_fix()
