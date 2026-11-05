import frappe
from frappe import _
from frappe.utils import getdate, add_days, nowdate, now_datetime, get_time
from datetime import datetime, timedelta


DEFAULT_WAIT_HOURS = 12
DEFAULT_LOOKBACK_DAYS = 3
DEFAULT_MONTHLY_LIMIT = 3

COUNTABLE_STATES = {
    "Pending Manager Approval",
    "Manager Approved",
    "Pending For HR Approval",
    "Approved By HR",
}

OPEN_STATES = {
    "Pending Manager Approval",
    "Manager Approved",
    "Pending For HR Approval",
}

APPROVED_STATES = {"Approved By HR"}


def execute(filters=None):
    filters = frappe._dict(filters or {})
    validate_filters(filters)

    columns = get_columns()
    data = get_report_data(filters)

    # Show all report columns even when no records are available.
    # This is only a display placeholder, not an actual database record.
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

    return columns, data


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

    assignments = get_shift_assignments(employee_names, to_date)

    leave_map = get_leave_map(
        employee_names, from_date, to_date
    )

    request_map = get_attendance_request_map(
        employee_names, from_date, to_date
    )

    month_start = from_date.replace(day=1)
    month_end = add_months(to_date.replace(day=1), 1)
    month_end = add_days(month_end, -1)

    regularizations = get_regularizations(
        employee_names, month_start, month_end
    )

    settings = get_settings()
    holiday_cache = {}

    rows = []

    for employee in employees:
        employee_assignments = assignments.get(employee.name, [])

        for attendance_date in dates:
            key = (employee.name, attendance_date)

            attendance = attendance_map.get(key)

            assignment = get_assignment_for_date(
                employee_assignments, attendance_date
            )

            shift_name = (
                assignment.shift_type if assignment
                else employee.default_shift
            )

            shift = get_shift_details(shift_name)

            shift_start_dt, shift_end_dt = get_shift_datetimes(
                attendance_date, shift
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
                in_datetime, out_datetime
            )

            # Status is taken from Attendance only.
            status = attendance.status if attendance else "Not Marked"

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
                employee.name, attendance_date
            )

            eligible, remarks = get_eligibility(
                attendance_date=attendance_date,
                status=status,
                missed_punch=missed_punch,
                shift_end=shift_end_dt,
                settings=settings,
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


def get_regularizations(employee_names, from_date, to_date):
    records = frappe.get_all(
        "Attendance Regularization",
        filters={
            "employee": ["in", employee_names],
            "date": ["between", [from_date, to_date]],
        },
        fields=[
            "employee",
            "date",
            "workflow_state",
        ],
    )

    counts = {}

    for record in records:
        if record.workflow_state not in COUNTABLE_STATES:
            continue

        date_value = getdate(record.date)

        key = (
            record.employee,
            date_value.year,
            date_value.month,
        )

        counts[key] = counts.get(key, 0) + 1

    return counts


def get_existing_request(employee, attendance_date):
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
        if record.workflow_state not in {
            "Rejected By Manager",
            "Rejected By HR",
            "Canceled",
        }:
            return record

    return records[0] if records else None


def get_settings():
    if not frappe.db.exists(
        "DocType",
        "Attendance Settings",
    ):
        return frappe._dict()

    return frappe._dict(
        frappe.get_single("Attendance Settings").as_dict()
    )


def get_eligibility(
    attendance_date,
    status,
    missed_punch,
    shift_end,
    settings,
    month_count,
    existing_request,
    is_full_leave,
    is_holiday,
    is_weekly_off,
    is_half_leave,
    is_half_request,
):
    if (
        is_full_leave
        or status == "On Leave"
        or is_holiday
        or is_weekly_off
    ):
        return "No", ""

    if existing_request:
        state = existing_request.workflow_state or "Draft"

        if state in OPEN_STATES:
            return "No", "Regularization pending approval"

        if state in APPROVED_STATES:
            return "No", "Already regularized"

    if (
        missed_punch not in {"IN", "OUT", "BOTH"}
        and status != "Absent"
    ):
        return "No", ""

    if not settings.get("enable_regularization"):
        return "No", "Regularization is disabled in Attendance Settings"

    if attendance_date < add_days(
        getdate(nowdate()),
        -DEFAULT_LOOKBACK_DAYS,
    ):
        return "No", "Date is outside the regularization period"

    wait_hours = (
        settings.get("regularization_from_hours")
        or DEFAULT_WAIT_HOURS
    )

    if shift_end and now_datetime() < (
        shift_end + timedelta(hours=wait_hours)
    ):
        return "No", f"Wait for {wait_hours} hours to regularize"

    monthly_limit = (
        settings.get("max_requests_per_month")
        or DEFAULT_MONTHLY_LIMIT
    )

    if month_count >= monthly_limit:
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
        "Not Marked": 2,
        "Half Day": 3,
        "Present": 4,
        "Work From Home": 5,
        "On Leave": 6,
    }

    return priority.get(status, 7)