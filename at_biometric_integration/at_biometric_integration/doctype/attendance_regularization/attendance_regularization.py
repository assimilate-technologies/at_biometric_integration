# from frappe.model.document import Document
# import frappe
# from datetime import datetime, time, timedelta
# from at_biometric_integration.utils.helpers import get_leave_status, is_holiday, determine_attendance_status

# class AttendanceRegularization(Document):
#     def on_submit(self):
#         # Always allow submit, but process only if Approved By HR
#         if self.workflow_state == "Approved By HR":
#             self.process_approved_regularization()
#         else:
#             # Just log info (no attendance or checkin creation)
#             frappe.logger().info(
#                 f"Attendance Regularization {self.name} submitted with state {self.workflow_state}. "
#                 "No Employee Checkin or Attendance created."
#             )

#     def process_approved_regularization(self):
#         """
#         Process Attendance Regularization when approved by HR.
#         Creates or updates Employee Checkin and Attendance.
#         """
#         # Fetch company and shift from Employee
#         employee_details = frappe.get_value(
#             "Employee",
#             self.employee,
#             ["company", "default_shift"],
#             as_dict=True
#         )

#         if not employee_details:
#             frappe.throw(f"Employee {self.employee} not found.")

#         def combine_date_time(date, time_obj):
#             """Combine date with time or timedelta to form a datetime object."""
#             if isinstance(time_obj, timedelta):
#                 return datetime.combine(date, (datetime.min + time_obj).time())
#             elif isinstance(time_obj, time):
#                 return datetime.combine(date, time_obj)
#             elif isinstance(time_obj, datetime):
#                 return time_obj
#             else:
#                 frappe.throw("Invalid time format for in_time or out_time.")

#         in_time_dt = None
#         out_time_dt = None

#         # Create or update Employee Checkin for IN time
#         if self.in_time:
#             in_time_dt = combine_date_time(self.date, self.in_time)
#             self.create_or_update_checkin(self.employee, in_time_dt, "IN", employee_details.company)

#         # Create or update Employee Checkin for OUT time
#         if self.out_time:
#             out_time_dt = combine_date_time(self.date, self.out_time)
#             self.create_or_update_checkin(self.employee, out_time_dt, "OUT", employee_details.company)

#         # Create or update Attendance record
#         self.create_or_update_attendance(employee_details, in_time_dt, out_time_dt)

#     def create_or_update_checkin(self, employee, time, log_type, company):
#         """
#         Create or update Employee Checkin record.
#         """
#         existing_checkin = frappe.get_all(
#             "Employee Checkin",
#             filters={"employee": employee, "time": time, "log_type": log_type},
#             limit=1
#         )

#         if existing_checkin:
#             frappe.db.set_value("Employee Checkin", existing_checkin[0].name, {"time": time})
#         else:
#             frappe.get_doc({
#                 "doctype": "Employee Checkin",
#                 "employee": employee,
#                 "time": time,
#                 "log_type": log_type,
#                 "company": company,
#                 "latitude": "0.0",
#                 "longitude": "0.0"
#             }).insert(ignore_permissions=True)

#     def create_or_update_attendance(self, employee_details, in_time=None, out_time=None):
#         """
#         Create or update Attendance record.
#         """
#         existing_attendance = frappe.db.get_value(
#             "Attendance",
#             {"employee": self.employee, "attendance_date": self.date},
#             "name"
#         )

#         working_hours = 0.0
#         if in_time and out_time:
#             diff = out_time - in_time
#             working_hours = round(diff.total_seconds() / 3600, 2)

#         # Calculate status dynamically
#         leave_status = get_leave_status(self.employee, self.date)
#         holiday_flag = is_holiday(self.employee, self.date)
#         status = determine_attendance_status(working_hours, leave_status, holiday_flag)

#         attendance_data = {
#             "employee": self.employee,
#             "employee_name": self.employee_name,
#             "attendance_date": self.date,
#             "status": status,
#             "company": employee_details.company,
#             "shift": employee_details.default_shift,
#             "docstatus": 1,
#             "in_time": in_time,
#             "out_time": out_time,
#             "working_hours": working_hours
#         }

