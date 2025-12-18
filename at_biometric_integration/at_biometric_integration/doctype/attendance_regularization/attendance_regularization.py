from frappe.model.document import Document
import frappe
from datetime import datetime, time, timedelta

class AttendanceRegularization(Document):
    def on_submit(self):
        # Always allow submit, but process only if Approved By HR
        if self.workflow_state == "Approved By HR":
            self.process_approved_regularization()
        else:
            # Just log info (no attendance or checkin creation)
            frappe.logger().info(
                f"Attendance Regularization {self.name} submitted with state {self.workflow_state}. "
                "No Employee Checkin or Attendance created."
            )

    def process_approved_regularization(self):
        """
        Process Attendance Regularization when approved by HR.
        Creates or updates Employee Checkin and Attendance.
        """
        # Fetch company and shift from Employee
        employee_details = frappe.get_value(
            "Employee",
            self.employee,
            ["company", "default_shift"],
            as_dict=True
        )

        if not employee_details:
            frappe.throw(f"Employee {self.employee} not found.")

        def combine_date_time(date, time_obj):
            """Combine date with time or timedelta to form a datetime object."""
            if isinstance(time_obj, timedelta):
                return datetime.combine(date, (datetime.min + time_obj).time())
            elif isinstance(time_obj, time):
                return datetime.combine(date, time_obj)
            elif isinstance(time_obj, datetime):
                return time_obj
            else:
                frappe.throw("Invalid time format for in_time or out_time.")

        in_time_dt = None
        out_time_dt = None

        # Create or update Employee Checkin for IN time
        if self.in_time:
            in_time_dt = combine_date_time(self.date, self.in_time)
            self.create_or_update_checkin(self.employee, in_time_dt, "IN", employee_details.company)

        # Create or update Employee Checkin for OUT time
        if self.out_time:
            out_time_dt = combine_date_time(self.date, self.out_time)
            self.create_or_update_checkin(self.employee, out_time_dt, "OUT", employee_details.company)

        # Create or update Attendance record
        self.create_or_update_attendance(employee_details, in_time_dt, out_time_dt)

    def create_or_update_checkin(self, employee, time, log_type, company):
        """
        Create or update Employee Checkin record.
        """
        existing_checkin = frappe.get_all(
            "Employee Checkin",
            filters={"employee": employee, "time": time, "log_type": log_type},
            limit=1
        )

        if existing_checkin:
            frappe.db.set_value("Employee Checkin", existing_checkin[0].name, {"time": time})
        else:
            frappe.get_doc({
                "doctype": "Employee Checkin",
                "employee": employee,
                "time": time,
                "log_type": log_type,
                "company": company,
                "latitude": 0.0,
                "longitude": 0.0
            }).insert(ignore_permissions=True)

    def create_or_update_attendance(self, employee_details, in_time=None, out_time=None):
        """
        Create or update Attendance record.
        """
        existing_attendance = frappe.db.get_value(
            "Attendance",
            {"employee": self.employee, "attendance_date": self.date},
            "name"
        )

        working_hours = 0.0
        if in_time and out_time:
            diff = out_time - in_time
            working_hours = round(diff.total_seconds() / 3600, 2)

        attendance_data = {
            "employee": self.employee,
            "employee_name": self.employee_name,
            "attendance_date": self.date,
            "status": self.attendance_status,
            "company": employee_details.company,
            "shift": employee_details.default_shift,
            "docstatus": 1,
            "in_time": in_time,
            "out_time": out_time,
            "working_hours": working_hours
        }

        if existing_attendance:
            frappe.db.set_value("Attendance", existing_attendance, attendance_data)
        else:
            frappe.get_doc({
                "doctype": "Attendance",
                **attendance_data
            }).insert(ignore_permissions=True)
            
    
    def on_cancel(self):
        """
        On cancellation of Attendance Regularization:
        - Delete only Employee Checkin records created for this regularization's in_time and out_time.
        - Cancel & delete related Attendance records created from these checkins.
        - Set workflow_state to 'Canceled'.
        """

        # --- Update workflow state safely ---
        if self.workflow_state != "Canceled":
            self.workflow_state = "Canceled"
            self.db_set("workflow_state", "Canceled", update_modified=False)

        # --- Prepare check-in/out datetimes ---
        checkin_times = []
        if self.in_time:
            in_dt = datetime.combine(self.date, self.in_time) if isinstance(self.in_time, time) else self.in_time
            checkin_times.append(in_dt)
        if self.out_time:
            out_dt = datetime.combine(self.date, self.out_time) if isinstance(self.out_time, time) else self.out_time
            checkin_times.append(out_dt)

        if not checkin_times:
            frappe.logger().info(f"[Attendance Regularization] No check-in/out times found for {self.name}")
            return

        # --- Delete Employee Checkin records that match in/out times ---
        checkins_to_delete = frappe.get_all(
            "Employee Checkin",
            filters={"employee": self.employee, "time": ["in", checkin_times]},
            pluck="name"
        )

        for checkin_name in checkins_to_delete:
            try:
                frappe.delete_doc("Employee Checkin", checkin_name, ignore_permissions=True)
                frappe.logger().info(f"[Attendance Regularization] Deleted Employee Checkin: {checkin_name}")
            except Exception as e:
                frappe.log_error(f"Error deleting Employee Checkin {checkin_name}: {str(e)}")

        # --- Find related Attendance records on same date ---
        attendance_records = frappe.get_all(
            "Attendance",
            filters={"employee": self.employee, "attendance_date": self.date},
            pluck="name"
        )

        for attendance_name in attendance_records:
            try:
                attendance_doc = frappe.get_doc("Attendance", attendance_name)
                check_in = getattr(attendance_doc, "check_in", None)
                check_out = getattr(attendance_doc, "check_out", None)

                # If this attendance was created using the same in/out times, delete it
                if check_in in checkin_times or check_out in checkin_times:
                    if attendance_doc.docstatus == 1:
                        # Cancel submitted attendance first
                        attendance_doc.cancel()
                        frappe.logger().info(f"[Attendance Regularization] Canceled Attendance: {attendance_name}")

                    # Then delete the attendance record
                    frappe.delete_doc("Attendance", attendance_name, ignore_permissions=True)
                    frappe.logger().info(f"[Attendance Regularization] Deleted Attendance: {attendance_name}")

            except Exception as e:
                frappe.log_error(f"Error deleting Attendance {attendance_name}: {str(e)}")

        frappe.msgprint("Related Employee Checkin and Attendance records deleted successfully.")
    def validate(self):
        # Ensure in_time is before out_time if both are provided
        if self.in_time and self.out_time:
            in_time_dt = datetime.combine(self.date, self.in_time) if isinstance(self.in_time, time) else self.in_time
            out_time_dt = datetime.combine(self.date, self.out_time) if isinstance(self.out_time, time) else self.out_time
            if in_time_dt >= out_time_dt:
                frappe.throw("In Time must be before Out Time.")
   