# at_biometric_integration/utils/checkin_processing.py
import frappe
from .helpers import log_error
from frappe.utils import get_datetime

def create_frappe_checkins_from_devices(devices):
    """
    devices: list of dicts with keys 'device_ip' or device name structure.
    Reads json files created by biometric_sync and creates Employee Checkin records.
    Returns list of created checkin names.
    """
    created = []
    # Gather all records from supplied devices
    all_records = []
    for dev in devices:
        ip = dev.get("device_ip") or dev.get("ip") or dev.get("name")
        # read attendance file
        from .biometric_sync import load_attendance_data
        recs = load_attendance_data(ip)
        for r in recs:
            r["device_ip"] = ip
        all_records.extend(recs)

    if not all_records:
        return created

    # Map user_ids to Employee
    user_ids = list({r.get("user_id") for r in all_records if r.get("user_id")})
    employees = frappe.get_all("Employee", filters={"attendance_device_id": ["in", user_ids], "status": "Active"}, fields=["name", "attendance_device_id"])
    emp_map = {e.attendance_device_id: e.name for e in employees}

    # Build list of timestamps to check existing
    timestamps = [r.get("timestamp") for r in all_records]
    existing_checkins = {
        (c.employee, c.time.strftime("%Y-%m-%d %H:%M:%S"))
        for c in frappe.get_all("Employee Checkin", filters={"time": ["in", timestamps]}, fields=["employee", "time"])
    }

    to_insert = []
    for r in all_records:
        uid = r.get("user_id")
        emp = emp_map.get(uid)
        if not emp:
            continue
        key = (emp, r.get("timestamp"))
        if key in existing_checkins:
            continue
        # determine log_type - prefer punch mapping (0,4 => IN else OUT)
        punch = r.get("punch")
        log_type = "IN" if punch in (0, 4) else "OUT"
        to_insert.append({
            "doctype": "Employee Checkin",
            "employee": emp,
            "time": r.get("timestamp"),
            "log_type": log_type,
            "device_id": r.get("uid"),
            "device_ip": r.get("device_ip")
        })

    for doc in to_insert:
        try:
            d = frappe.get_doc(doc).insert(ignore_permissions=True)
            created.append(d.name)
        except Exception as e:
            log_error(f"Failed to insert checkin {doc}: {e}", "Checkin Insert")

    if created:
        frappe.db.commit()
    return created