#         if existing_attendance:
#             frappe.db.set_value("Attendance", existing_attendance, attendance_data)
#         else:
#             frappe.get_doc({
#                 "doctype": "Attendance",
#                 **attendance_data
#             }).insert(ignore_permissions=True)
            
    
#     def on_cancel(self):
#         """
#         On cancellation of Attendance Regularization:
#         - Delete only Employee Checkin records created for this regularization's in_time and out_time.
#         - Cancel & delete related Attendance records created from these checkins.
#         - Set workflow_state to 'Canceled'.
#         """

#         # --- Update workflow state safely ---
#         if self.workflow_state != "Canceled":
#             self.workflow_state = "Canceled"
#             self.db_set("workflow_state", "Canceled", update_modified=False)

#         # --- Prepare check-in/out datetimes ---
#         checkin_times = []
#         if self.in_time:
#             in_dt = datetime.combine(self.date, self.in_time) if isinstance(self.in_time, time) else self.in_time
#             checkin_times.append(in_dt)
#         if self.out_time:
#             out_dt = datetime.combine(self.date, self.out_time) if isinstance(self.out_time, time) else self.out_time
#             checkin_times.append(out_dt)

#         if not checkin_times:
#             frappe.logger().info(f"[Attendance Regularization] No check-in/out times found for {self.name}")
#             return

#         # --- Delete Employee Checkin records that match in/out times ---
#         checkins_to_delete = frappe.get_all(
#             "Employee Checkin",
#             filters={"employee": self.employee, "time": ["in", checkin_times]},
#             pluck="name"
#         )

#         for checkin_name in checkins_to_delete:
#             try:
#                 frappe.delete_doc("Employee Checkin", checkin_name, ignore_permissions=True)
#                 frappe.logger().info(f"[Attendance Regularization] Deleted Employee Checkin: {checkin_name}")
#             except Exception as e:
#                 frappe.log_error(f"Error deleting Employee Checkin {checkin_name}: {str(e)}")

#         # --- Find related Attendance records on same date ---
#         attendance_records = frappe.get_all(
#             "Attendance",
#             filters={"employee": self.employee, "attendance_date": self.date},
#             pluck="name"
#         )

#         for attendance_name in attendance_records:
#             try:
#                 attendance_doc = frappe.get_doc("Attendance", attendance_name)
#                 check_in = getattr(attendance_doc, "check_in", None)
#                 check_out = getattr(attendance_doc, "check_out", None)

#                 # If this attendance was created using the same in/out times, delete it
#                 if check_in in checkin_times or check_out in checkin_times:
#                     if attendance_doc.docstatus == 1:
#                         # Cancel submitted attendance first
#                         attendance_doc.cancel()
#                         frappe.logger().info(f"[Attendance Regularization] Canceled Attendance: {attendance_name}")

#                     # Then delete the attendance record
#                     frappe.delete_doc("Attendance", attendance_name, ignore_permissions=True)
#                     frappe.logger().info(f"[Attendance Regularization] Deleted Attendance: {attendance_name}")

#             except Exception as e:
#                 frappe.log_error(f"Error deleting Attendance {attendance_name}: {str(e)}")

#         frappe.msgprint("Related Employee Checkin and Attendance records deleted successfully.")
#     def validate(self):
#         # Ensure in_time is before out_time if both are provided
#         if self.in_time and self.out_time:
#             in_time_dt = datetime.combine(self.date, self.in_time) if isinstance(self.in_time, time) else self.in_time
#             out_time_dt = datetime.combine(self.date, self.out_time) if isinstance(self.out_time, time) else self.out_time
#             if in_time_dt >= out_time_dt:
#                 frappe.throw("In Time must be before Out Time.")
   




from frappe.model.document import Document
import frappe
from datetime import datetime, time, timedelta

from at_biometric_integration.utils.helpers import (
    get_leave_status,
    is_holiday,
    determine_attendance_status,
)


