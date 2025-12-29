"""
Comprehensive Attendance Backfill Script
Run this to create attendance for ALL dates with checkins that are missing attendance records.

Usage:
    bench --site [your-site] console
    Then: exec(open('apps/at_biometric_integration/at_biometric_integration/backfill_attendance.py').read())
"""
import frappe
from at_biometric_integration.utils.attendance_processing import backfill_all_missing_attendance

def run_backfill():
    """Run comprehensive backfill for all missing attendance"""
    print("=" * 60)
    print("ATTENDANCE BACKFILL - Processing ALL dates with checkins")
    print("=" * 60)
    
    try:
        result = backfill_all_missing_attendance()
        print(f"\n✅ Backfill completed successfully!")
        print(f"   Processed {len(result)} attendance records")
        print("\nCheck the Attendance list to verify all dates now have attendance records.")
    except Exception as e:
        print(f"\n❌ Error during backfill: {e}")
        frappe.log_error(str(e), "Backfill Attendance Script Error")
        raise

if __name__ == "__main__":
    frappe.connect()
    run_backfill()
    frappe.db.commit()

