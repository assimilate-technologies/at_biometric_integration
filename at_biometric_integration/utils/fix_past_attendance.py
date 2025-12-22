import frappe
from at_biometric_integration.utils.attendance_processing import process_attendance_realtime, auto_submit_due_attendances

def run_fix():
    print("Starting Attendance Fix...")
    
    # DEBUG: Check counts
    emp_count = frappe.db.count("Employee", {"status": "Active"})
    chk_count = frappe.db.count("Employee Checkin")
    att_count = frappe.db.count("Attendance")
    print(f"DEBUG: Found {emp_count} Active Employees, {chk_count} Checkins, {att_count} Attendance records.")

    if emp_count > 0:
        first_emp = frappe.get_all("Employee", filters={"status": "Active"}, limit=1)[0].name
        print(f"DEBUG: First Employee: {first_emp}")
        emp_checkins = frappe.db.count("Employee Checkin", {"employee": first_emp})
        print(f"DEBUG: Checkins for {first_emp}: {emp_checkins}")

    # 1. Recalculate Attendance (First-In Last-Out)
    print("Recalculating attendance based on checkins (First-In Last-Out)...")
    try:
        updated = process_attendance_realtime()
        print(f"Recalculated/Updated {len(updated)} attendance records.")
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
