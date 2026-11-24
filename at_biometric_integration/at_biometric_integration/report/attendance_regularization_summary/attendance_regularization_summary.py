# import frappe
# from frappe import _
# from frappe.utils import getdate, add_days, nowdate, now_datetime, get_time
# from datetime import datetime, timedelta



# def execute(filters=None):
#     filters = frappe._dict(filters or {})
#     validate_filters(filters)

#     columns = get_columns()
#     data = get_report_data(filters)

#     # Show all report columns even when no records are available.
#     # This is only a display placeholder, not an actual database record.
#     if not data:
#         data = [{
#             "employee": "",
#             "employee_name": _("No records found for selected filters"),
#             "attendance_date": None,
#             "shift_start": "",
#             "shift_end": "",
#             "in_time": "",
#             "out_time": "",
#             "working_hours": "",
#             "status": "",
#             "missed_punch": "",
#             "regularization_count": 0,
#             "eligible": "",
#             "action": "",
#             "remarks": "",
#         }]

#     message = get_employee_regularization_message(filters)

#     return columns, data, message


# def get_employee_regularization_message(filters):
#     employee = filters.get("employee")

#     if not employee:
#         return None

#     from_date = filters.get("from_date")
#     to_date = filters.get("to_date")

#     settings = get_settings()
#     state_config = get_workflow_state_config(settings)
#     counts = get_total_regularizations([employee], from_date, to_date, state_config)

#     total = counts.get(employee, 0)

#     employee_name = frappe.db.get_value(
#         "Employee", employee, "employee_name"
#     ) or employee

#     if from_date and to_date:
#         employee_name = f"{employee_name} ({from_date} to {to_date})"

#     return _("Total Attendance Regularization requests for {0}: {1}").format(
#         frappe.utils.escape_html(employee_name),
#         total,
#     )


# def validate_filters(filters):
#     if filters.get("from_date") and filters.get("to_date"):
#         if getdate(filters.from_date) > getdate(filters.to_date):
#             frappe.throw(_("From Date cannot be after To Date."))


# def get_columns():
#     return [
#         {
#             "label": _("Employee"),
#             "fieldname": "employee",
#             "fieldtype": "Link",
#             "options": "Employee",
#             "width": 120,
#         },
#         {
#             "label": _("Employee Name"),
#             "fieldname": "employee_name",
#             "fieldtype": "Data",
#             "width": 160,
#         },
#         {
#             "label": _("Attendance Date"),
#             "fieldname": "attendance_date",
#             "fieldtype": "Date",
#             "width": 110,
#         },
#         {
#             "label": _("Shift Start"),
#             "fieldname": "shift_start",
#             "fieldtype": "Data",
#             "width": 90,
#         },
#         {
#             "label": _("Shift End"),
#             "fieldname": "shift_end",
#             "fieldtype": "Data",
#             "width": 90,
#         },
#         {
#             "label": _("In Time"),
#             "fieldname": "in_time",
#             "fieldtype": "Data",
#             "width": 85,
#         },
#         {
#             "label": _("Out Time"),
#             "fieldname": "out_time",
#             "fieldtype": "Data",
#             "width": 85,
#         },
#         {
#             "label": _("Working Hours (HH:MM)"),
#             "fieldname": "working_hours",
#             "fieldtype": "Data",
#             "width": 120,
#         },
#         {
#             "label": _("Status"),
#             "fieldname": "status",
#             "fieldtype": "Data",
#             "width": 100,
#         },
#         {
#             "label": _("Missed Punch"),
#             "fieldname": "missed_punch",
#             "fieldtype": "Data",
#             "width": 100,
#         },
#         {
#             "label": _("Regularization Count (Month)"),
#             "fieldname": "regularization_count",
#             "fieldtype": "Int",
#             "width": 145,
#         },
#         {
#             "label": _("Regularization Eligible"),
#             "fieldname": "eligible",
#             "fieldtype": "Data",
#             "width": 125,
#         },
#         {
#             "label": _("Action"),
#             "fieldname": "action",
#             "fieldtype": "Data",
#             "width": 180,
#         },
#         {
#             "label": _("Remarks"),
#             "fieldname": "remarks",
#             "fieldtype": "Data",
#             "width": 230,
#         },
#     ]


# def get_report_data(filters):
#     from_date = getdate(filters.get("from_date") or nowdate())
#     to_date = getdate(filters.get("to_date") or nowdate())

#     employees = get_employees(filters)

#     if not employees:
#         return []

#     employee_names = [employee.name for employee in employees]

#     dates = []
#     current_date = from_date

#     while current_date <= to_date:
#         dates.append(current_date)
#         current_date = add_days(current_date, 1)

#     attendance_map = get_attendance_map(
#         employee_names, from_date, to_date
#     )

#     assignments = get_shift_assignments(employee_names, to_date)

#     leave_map = get_leave_map(
#         employee_names, from_date, to_date
#     )

#     request_map = get_attendance_request_map(
#         employee_names, from_date, to_date
#     )

#     month_start = from_date.replace(day=1)
#     month_end = add_months(to_date.replace(day=1), 1)
#     month_end = add_days(month_end, -1)

#     settings = get_settings()
#     state_config = get_workflow_state_config(settings)

#     regularizations = get_regularizations(
#         employee_names, month_start, month_end, state_config
#     )

#     holiday_cache = {}

#     rows = []

#     for employee in employees:
#         employee_assignments = assignments.get(employee.name, [])

#         for attendance_date in dates:
#             key = (employee.name, attendance_date)

#             attendance = attendance_map.get(key)

#             assignment = get_assignment_for_date(
#                 employee_assignments, attendance_date
#             )

#             shift_name = (
#                 assignment.shift_type if assignment
#                 else employee.default_shift
#             )

