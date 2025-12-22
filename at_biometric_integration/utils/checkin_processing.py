# at_biometric_integration/utils/checkin_processing.py
import frappe
from .helpers import log_error
from frappe.utils import get_datetime

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
            filters={"attendance_device_id": ["in", user_ids], "status": "Active"},
            fields=["name", "attendance_device_id"]
        )
        emp_map = {e.attendance_device_id: e.name for e in employees}

        timestamps = [r["timestamp"] for r in records]

        existing = {
            (c.employee, c.time.strftime("%Y-%m-%d %H:%M:%S"))
            for c in frappe.get_all(
                "Employee Checkin",
                filters={"time": ["in", timestamps]},
                fields=["employee", "time"]
            )
        }

        to_insert = []

        for r in records:
            emp = emp_map.get(r["user_id"])
            if not emp:
                continue

            key = (emp, r["timestamp"])
            if key in existing:
                continue

            log_type = "IN" if r.get("punch") in (0, 4) else "OUT"

            to_insert.append({
                "doctype": "Employee Checkin",
                "employee": emp,
                "time": r["timestamp"],
                "log_type": log_type,
                "device_id": r.get("uid"),
                "device_ip": ip,
                "latitude": "0.0",
                "longitude": "0.0",
            })

        for doc in to_insert:
            d = frappe.get_doc(doc).insert(ignore_permissions=True)
            created.append(d.name)

    if created:
        frappe.db.commit()

    return created
