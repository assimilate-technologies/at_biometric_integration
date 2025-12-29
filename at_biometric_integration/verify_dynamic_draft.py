import frappe
from frappe.utils import getdate, add_days
from at_biometric_integration.utils.attendance_processing import process_attendance_realtime

def test_dynamic_draft():
    emp = frappe.get_all('Employee', limit=1)[0].name
    # Use a date older than the default 2-day range
    old_date = add_days(getdate(), -10)
    print(f'Testing dynamic draft update for {emp} on {old_date}')

    # Cleanup existing record if any
    frappe.db.sql("DELETE FROM `tabAttendance` WHERE employee=%s AND attendance_date=%s", (emp, old_date))
    frappe.db.sql("DELETE FROM `tabEmployee Checkin` WHERE employee=%s AND DATE(time)=%s", (emp, old_date))
    frappe.db.commit()

    # 1. Create a Draft Attendance record manually (simulation)
    att = frappe.get_doc({
        'doctype': 'Attendance',
        'employee': emp,
        'attendance_date': old_date,
        'status': 'Absent',
        'docstatus': 0,
        'company': frappe.db.get_value('Employee', emp, 'company')
    })
    att.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f'Created manual Draft Attendance: {att.name} with status {att.status}')

    # 2. Create actual checkins for that date
    frappe.get_doc({
        'doctype': 'Employee Checkin',
        'employee': emp,
        'time': f'{old_date} 09:00:00',
        'log_type': 'IN',
        'latitude': '0.0',
        'longitude': '0.0'
    }).insert()
    frappe.get_doc({
        'doctype': 'Employee Checkin',
        'employee': emp,
        'time': f'{old_date} 18:00:00',
        'log_type': 'OUT',
        'latitude': '0.0',
        'longitude': '0.0'
    }).insert()
    frappe.db.commit()
    print('Created biometric checkins')

    # 3. Run realtime process without specific date range (default is last 2 days)
    print('Running attendance_processing.process_attendance_realtime() (default range)...')
    process_attendance_realtime()
    frappe.db.commit()

    # 4. Verify the old record was updated
    att.reload()
    print(f'Final Status: {att.status}, In: {att.in_time}, Out: {att.out_time}')

    if att.status == 'Present' and str(att.out_time).endswith('18:00:00'):
        print('SUCCESS: Dynamic Draft update worked correctly despite being outside default range.')
        # Cleanup
        frappe.db.sql("DELETE FROM `tabAttendance` WHERE name=%s", att.name)
        frappe.db.sql("DELETE FROM `tabEmployee Checkin` WHERE employee=%s AND DATE(time)=%s", (emp, old_date))
        frappe.db.commit()
    else:
        print('FAILURE: Dynamic Draft update did not process the old record.')

if __name__ == "__main__":
    test_dynamic_draft()