#             shift = get_shift_details(shift_name)

#             shift_start_dt, shift_end_dt = get_shift_datetimes(
#                 attendance_date, shift
#             )

#             # Attendance DocType is the source for In Time and Out Time.
#             in_datetime = attendance.in_time if attendance else None
#             out_datetime = attendance.out_time if attendance else None

#             in_datetime = (
#                 frappe.utils.get_datetime(in_datetime)
#                 if in_datetime else None
#             )

#             out_datetime = (
#                 frappe.utils.get_datetime(out_datetime)
#                 if out_datetime else None
#             )

#             in_time = (
#                 in_datetime.strftime("%H:%M")
#                 if in_datetime else "-"
#             )

#             out_time = (
#                 out_datetime.strftime("%H:%M")
#                 if out_datetime else "-"
#             )

#             working_hours = calculate_working_hours(
#                 in_datetime, out_datetime
#             )

#             leave_info = leave_map.get(key, {})
#             request_info = request_map.get(key, {})

#             holiday_info = get_holiday_info(
#                 employee,
#                 shift_name,
#                 attendance_date,
#                 holiday_cache,
#             )

#             is_full_leave = leave_info.get("full_day", False)
#             is_half_leave = leave_info.get("half_day", False)
#             is_half_request = request_info.get("half_day", False)

#             is_holiday = bool(
#                 holiday_info and not holiday_info.get("weekly_off")
#             )

#             is_weekly_off = bool(
#                 holiday_info and holiday_info.get("weekly_off")
#             )

#             if attendance:
#                 status = attendance.status
#             elif is_weekly_off:
#                 status = "Week Off"
#             elif holiday_info:
#                 status = "Holiday"
#             else:
#                 status = "Not Marked"

#             if (
#                 is_full_leave
#                 or status == "On Leave"
#                 or is_holiday
#                 or is_weekly_off
#             ):
#                 missed_punch = "NA"

#             elif in_datetime and not out_datetime:
#                 missed_punch = "OUT"

#             elif out_datetime and not in_datetime:
#                 missed_punch = "IN"

#             elif not in_datetime and not out_datetime:
#                 missed_punch = "BOTH"

#             else:
#                 missed_punch = "-"

#             month_key = (
#                 employee.name,
#                 attendance_date.year,
#                 attendance_date.month,
#             )

#             month_count = regularizations.get(month_key, 0)

#             existing_request = get_existing_request(
#                 employee.name, attendance_date, state_config
#             )

#             eligible, remarks = get_eligibility(
#                 attendance_date=attendance_date,
#                 status=status,
#                 missed_punch=missed_punch,
#                 shift_end=shift_end_dt,
#                 settings=settings,
#                 state_config=state_config,
#                 month_count=month_count,
#                 existing_request=existing_request,
#                 is_full_leave=is_full_leave,
#                 is_holiday=is_holiday,
#                 is_weekly_off=is_weekly_off,
#                 is_half_leave=is_half_leave,
#                 is_half_request=is_half_request,
#             )

#             row = {
#                 "employee": employee.name,
#                 "employee_name": employee.employee_name,
#                 "attendance_date": attendance_date,
#                 "shift_start": (
#                     str(shift.start_time)[:5] if shift else "-"
#                 ),
#                 "shift_end": (
#                     str(shift.end_time)[:5] if shift else "-"
#                 ),
#                 "in_time": in_time,
#                 "out_time": out_time,
#                 "working_hours": working_hours,
#                 "status": status,
#                 "missed_punch": missed_punch,
#                 "regularization_count": month_count,
#                 "eligible": eligible,
#                 "action": "",
#                 "remarks": remarks,
#             }

#             if existing_request:
#                 row["action"] = (
#                     existing_request.workflow_state or "Existing Request"
#                 )
#                 row["regularization_name"] = existing_request.name

#             elif eligible == "Yes":
#                 row["action"] = "Create Regularization"

#             if matches_filters(row, filters):
#                 rows.append(row)

#     rows.sort(
#         key=lambda row: (
#             row["attendance_date"],
#             status_priority(row["status"]),
#             row["employee_name"] or "",
#         )
#     )

#     return rows


# def add_months(date_value, months):
#     month_index = date_value.month - 1 + months
#     year = date_value.year + month_index // 12
#     month = month_index % 12 + 1

#     return date_value.replace(
#         year=year,
#         month=month,
#         day=1,
#     )


# def get_employees(filters):
#     conditions = {"status": "Active"}

#     if filters.get("company"):
#         conditions["company"] = filters.company

#     if filters.get("department"):
#         conditions["department"] = filters.department

#     if filters.get("employee"):
#         conditions["name"] = filters.employee

#     if filters.get("employee_type"):
#         conditions["employment_type"] = filters.employee_type

#     employees = frappe.get_all(
#         "Employee",
#         filters=conditions,
#         fields=[
#             "name",
#             "employee_name",
#             "company",
#             "department",
#             "employment_type",
#             "user_id",
#             "reports_to",
#             "holiday_list",
#             "default_shift",
#         ],
#         order_by="employee_name asc",
#     )

#     return apply_user_restrictions(employees)


# def apply_user_restrictions(employees):
#     user = frappe.session.user
#     roles = set(frappe.get_roles(user))

#     if roles.intersection({
#         "System Manager",
#         "HR Manager",
#         "HR User",
#     }):
#         return employees

#     own_employee = frappe.db.get_value(
#         "Employee",
#         {"user_id": user},
#         "name",
#     )

#     if "Projects Manager" in roles and own_employee:
#         return [
#             employee
#             for employee in employees
#             if (
#                 employee.name == own_employee
#                 or employee.reports_to == own_employee
#             )
#         ]

#     if own_employee:
#         return [
#             employee
#             for employee in employees
#             if employee.name == own_employee
#         ]

