import frappe
from erpnext.controllers.status_updater import validate_status
from hrms.hr.doctype.attendance.attendance import (
    Attendance,
    validate_active_employee,
)


class CustomAttendance(Attendance):
    def validate(self):
        # Allow 'Absent-Half Day' alongside all standard attendance statuses
        validate_status(
            self.status,
            [
                "Present",
                "Absent",
                "Absent-Half Day",
                "On Leave",
                "Half Day",
                "Work From Home",
            ],
        )
        validate_active_employee(self.employee)
        self.validate_attendance_date()
        self.validate_duplicate_record()
        self.validate_overlapping_shift_attendance()
        self.validate_employee_status()
        self.check_leave_record()