class AttendanceRegularization(Document):

    def before_save(self):
        self.calculate_and_set_attendance_status()

    def calculate_and_set_attendance_status(self):
        """
        Calculate hours between in_time and out_time:
          - < 5 hr         -> 'Absent'
          - 5 to 8:45 hr   -> 'Half Day'
          - >= 8:45 hr     -> 'Present'
        Preserves 'Work From Home' when is_work_from_home checkbox is ticked.
        """
        if self.is_work_from_home:
            self.attendance_status = "Work From Home"
            return

        if not self.in_time or not self.out_time:
            return

        def parse_time_string(value):
            s = str(value).strip()
            for fmt in ("%H:%M:%S.%f", "%H:%M:%S", "%H:%M"):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    continue
            return None

        def to_seconds(value):
            if isinstance(value, timedelta):
                return value.total_seconds()
            if isinstance(value, (datetime, time)):
                return value.hour * 3600 + value.minute * 60 + value.second
            if isinstance(value, str):
                pt = parse_time_string(value)
                if pt:
                    return pt.hour * 3600 + pt.minute * 60 + pt.second
            return 0

        in_sec = to_seconds(self.in_time)
        out_sec = to_seconds(self.out_time)

        if in_sec and out_sec:
            diff = out_sec - in_sec
            if diff < 0:
                diff += 24 * 3600

            FIVE_HOURS = 5 * 3600                     # 18,000 seconds (5:00:00)
            EIGHT_FORTY_FIVE = 8 * 3600 + 45 * 60     # 31,500 seconds (8:45:00)

            if diff < FIVE_HOURS:
                self.attendance_status = "Absent"
            elif diff < EIGHT_FORTY_FIVE:
                self.attendance_status = "Half Day"
            else:
                self.attendance_status = "Present"

    def validate(self):
        """
        Validate:
        1. In Time is earlier than Out Time.
        2. Set attendance_status based on duration between in_time and out_time.
        3. No duplicate Attendance Regularization exists for same employee + date.
        4. The regularization is being created within the allowed time window
           (regularization_from_hours after shift start  →
            regularization_to_hours after shift end) defined in Attendance Settings.
        """
        self.calculate_and_set_attendance_status()

        if not self.is_work_from_home:
            if not self.in_time or not self.out_time:
                frappe.throw(
                    frappe._("In Time and Out Time are mandatory when Attendance Status is not Work From Home.")
                )

        def parse_time_string(value):
            """Parse a time string that may be HH:MM, HH:MM:SS, or HH:MM:SS.ffffff."""
            s = value.strip()
            for fmt in ("%H:%M:%S.%f", "%H:%M:%S", "%H:%M"):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    continue
            return None

        def convert_to_seconds(value):
            if isinstance(value, timedelta):
                return value.total_seconds()

            if isinstance(value, datetime):
                return (
                    value.hour * 3600
                    + value.minute * 60
                    + value.second
                    + value.microsecond / 1_000_000
                )

            if isinstance(value, time):
                return (
                    value.hour * 3600
                    + value.minute * 60
                    + value.second
                    + value.microsecond / 1_000_000
                )

            if isinstance(value, str):
                parsed_time = parse_time_string(value)
                if parsed_time:
                    return (
                        parsed_time.hour * 3600
                        + parsed_time.minute * 60
                        + parsed_time.second
                        + parsed_time.microsecond / 1_000_000
                    )
                frappe.throw(
                    f"Invalid time format: {value}"
                )

            frappe.throw(
                f"Unsupported time format: {value}"
            )

        if self.in_time and self.out_time:
            in_seconds = convert_to_seconds(self.in_time)
            out_seconds = convert_to_seconds(self.out_time)

            if in_seconds >= out_seconds:
                frappe.throw(
                    "In Time must be before Out Time."
                )

        # --- Duplicate check ---
        existing = frappe.db.exists(
            "Attendance Regularization",
            {
                "employee": self.employee,
                "date": self.date,
                "docstatus": ["!=", 2],   # not cancelled
                "name": ["!=", self.name or ""],
            },
        )
        if existing:
            frappe.throw(
                f"An Attendance Regularization already exists for "
                f"Employee {self.employee} on {self.date}: {existing}. "
                "Please cancel the existing record before creating a new one."
            )

        # --- Regularization window check ---
        self._validate_regularization_window()

    def _validate_regularization_window(self):
        """
        Validate that the regularization is being created/saved within the
        allowed time window configured in Attendance Settings:
          - Window opens : shift_start  + regularization_from_hours
          - Window closes: shift_end    + regularization_to_hours
        If enable_regularization is False in Settings, skip this check.
        """
        from at_biometric_integration.utils.helpers import (
            get_attendance_settings,
            get_employee_shift,
            get_shift_end_datetime,
        )
        from frappe.utils import now_datetime, get_datetime

        settings = get_attendance_settings()

        if not settings.enable_regularization:
            return

        reg_from_hours = float(settings.regularization_from_hours or 0)
        reg_to_hours = float(settings.regularization_to_hours or 24)

        # Get the employee's shift for the regularization date
        shift_doc = get_employee_shift(self.employee, self.date)

        # Determine shift start datetime
        if shift_doc and getattr(shift_doc, "start_time", None):
            shift_start_dt = get_datetime(f"{self.date} {shift_doc.start_time}")
        else:
            # Default shift start 09:00 when not configured
            shift_start_dt = get_datetime(f"{self.date} 09:00:00")

        # Determine shift end datetime using existing helper
        shift_end_dt = get_shift_end_datetime(shift_doc, self.date)

        window_open  = shift_start_dt + timedelta(hours=reg_from_hours)
        window_close = shift_end_dt   + timedelta(hours=reg_to_hours)

        now = now_datetime()

        if now < window_open:
            frappe.throw(
                f"Attendance Regularization for {self.date} cannot be submitted yet. "
                f"The regularization window opens at {window_open.strftime('%d-%m-%Y %H:%M')}."
            )

        if now > window_close:
            frappe.throw(
                f"Attendance Regularization for {self.date} cannot be submitted. "
                f"The regularization window closed at {window_close.strftime('%d-%m-%Y %H:%M')}."
            )

    def on_submit(self):
        # Process only when Approved By HR.
        if self.workflow_state == "Approved By HR":
            self.process_approved_regularization()
        else:
            frappe.logger().info(
                f"Attendance Regularization {self.name} "
                f"submitted with state {self.workflow_state}. "
                "No Employee Checkin or Attendance created."
            )

    def process_approved_regularization(self):
        """
        Process Attendance Regularization when approved by HR.
        Creates or updates Employee Checkin and Attendance.
        """

        employee_details = frappe.get_value(
            "Employee",
            self.employee,
            ["company", "default_shift"],
            as_dict=True,
        )

        if not employee_details:
            frappe.throw(
                f"Employee {self.employee} not found."
            )

        def combine_date_time(date, time_obj):
            """Combine the attendance date and time safely."""

            if isinstance(time_obj, timedelta):
                seconds = time_obj.total_seconds()

                if seconds < 0 or seconds >= 86400:
                    frappe.throw(
                        "Time value must be within a single day."
                    )

                time_obj = (
                    datetime.min + time_obj
                ).time()

                return datetime.combine(date, time_obj)

            elif isinstance(time_obj, time):
                return datetime.combine(date, time_obj)

            elif isinstance(time_obj, datetime):
                return time_obj

            elif isinstance(time_obj, str):
                s = time_obj.strip()
                parsed_time = None
                for fmt in ("%H:%M:%S.%f", "%H:%M:%S", "%H:%M"):
                    try:
                        parsed_time = datetime.strptime(s, fmt).time()
                        break
                    except ValueError:
                        continue

                if parsed_time is None:
                    frappe.throw(
                        f"Invalid time format: {time_obj}"
                    )

                return datetime.combine(date, parsed_time)

            else:
                frappe.throw(
                    "Invalid time format for in_time or out_time."
                )

        in_time_dt = None
        out_time_dt = None

        # Create or update Employee Checkin for IN time.
        if self.in_time:
            in_time_dt = combine_date_time(
                self.date, self.in_time
            )

            self.create_or_update_checkin(
                self.employee,
                in_time_dt,
                "IN",
                employee_details.company,
            )

        # Create or update Employee Checkin for OUT time.
        if self.out_time:
            out_time_dt = combine_date_time(
                self.date, self.out_time
            )

            self.create_or_update_checkin(
                self.employee,
                out_time_dt,
                "OUT",
                employee_details.company,
            )

        # Create or update Attendance record.
        self.create_or_update_attendance(
            employee_details,
            in_time_dt,
            out_time_dt,
        )

    def create_or_update_checkin(
        self, employee, time, log_type, company
    ):
        """Create or update Employee Checkin record."""

        existing_checkin = frappe.get_all(
            "Employee Checkin",
            filters={
                "employee": employee,
                "time": time,
                "log_type": log_type,
            },
            fields=["name"],
            limit=1,
        )

        if existing_checkin:
            frappe.db.set_value(
                "Employee Checkin",
                existing_checkin[0].name,
                {"time": time},
            )
        else:
            frappe.get_doc(
                {
                    "doctype": "Employee Checkin",
                    "employee": employee,
                    "time": time,
                    "log_type": log_type,
                    "company": company,
                    "latitude": "0.0",
                    "longitude": "0.0",
                }
            ).insert(ignore_permissions=True)

    def create_or_update_attendance(
        self, employee_details, in_time=None, out_time=None
    ):
        """
        Create or update Attendance record from an approved regularization.

        - If an existing Attendance record is found (draft or submitted),
          update its in_time, out_time, working_hours, status, and
          attendance_regularization using db_set (works even on submitted docs).
        - If no record exists, create a new submitted Attendance.
        """

        existing_attendance = frappe.db.get_value(
            "Attendance",
            {
                "employee": self.employee,
                "attendance_date": self.date,
            },
            ["name", "docstatus"],
            as_dict=True,
        )

        working_hours = 0.0

        if in_time and out_time:
            diff = out_time - in_time
            working_hours = round(
                diff.total_seconds() / 3600, 2
            )

        # Use the attendance_status already set on the regularization record
        # (calculated in before_save / validate from in_time & out_time).
        # Fall back to dynamic calculation only if not explicitly set.
        if self.attendance_status:
            status = self.attendance_status
        else:
            leave_status = get_leave_status(self.employee, self.date)
            holiday_flag = is_holiday(self.employee, self.date)
            status = determine_attendance_status(
                working_hours,
                leave_status,
                holiday_flag,
            )

        if existing_attendance:
            # Capture old values BEFORE updating (for activity history comment)
            old = frappe.db.get_value(
                "Attendance",
                existing_attendance.name,
                ["status", "in_time", "out_time", "working_hours"],
                as_dict=True,
            ) or {}

            # Use db_set so it works even on submitted (docstatus=1) records
            frappe.db.set_value(
                "Attendance",
                existing_attendance.name,
                {
                    "status": status,
                    "in_time": in_time,
                    "out_time": out_time,
                    "working_hours": working_hours,
                    "attendance_regularization": self.name,
                },
                update_modified=True,
            )

            # --- Add Activity comment showing before → after ---
            def fmt_time(val):
                if not val:
                    return "—"
                if hasattr(val, "strftime"):
                    return val.strftime("%H:%M:%S")
                return str(val)

            def fmt_status(val):
                return val or "—"

            changes = []
            if fmt_status(old.get("status")) != fmt_status(status):
                changes.append(
                    f"<b>Status:</b> {fmt_status(old.get('status'))} → <b>{fmt_status(status)}</b>"
                )
            if fmt_time(old.get("in_time")) != fmt_time(in_time):
                changes.append(
                    f"<b>In Time:</b> {fmt_time(old.get('in_time'))} → <b>{fmt_time(in_time)}</b>"
                )
            if fmt_time(old.get("out_time")) != fmt_time(out_time):
                changes.append(
                    f"<b>Out Time:</b> {fmt_time(old.get('out_time'))} → <b>{fmt_time(out_time)}</b>"
                )
            old_wh = round(float(old.get("working_hours") or 0), 2)
            if old_wh != working_hours:
                changes.append(
                    f"<b>Working Hours:</b> {old_wh} → <b>{working_hours}</b>"
                )

            if changes:
                comment_text = (
                    f"Updated via Attendance Regularization "
                    f"<a href='/app/attendance-regularization/{self.name}'>{self.name}</a>:<br>"
                    + "<br>".join(changes)
                )
                att_doc = frappe.get_doc("Attendance", existing_attendance.name)
                att_doc.add_comment("Info", text=comment_text)

        else:
            # No attendance record for this date — create a new submitted one
            from at_biometric_integration.utils.helpers import get_employee_shift
            shift_doc = get_employee_shift(self.employee, self.date)
            shift_name = shift_doc.name if shift_doc else employee_details.default_shift

            att = frappe.get_doc({
                "doctype": "Attendance",
                "employee": self.employee,
                "employee_name": self.employee_name,
                "attendance_date": self.date,
                "status": status,
                "company": employee_details.company,
                "shift": shift_name,
                "in_time": in_time,
                "out_time": out_time,
                "working_hours": working_hours,
                "attendance_regularization": self.name,
            })
            att.flags.ignore_permissions = True
            att.insert()
            att.submit()

    def on_cancel(self):
        """
        On cancellation:
        - Delete matching Employee Checkin records.
        - Cancel and delete matching Attendance records.
        - Set workflow_state to Canceled.
        """

        if self.workflow_state != "Canceled":
            self.workflow_state = "Canceled"
            self.db_set(
                "workflow_state",
                "Canceled",
                update_modified=False,
            )

        checkin_times = []

        if self.in_time:
            in_dt = (
                datetime.combine(self.date, self.in_time)
                if isinstance(self.in_time, time)
                else self.in_time
            )
            checkin_times.append(in_dt)

        if self.out_time:
            out_dt = (
                datetime.combine(self.date, self.out_time)
                if isinstance(self.out_time, time)
                else self.out_time
            )
            checkin_times.append(out_dt)

        if not checkin_times:
            frappe.logger().info(
                "[Attendance Regularization] "
                f"No check-in/out times found for {self.name}"
            )
            return

        checkins_to_delete = frappe.get_all(
            "Employee Checkin",
            filters={
                "employee": self.employee,
                "time": ["in", checkin_times],
            },
            pluck="name",
        )

        for checkin_name in checkins_to_delete:
            try:
                frappe.delete_doc(
                    "Employee Checkin",
                    checkin_name,
                    ignore_permissions=True,
                )

                frappe.logger().info(
                    "[Attendance Regularization] "
                    f"Deleted Employee Checkin: {checkin_name}"
                )

            except Exception:
                frappe.log_error(
                    title="Attendance Regularization Cancellation Error",
                    message=(
                        f"Error deleting Employee Checkin "
                        f"{checkin_name}:\n"
                        f"{frappe.get_traceback()}"
                    ),
                )

        attendance_records = frappe.get_all(
            "Attendance",
            filters={
                "employee": self.employee,
                "attendance_date": self.date,
            },
            pluck="name",
        )

        for attendance_name in attendance_records:
            try:
                attendance_doc = frappe.get_doc(
                    "Attendance", attendance_name
                )

                check_in = getattr(
                    attendance_doc, "check_in", None
                )
                check_out = getattr(
                    attendance_doc, "check_out", None
                )

                if (
                    check_in in checkin_times
                    or check_out in checkin_times
                ):
                    if attendance_doc.docstatus == 1:
                        attendance_doc.cancel()

                        frappe.logger().info(
                            "[Attendance Regularization] "
                            f"Canceled Attendance: {attendance_name}"
                        )

                    frappe.delete_doc(
                        "Attendance",
                        attendance_name,
                        ignore_permissions=True,
                    )

                    frappe.logger().info(
                        "[Attendance Regularization] "
                        f"Deleted Attendance: {attendance_name}"
                    )

            except Exception:
                frappe.log_error(
                    title="Attendance Regularization Cancellation Error",
                    message=(
                        f"Error processing Attendance "
                        f"{attendance_name}:\n"
                        f"{frappe.get_traceback()}"
                    ),
                )

        frappe.msgprint(
            "Related Employee Checkin and Attendance "
            "records deleted successfully."
        )