#     return []


# def get_attendance_map(employee_names, from_date, to_date):
#     records = frappe.get_all(
#         "Attendance",
#         filters={
#             "employee": ["in", employee_names],
#             "attendance_date": ["between", [from_date, to_date]],
#             "docstatus": ["!=", 2],
#         },
#         fields=[
#             "name",
#             "employee",
#             "attendance_date",
#             "status",
#             "in_time",
#             "out_time",
#             "working_hours",
#         ],
#     )

#     return {
#         (
#             record.employee,
#             getdate(record.attendance_date),
#         ): record
#         for record in records
#     }


# def get_shift_assignments(employee_names, to_date):
#     records = frappe.get_all(
#         "Shift Assignment",
#         filters={
#             "employee": ["in", employee_names],
#             "status": "Active",
#             "start_date": ["<=", to_date],
#         },
#         fields=[
#             "employee",
#             "shift_type",
#             "start_date",
#             "end_date",
#         ],
#         order_by="start_date desc",
#     )

#     result = {}

#     for record in records:
#         result.setdefault(record.employee, []).append(record)

#     return result


# def get_assignment_for_date(assignments, attendance_date):
#     for assignment in assignments:
#         if getdate(assignment.start_date) > attendance_date:
#             continue

#         if (
#             assignment.end_date
#             and getdate(assignment.end_date) < attendance_date
#         ):
#             continue

#         return assignment

#     return None


# def get_shift_details(shift_name):
#     if not shift_name:
#         return None

#     return frappe.get_cached_doc("Shift Type", shift_name)


# def get_shift_datetimes(attendance_date, shift):
#     if not shift or not shift.start_time or not shift.end_time:
#         start = datetime.combine(
#             attendance_date,
#             datetime.min.time(),
#         )

#         end = datetime.combine(
#             attendance_date,
#             datetime.max.time(),
#         )

#         return start, end

#     start_time = get_time(shift.start_time)
#     end_time = get_time(shift.end_time)

#     start = datetime.combine(attendance_date, start_time)
#     end = datetime.combine(attendance_date, end_time)

#     if end_time <= start_time:
#         end += timedelta(days=1)

#     return start, end


# def calculate_working_hours(in_datetime, out_datetime):
#     if not in_datetime and not out_datetime:
#         return "-"

#     if not in_datetime or not out_datetime:
#         return "00:00"

#     seconds = int(
#         (out_datetime - in_datetime).total_seconds()
#     )

#     if seconds < 0:
#         return "00:00"

#     hours, remainder = divmod(seconds, 3600)
#     minutes = remainder // 60

#     return f"{hours:02d}:{minutes:02d}"


# def get_leave_map(employee_names, from_date, to_date):
#     records = frappe.get_all(
#         "Leave Application",
#         filters={
#             "employee": ["in", employee_names],
#             "status": "Approved",
#             "docstatus": 1,
#             "from_date": ["<=", to_date],
#             "to_date": [">=", from_date],
#         },
#         fields=[
#             "employee",
#             "from_date",
#             "to_date",
#             "half_day",
#             "half_day_date",
#         ],
#     )

#     result = {}

#     for record in records:
#         current = max(getdate(record.from_date), from_date)
#         last = min(getdate(record.to_date), to_date)

#         while current <= last:
#             is_half_day = (
#                 record.half_day
#                 and record.half_day_date
#                 and current == getdate(record.half_day_date)
#             )

#             result[(record.employee, current)] = {
#                 "half_day": bool(is_half_day),
#                 "full_day": not bool(is_half_day),
#             }

#             current = add_days(current, 1)

#     return result


# def get_attendance_request_map(employee_names, from_date, to_date):
#     records = frappe.get_all(
#         "Attendance Request",
#         filters={
#             "employee": ["in", employee_names],
#             "docstatus": 1,
#             "from_date": ["<=", to_date],
#             "to_date": [">=", from_date],
#         },
#         fields=[
#             "employee",
#             "from_date",
#             "to_date",
#             "half_day",
#             "half_day_date",
#             "reason",
#         ],
#     )

#     result = {}

#     for record in records:
#         current = max(getdate(record.from_date), from_date)
#         last = min(getdate(record.to_date), to_date)

#         while current <= last:
#             is_half_day = (
#                 record.half_day
#                 and record.half_day_date
#                 and current == getdate(record.half_day_date)
#             )

#             result[(record.employee, current)] = {
#                 "half_day": bool(is_half_day),
#                 "wfh": record.reason == "Work From Home",
#             }

#             current = add_days(current, 1)

#     return result


# def get_holiday_info(employee, shift_name, attendance_date, cache):
#     holiday_list = employee.holiday_list

#     if not holiday_list and shift_name:
#         holiday_list = frappe.db.get_value(
#             "Shift Type",
#             shift_name,
#             "holiday_list",
#         )

#     if not holiday_list:
#         return None

#     cache_key = (holiday_list, attendance_date)

#     if cache_key in cache:
#         return cache[cache_key]

#     holiday_list_doc = frappe.get_cached_doc(
#         "Holiday List",
#         holiday_list,
#     )

#     weekday = attendance_date.strftime("%A")

#     # Saturday and Sunday are both treated as weekly off when the
#     # holiday list is configured with a weekend weekly off day.
#     if holiday_list_doc.weekly_off in ("Saturday", "Sunday"):
#         weekly_off_day = weekday in ("Saturday", "Sunday")
#     else:
#         weekly_off_day = (
#             holiday_list_doc.weekly_off == weekday
#             if holiday_list_doc.weekly_off
#             else False
#         )

#     holiday = frappe.db.get_value(
#         "Holiday",
#         {
#             "parent": holiday_list,
#             "parenttype": "Holiday List",
#             "holiday_date": attendance_date,
#         },
#         ["weekly_off", "is_half_day"],
#         as_dict=True,
#     )

