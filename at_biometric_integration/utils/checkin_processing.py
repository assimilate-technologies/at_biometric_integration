# at_biometric_integration/utils/checkin_processing.py
import frappe
from .helpers import log_error
from frappe.utils import get_datetime
from .biometric_sync import load_attendance_data


def create_frappe_checkins_from_devices(devices):
    created = []

    for dev in devices:
        ip = dev.device_ip
        records = load_attendance_data(ip)

        if not records:
            continue

        user_ids = list({r["user_id"] for r in records})

        employees = frappe.get_all(
            "Employee",
            filters={
                "attendance_device_id": ["in", user_ids],
                "status": "Active"
            },
            fields=["name", "attendance_device_id"]
        )

        emp_map = {e.attendance_device_id: e.name for e in employees}
        timestamps = [r["timestamp"] for r in records]

        existing = set()
        if timestamps:
            existing_checkins = frappe.get_all(
                "Employee Checkin",
                filters={
                    "time": ["between", [min(timestamps), max(timestamps)]]
                },
                fields=["employee", "time"]
            )

            existing = {
                (c.employee, c.time.strftime("%Y-%m-%d %H:%M:%S"))
                for c in existing_checkins
            }

        for r in records:
            emp = emp_map.get(r["user_id"])
            if not emp:
                continue

            key = (emp, r["timestamp"])
            if key in existing:
                continue

            punch = r.get("punch")
            log_type = "IN" if punch in (0, 4) else "OUT"

            try:
                d = frappe.get_doc({
                    "doctype": "Employee Checkin",
                    "employee": emp,
                    "time": r["timestamp"],
                    "log_type": log_type,
                    "device_id": r.get("uid"),
                    "device_ip": ip,
                    "latitude": "0.0",
                    "longitude": "0.0",
                }).insert(ignore_permissions=True)

                created.append(d.name)

            except Exception as e:
                log_error(e, "Employee Checkin Insert")

    if created:
        frappe.db.commit()

    return created