#     if holiday:
#         info = {
#             "weekly_off": (
#                 bool(holiday.weekly_off) or weekly_off_day
#             ),
#             "is_half_day": bool(holiday.is_half_day),
#         }

#     elif weekly_off_day:
#         info = {
#             "weekly_off": True,
#             "is_half_day": False,
#         }

#     else:
#         info = None

#     cache[cache_key] = info

#     return info


# def get_workflow_state_config(settings):
#     """Read workflow-state behaviour from the Attendance Settings child table.

#     Attendance Settings child table field: regularization_workflow_states
#     Child fields: workflow_state, counts_for_monthly_limit,
#                   blocks_new_request, is_approved
#     """
#     rows = settings.get("regularization_workflow_states") or []
#     config = {}

#     for row in rows:
#         state = row.get("workflow_state")
#         if not state:
#             continue

#         config[state] = frappe._dict(
#             counts_for_monthly_limit=bool(row.get("counts_for_monthly_limit")),
#             blocks_new_request=bool(row.get("blocks_new_request")),
#             is_approved=bool(row.get("is_approved")),
#         )

#     return config


# def get_regularizations(employee_names, from_date, to_date, state_config):
#     records = frappe.get_all(
#         "Attendance Regularization",
#         filters={
#             "employee": ["in", employee_names],
#             "date": ["between", [from_date, to_date]],
#         },
#         fields=["employee", "date", "workflow_state"],
#     )

#     counts = {}
#     for record in records:
#         state_rule = state_config.get(record.workflow_state)
#         if not state_rule or not state_rule.counts_for_monthly_limit:
#             continue

#         date_value = getdate(record.date)
#         key = (record.employee, date_value.year, date_value.month)
#         counts[key] = counts.get(key, 0) + 1

#     return counts


# def get_total_regularizations(
#     employee_names, from_date=None, to_date=None, state_config=None
# ):
#     conditions = {"employee": ["in", employee_names]}

#     if from_date and to_date:
#         conditions["date"] = ["between", [getdate(from_date), getdate(to_date)]]

#     records = frappe.get_all(
#         "Attendance Regularization",
#         filters=conditions,
#         fields=["employee", "workflow_state"],
#     )

#     state_config = state_config or {}
#     counts = {}
#     for record in records:
#         state_rule = state_config.get(record.workflow_state)
#         if not state_rule or not state_rule.counts_for_monthly_limit:
#             continue
#         counts[record.employee] = counts.get(record.employee, 0) + 1

#     return counts


# def get_existing_request(employee, attendance_date, state_config):
#     records = frappe.get_all(
#         "Attendance Regularization",
#         filters={"employee": employee, "date": attendance_date},
#         fields=["name", "workflow_state", "creation"],
#         order_by="creation desc",
#         limit=10,
#     )

#     for record in records:
#         state_rule = state_config.get(record.workflow_state)

#         # Unknown/unconfigured states are treated conservatively as existing
#         # requests, so the report does not allow duplicate requests by mistake.
#         if not state_rule:
#             return record

#         if state_rule.blocks_new_request or state_rule.is_approved:
#             return record

#     return None


# def get_settings():
#     if not frappe.db.exists("DocType", "Attendance Settings"):
#         frappe.throw(_("Attendance Settings DocType was not found."))

#     return frappe._dict(frappe.get_single("Attendance Settings").as_dict())


# def get_eligibility(
#     attendance_date,
#     status,
#     missed_punch,
#     shift_end,
#     settings,
#     state_config,
#     month_count,
#     existing_request,
#     is_full_leave,
#     is_holiday,
#     is_weekly_off,
#     is_half_leave,
#     is_half_request,
# ):
#     if not settings.get("enable_regularization"):
#         return "No", "Regularization is disabled in Attendance Settings"

#     if is_full_leave or status == "On Leave" or is_holiday or is_weekly_off:
#         return "No", ""

#     if existing_request:
#         state_rule = state_config.get(existing_request.workflow_state)
#         if state_rule and state_rule.is_approved:
#             return "No", "Already regularized"
#         if state_rule and state_rule.blocks_new_request:
#             return "No", "Regularization pending approval"

#     if missed_punch not in {"IN", "OUT", "BOTH"} and status != "Absent":
#         return "No", ""

#     # From Hours and To Hours are interpreted as the allowed elapsed-time
#     # window after the employee's scheduled shift end.
#     from_hours = settings.get("regularization_from_hours")
#     to_hours = settings.get("regularization_to_hours")
#     monthly_limit = settings.get("max_requests_per_month")

#     if from_hours is None or to_hours is None or monthly_limit is None:
#         return "No", "Please configure From Hours, To Hours and Monthly Limit in Attendance Settings"

#     from_hours = float(from_hours)
#     to_hours = float(to_hours)
#     monthly_limit = int(monthly_limit)

#     if from_hours < 0 or to_hours < from_hours:
#         return "No", "Invalid regularization hour range in Attendance Settings"

#     if shift_end:
#         elapsed_hours = (now_datetime() - shift_end).total_seconds() / 3600

#         if elapsed_hours < from_hours:
#             remaining = round(from_hours - elapsed_hours, 2)
#             return "No", f"Regularization will be available after {remaining} more hour(s)"

#         if elapsed_hours > to_hours:
#             return "No", "Regularization time window has expired"

#     # A monthly limit of 0 means unlimited requests.
#     if monthly_limit > 0 and month_count >= monthly_limit:
#         return "No", "Monthly regularization limit reached"

#     return "Yes", ""


# def matches_filters(row, filters):
#     if (
#         filters.get("status")
#         and row["status"] != filters.status
#     ):
#         return False

#     if (
#         filters.get("missed_punch")
#         and row["missed_punch"] != filters.missed_punch
#     ):
#         return False

#     if (
#         filters.get("eligibility")
#         and row["eligible"] != filters.eligibility
#     ):
#         return False

#     return True


# def status_priority(status):
#     priority = {
#         "Absent": 1,
#         "Not Marked": 2,
#         "Week Off": 3,
#         "Holiday": 4,
#         "Half Day": 5,
#         "Present": 6,
#         "Work From Home": 7,
#         "On Leave": 8,
#     }

#     return priority.get(status, 8)






import frappe
from frappe import _
from frappe.utils import getdate, add_days, nowdate, now_datetime, get_time
from datetime import datetime, timedelta


# Only these four workflow states count towards the monthly limit.
COUNTABLE_REGULARIZATION_STATES = [
    "Pending Manager Approval",
    "Manager Approved",
    "Pending For HR Approval",
    "Approved By HR",
]


def execute(filters=None):
    filters = frappe._dict(filters or {})
    validate_filters(filters)

    columns = get_columns()
    data = get_report_data(filters)

    # Display all columns even when no records are available.
    if not data:
        data = [{
            "employee": "",
            "employee_name": _("No records found for selected filters"),
            "attendance_date": None,
            "shift_start": "",
            "shift_end": "",
            "in_time": "",
            "out_time": "",
            "working_hours": "",
            "status": "",
            "missed_punch": "",
            "regularization_count": 0,
            "eligible": "",
            "action": "",
            "remarks": "",
        }]

    message = get_employee_regularization_message(filters)

    return columns, data, message


def get_employee_regularization_message(filters):
    employee = filters.get("employee")

    if not employee:
        return None

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    counts = get_total_regularizations(
        [employee],
        from_date,
        to_date,
    )

    total = counts.get(employee, 0)

    employee_name = frappe.db.get_value(
        "Employee", employee, "employee_name"
    ) or employee

    if from_date and to_date:
        employee_name = f"{employee_name} ({from_date} to {to_date})"

    return _("Total Attendance Regularization requests for {0}: {1}").format(
        frappe.utils.escape_html(employee_name),
        total,
    )


def validate_filters(filters):
    if filters.get("from_date") and filters.get("to_date"):
        if getdate(filters.from_date) > getdate(filters.to_date):
            frappe.throw(_("From Date cannot be after To Date."))


def get_columns():
    return [
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Attendance Date"),
            "fieldname": "attendance_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": _("Shift Start"),
            "fieldname": "shift_start",
            "fieldtype": "Data",
            "width": 90,
        },
        {
            "label": _("Shift End"),
            "fieldname": "shift_end",
            "fieldtype": "Data",
            "width": 90,
        },
        {
            "label": _("In Time"),
            "fieldname": "in_time",
            "fieldtype": "Data",
            "width": 85,
        },
        {
            "label": _("Out Time"),
            "fieldname": "out_time",
            "fieldtype": "Data",
            "width": 85,
        },
        {
            "label": _("Working Hours (HH:MM)"),
            "fieldname": "working_hours",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Missed Punch"),
            "fieldname": "missed_punch",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Regularization Count (Month)"),
            "fieldname": "regularization_count",
            "fieldtype": "Int",
            "width": 145,
        },
        {
            "label": _("Regularization Eligible"),
            "fieldname": "eligible",
            "fieldtype": "Data",
            "width": 125,
        },
        {
            "label": _("Action"),
            "fieldname": "action",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Remarks"),
            "fieldname": "remarks",
            "fieldtype": "Data",
            "width": 230,
        },
    ]


def get_report_data(filters):
    from_date = getdate(filters.get("from_date") or nowdate())
    to_date = getdate(filters.get("to_date") or nowdate())

    employees = get_employees(filters)

    if not employees:
        return []

    employee_names = [employee.name for employee in employees]

    dates = []
    current_date = from_date

    while current_date <= to_date:
        dates.append(current_date)
        current_date = add_days(current_date, 1)

    attendance_map = get_attendance_map(
        employee_names, from_date, to_date
    )

    assignments = get_shift_assignments(
        employee_names, to_date
    )

    leave_map = get_leave_map(
        employee_names, from_date, to_date
    )

    request_map = get_attendance_request_map(
        employee_names, from_date, to_date
    )

    month_start = from_date.replace(day=1)
    month_end = add_months(to_date.replace(day=1), 1)
    month_end = add_days(month_end, -1)

    settings = get_settings()

    # Monthly count uses the four selected workflow states.
    regularizations = get_regularizations(
        employee_names,
        month_start,
        month_end,
    )

    # Workflow configuration is maintained in code.
    # No Attendance Settings child table dependency.
    state_config = get_workflow_state_config()

    holiday_cache = {}
    rows = []

    for employee in employees:
        employee_assignments = assignments.get(employee.name, [])

        for attendance_date in dates:
            key = (employee.name, attendance_date)

            attendance = attendance_map.get(key)

            assignment = get_assignment_for_date(
                employee_assignments,
                attendance_date,
            )

            shift_name = (
                assignment.shift_type if assignment
                else employee.default_shift
            )

            shift = get_shift_details(shift_name)

            shift_start_dt, shift_end_dt = get_shift_datetimes(
                attendance_date,
                shift,
            )

            # Attendance DocType is the source for In Time and Out Time.
            in_datetime = attendance.in_time if attendance else None
            out_datetime = attendance.out_time if attendance else None

            in_datetime = (
                frappe.utils.get_datetime(in_datetime)
                if in_datetime else None
            )

            out_datetime = (
                frappe.utils.get_datetime(out_datetime)
                if out_datetime else None
            )

            in_time = (
                in_datetime.strftime("%H:%M")
                if in_datetime else "-"
            )

            out_time = (
                out_datetime.strftime("%H:%M")
                if out_datetime else "-"
            )

            working_hours = calculate_working_hours(
                in_datetime,
                out_datetime,
            )

            leave_info = leave_map.get(key, {})
            request_info = request_map.get(key, {})

            holiday_info = get_holiday_info(
                employee,
                shift_name,
                attendance_date,
                holiday_cache,
            )

            is_full_leave = leave_info.get("full_day", False)
            is_half_leave = leave_info.get("half_day", False)
            is_half_request = request_info.get("half_day", False)

            is_holiday = bool(
                holiday_info and not holiday_info.get("weekly_off")
            )

            is_weekly_off = bool(
                holiday_info and holiday_info.get("weekly_off")
            )

            # Attendance status is taken directly from Attendance.
            if attendance:
                status = attendance.status
            elif is_weekly_off:
                status = "Week Off"
            elif holiday_info:
                status = "Holiday"
            else:
                status = "Not Marked"

            # Missed Punch calculation.
            if (
                is_full_leave
                or status == "On Leave"
                or is_holiday
                or is_weekly_off
            ):
                missed_punch = "NA"

            elif in_datetime and not out_datetime:
                missed_punch = "OUT"

            elif out_datetime and not in_datetime:
                missed_punch = "IN"

            elif not in_datetime and not out_datetime:
                missed_punch = "BOTH"

            else:
                missed_punch = "-"

            month_key = (
                employee.name,
                attendance_date.year,
                attendance_date.month,
            )

            month_count = regularizations.get(month_key, 0)

            existing_request = get_existing_request(
                employee.name,
                attendance_date,
                state_config,
            )

            eligible, remarks = get_eligibility(
                attendance_date=attendance_date,
                status=status,
                missed_punch=missed_punch,
                shift_end=shift_end_dt,
                settings=settings,
                state_config=state_config,
                month_count=month_count,
                existing_request=existing_request,
                is_full_leave=is_full_leave,
                is_holiday=is_holiday,
                is_weekly_off=is_weekly_off,
                is_half_leave=is_half_leave,
                is_half_request=is_half_request,
            )

            row = {
                "employee": employee.name,
                "employee_name": employee.employee_name,
                "attendance_date": attendance_date,
                "shift_start": (
                    str(shift.start_time)[:5] if shift else "-"
                ),
                "shift_end": (
                    str(shift.end_time)[:5] if shift else "-"
                ),
                "in_time": in_time,
                "out_time": out_time,
                "working_hours": working_hours,
                "status": status,
                "missed_punch": missed_punch,
                "regularization_count": month_count,
                "eligible": eligible,
                "action": "",
                "remarks": remarks,
            }

            if existing_request:
                row["action"] = (
                    existing_request.workflow_state or "Existing Request"
                )
                row["regularization_name"] = existing_request.name

            elif eligible == "Yes":
                row["action"] = "Create Regularization"

            if matches_filters(row, filters):
                rows.append(row)

    rows.sort(
        key=lambda row: (
            row["attendance_date"],
            status_priority(row["status"]),
            row["employee_name"] or "",
        )
    )

    return rows


def add_months(date_value, months):
    month_index = date_value.month - 1 + months
    year = date_value.year + month_index // 12
    month = month_index % 12 + 1

    return date_value.replace(
        year=year,
        month=month,
        day=1,
    )


def get_employees(filters):
    conditions = {"status": "Active"}

    if filters.get("company"):
        conditions["company"] = filters.company

    if filters.get("department"):
        conditions["department"] = filters.department

    if filters.get("employee"):
        conditions["name"] = filters.employee

    if filters.get("employee_type"):
        conditions["employment_type"] = filters.employee_type

    employees = frappe.get_all(
        "Employee",
        filters=conditions,
        fields=[
            "name",
            "employee_name",
            "company",
            "department",
            "employment_type",
            "user_id",
            "reports_to",
            "holiday_list",
            "default_shift",
        ],
        order_by="employee_name asc",
    )

    return apply_user_restrictions(employees)


def apply_user_restrictions(employees):
    user = frappe.session.user
    roles = set(frappe.get_roles(user))

    if roles.intersection({
        "System Manager",
        "HR Manager",
        "HR User",
    }):
        return employees

    own_employee = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        "name",
    )

    if "Projects Manager" in roles and own_employee:
        return [
            employee
            for employee in employees
            if (
                employee.name == own_employee
                or employee.reports_to == own_employee
            )
        ]

    if own_employee:
        return [
            employee
            for employee in employees
            if employee.name == own_employee
        ]

    return []


def get_attendance_map(employee_names, from_date, to_date):
    records = frappe.get_all(
        "Attendance",
        filters={
            "employee": ["in", employee_names],
            "attendance_date": ["between", [from_date, to_date]],
            "docstatus": ["!=", 2],
        },
        fields=[
            "name",
            "employee",
            "attendance_date",
            "status",
            "in_time",
            "out_time",
            "working_hours",
        ],
    )

    return {
        (
            record.employee,
            getdate(record.attendance_date),
        ): record
        for record in records
    }


def get_shift_assignments(employee_names, to_date):
    records = frappe.get_all(
        "Shift Assignment",
        filters={
            "employee": ["in", employee_names],
            "status": "Active",
            "start_date": ["<=", to_date],
        },
        fields=[
            "employee",
            "shift_type",
            "start_date",
            "end_date",
        ],
        order_by="start_date desc",
    )

    result = {}

    for record in records:
        result.setdefault(record.employee, []).append(record)

    return result


def get_assignment_for_date(assignments, attendance_date):
    for assignment in assignments:
        if getdate(assignment.start_date) > attendance_date:
            continue

        if (
            assignment.end_date
            and getdate(assignment.end_date) < attendance_date
        ):
            continue

        return assignment

    return None


def get_shift_details(shift_name):
    if not shift_name:
        return None

    return frappe.get_cached_doc("Shift Type", shift_name)


def get_shift_datetimes(attendance_date, shift):
    if not shift or not shift.start_time or not shift.end_time:
        start = datetime.combine(
            attendance_date,
            datetime.min.time(),
        )

        end = datetime.combine(
            attendance_date,
            datetime.max.time(),
        )

        return start, end

    start_time = get_time(shift.start_time)
    end_time = get_time(shift.end_time)

    start = datetime.combine(attendance_date, start_time)
    end = datetime.combine(attendance_date, end_time)

    if end_time <= start_time:
        end += timedelta(days=1)

    return start, end


def calculate_working_hours(in_datetime, out_datetime):
    if not in_datetime and not out_datetime:
        return "-"

    if not in_datetime or not out_datetime:
        return "00:00"

    seconds = int(
        (out_datetime - in_datetime).total_seconds()
    )

    if seconds < 0:
        return "00:00"

    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60

    return f"{hours:02d}:{minutes:02d}"


def get_leave_map(employee_names, from_date, to_date):
    records = frappe.get_all(
        "Leave Application",
        filters={
            "employee": ["in", employee_names],
            "status": "Approved",
            "docstatus": 1,
            "from_date": ["<=", to_date],
            "to_date": [">=", from_date],
        },
        fields=[
            "employee",
            "from_date",
            "to_date",
            "half_day",
            "half_day_date",
        ],
    )

    result = {}

    for record in records:
        current = max(getdate(record.from_date), from_date)
        last = min(getdate(record.to_date), to_date)

        while current <= last:
            is_half_day = (
                record.half_day
                and record.half_day_date
                and current == getdate(record.half_day_date)
            )

            result[(record.employee, current)] = {
                "half_day": bool(is_half_day),
                "full_day": not bool(is_half_day),
            }

            current = add_days(current, 1)

    return result


def get_attendance_request_map(employee_names, from_date, to_date):
    records = frappe.get_all(
        "Attendance Request",
        filters={
            "employee": ["in", employee_names],
            "docstatus": 1,
            "from_date": ["<=", to_date],
            "to_date": [">=", from_date],
        },
        fields=[
            "employee",
            "from_date",
            "to_date",
            "half_day",
            "half_day_date",
            "reason",
        ],
    )

    result = {}

    for record in records:
        current = max(getdate(record.from_date), from_date)
        last = min(getdate(record.to_date), to_date)

        while current <= last:
            is_half_day = (
                record.half_day
                and record.half_day_date
                and current == getdate(record.half_day_date)
            )

            result[(record.employee, current)] = {
                "half_day": bool(is_half_day),
                "wfh": record.reason == "Work From Home",
            }

            current = add_days(current, 1)

    return result


def get_holiday_info(employee, shift_name, attendance_date, cache):
    holiday_list = employee.holiday_list

    if not holiday_list and shift_name:
        holiday_list = frappe.db.get_value(
            "Shift Type",
            shift_name,
            "holiday_list",
        )

    if not holiday_list:
        return None

    cache_key = (holiday_list, attendance_date)

    if cache_key in cache:
        return cache[cache_key]

    holiday_list_doc = frappe.get_cached_doc(
        "Holiday List",
        holiday_list,
    )

    weekday = attendance_date.strftime("%A")

    if holiday_list_doc.weekly_off in ("Saturday", "Sunday"):
        weekly_off_day = weekday in ("Saturday", "Sunday")
    else:
        weekly_off_day = (
            holiday_list_doc.weekly_off == weekday
            if holiday_list_doc.weekly_off
            else False
        )

    holiday = frappe.db.get_value(
        "Holiday",
        {
            "parent": holiday_list,
            "parenttype": "Holiday List",
            "holiday_date": attendance_date,
        },
        ["weekly_off", "is_half_day"],
        as_dict=True,
    )

    if holiday:
        info = {
            "weekly_off": (
                bool(holiday.weekly_off) or weekly_off_day
            ),
            "is_half_day": bool(holiday.is_half_day),
        }

    elif weekly_off_day:
        info = {
            "weekly_off": True,
            "is_half_day": False,
        }

    else:
        info = None

    cache[cache_key] = info

    return info


def get_workflow_state_config():
    """
    Workflow configuration maintained in code.

    Monthly count:
    Pending Manager Approval
    Manager Approved
    Pending For HR Approval
    Approved By HR

    Pending states block another request.
    Approved By HR is treated as already regularized.
    Rejected and Canceled states do not block a new request.
    """

    return {
        "Draft": frappe._dict(
            counts_for_monthly_limit=False,
            blocks_new_request=True,
            is_approved=False,
        ),
        "Pending Manager Approval": frappe._dict(
            counts_for_monthly_limit=True,
            blocks_new_request=True,
            is_approved=False,
        ),
        "Manager Approved": frappe._dict(
            counts_for_monthly_limit=True,
            blocks_new_request=True,
            is_approved=False,
        ),
        "Pending For HR Approval": frappe._dict(
            counts_for_monthly_limit=True,
            blocks_new_request=True,
            is_approved=False,
        ),
        "Approved By HR": frappe._dict(
            counts_for_monthly_limit=True,
            blocks_new_request=False,
            is_approved=True,
        ),
        "Rejected By Manager": frappe._dict(
            counts_for_monthly_limit=False,
            blocks_new_request=False,
            is_approved=False,
        ),
        "Rejected By HR": frappe._dict(
            counts_for_monthly_limit=False,
            blocks_new_request=False,
            is_approved=False,
        ),
        "Canceled": frappe._dict(
            counts_for_monthly_limit=False,
            blocks_new_request=False,
            is_approved=False,
        ),
    }


def get_regularizations(employee_names, from_date, to_date):
    if not employee_names:
        return {}

    records = frappe.get_all(
        "Attendance Regularization",
        filters={
            "employee": ["in", employee_names],
            "date": ["between", [from_date, to_date]],
            "workflow_state": ["in", COUNTABLE_REGULARIZATION_STATES],
        },
        fields=["employee", "date"],
    )

    counts = {}

    for record in records:
        date_value = getdate(record.date)

        key = (
            record.employee,
            date_value.year,
            date_value.month,
        )

        counts[key] = counts.get(key, 0) + 1

    return counts


def get_total_regularizations(
    employee_names,
    from_date=None,
    to_date=None,
):
    if not employee_names:
        return {}

    conditions = {
        "employee": ["in", employee_names],
        "workflow_state": ["in", COUNTABLE_REGULARIZATION_STATES],
    }

    if from_date and to_date:
        conditions["date"] = [
            "between",
            [getdate(from_date), getdate(to_date)],
        ]

    records = frappe.get_all(
        "Attendance Regularization",
        filters=conditions,
        fields=["employee"],
    )

    counts = {}

    for record in records:
        counts[record.employee] = counts.get(record.employee, 0) + 1

    return counts


def get_existing_request(employee, attendance_date, state_config):
    records = frappe.get_all(
        "Attendance Regularization",
        filters={
            "employee": employee,
            "date": attendance_date,
        },
        fields=[
            "name",
            "workflow_state",
            "creation",
        ],
        order_by="creation desc",
        limit=10,
    )

    for record in records:
        state_rule = state_config.get(record.workflow_state)

        # Unknown states are conservatively treated as existing requests.
        if not state_rule:
            return record

        if (
            state_rule.blocks_new_request
            or state_rule.is_approved
        ):
            return record

    return None


def get_settings():
    if not frappe.db.exists("DocType", "Attendance Settings"):
        frappe.throw(
            _("Attendance Settings DocType was not found.")
        )

    return frappe._dict(
        frappe.get_single("Attendance Settings").as_dict()
    )


def normalize_status(status):
    """
    Normalize status text so these are treated equivalently:
    Absent-Half Day
    Absent - Half Day
    Absent_Half_Day

    Plain Half Day is NOT treated as Absent-Half Day.
    """

    value = str(status or "").strip().lower()
    value = value.replace("-", " ")
    value = value.replace("_", " ")

    return " ".join(value.split())


def is_absent_half_day(status):
    return normalize_status(status) == "absent half day"


def get_eligibility(
    attendance_date,
    status,
    missed_punch,
    shift_end,
    settings,
    state_config,
    month_count,
    existing_request,
    is_full_leave,
    is_holiday,
    is_weekly_off,
    is_half_leave,
    is_half_request,
):
    if not settings.get("enable_regularization"):
        return (
            "No",
            "Regularization is disabled in Attendance Settings",
        )

    if (
        is_full_leave
        or status == "On Leave"
        or is_holiday
        or is_weekly_off
    ):
        return "No", ""

    if existing_request:
        state_rule = state_config.get(
            existing_request.workflow_state
        )

        if state_rule and state_rule.is_approved:
            return "No", "Already regularized"

        if state_rule and state_rule.blocks_new_request:
            return "No", "Regularization pending approval"

    # Allow:
    # 1. Normal missed punch: IN / OUT / BOTH
    # 2. Absent
    # 3. Absent-Half Day
    #
    # Do NOT allow plain Half Day only.
    absent_half_day = is_absent_half_day(status)

    if (
        missed_punch not in {"IN", "OUT", "BOTH"}
        and status != "Absent"
        and not absent_half_day
    ):
        return "No", ""

    # From Hours and To Hours are interpreted as the allowed
    # elapsed-time window after the employee's scheduled shift end.
    from_hours = settings.get("regularization_from_hours")
    to_hours = settings.get("regularization_to_hours")
    monthly_limit = settings.get("max_requests_per_month")

    if (
        from_hours is None
        or to_hours is None
        or monthly_limit is None
    ):
        return (
            "No",
            "Please configure From Hours, To Hours and Monthly Limit in Attendance Settings",
        )

    from_hours = float(from_hours)
    to_hours = float(to_hours)
    monthly_limit = int(monthly_limit)

    if from_hours < 0 or to_hours < from_hours:
        return (
            "No",
            "Invalid regularization hour range in Attendance Settings",
        )

    if shift_end:
        elapsed_hours = (
            now_datetime() - shift_end
        ).total_seconds() / 3600

        if elapsed_hours < from_hours:
            remaining = round(
                from_hours - elapsed_hours,
                2,
            )

            return (
                "No",
                f"Regularization will be available after {remaining} more hour(s)",
            )

        if elapsed_hours > to_hours:
            return (
                "No",
                "Regularization time window has expired",
            )

    # Monthly limit 0 means unlimited.
    if monthly_limit > 0 and month_count >= monthly_limit:
        return "No", "Monthly regularization limit reached"

    return "Yes", ""


def matches_filters(row, filters):
    if (
        filters.get("status")
        and row["status"] != filters.status
    ):
        return False

    if (
        filters.get("missed_punch")
        and row["missed_punch"] != filters.missed_punch
    ):
        return False

    if (
        filters.get("eligibility")
        and row["eligible"] != filters.eligibility
    ):
        return False

    return True


def status_priority(status):
    priority = {
        "Absent": 1,
        "Absent-Half Day": 2,
        "Absent - Half Day": 2,
        "Not Marked": 3,
        "Week Off": 4,
        "Holiday": 5,
        "Half Day": 6,
        "Present": 7,
        "Work From Home": 8,
        "On Leave": 9,
    }

    return priority.get(status, 10)
