# at_biometric_integration/utils/biometric_sync.py
import frappe
import os
import json
from frappe.utils import getdate, nowdate, get_datetime
from zk import ZK
from .helpers import log_error

ATTENDANCE_NAME = "attendance_logs"
ATTENDANCE_DIR = frappe.get_site_path("public", "files", ATTENDANCE_NAME)

PUNCH_MAPPING = {
    0: "Check-In",
    1: "Check-Out",
    2: "Break-Out",
    3: "Break-In",
    4: "Overtime Start",
    5: "Overtime End"
}

def ensure_dir():
    if not os.path.exists(ATTENDANCE_DIR):
        os.makedirs(ATTENDANCE_DIR, exist_ok=True)

def get_attendance_file_path(ip):
    date_str = getdate(nowdate()).strftime("%Y-%m-%d")
    return os.path.join(ATTENDANCE_DIR, f"attendance_{ip}_{date_str}.json")

def load_attendance_data(ip):
    ensure_dir()
    path = get_attendance_file_path(ip)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            log_error(e, "load_attendance_data")
            return []
    return []

def save_attendance_data(ip, records):
    ensure_dir()
    path = get_attendance_file_path(ip)
    try:
        with open(path, "w") as f:
            json.dump(records, f, default=str, indent=2)
    except Exception as e:
        log_error(e, "save_attendance_data")

def fetch_attendance_from_device(ip, port=4370, timeout=10):
    """Connect to device using zk library and return device logs"""
    try:
        zk = ZK(ip, port=int(port), timeout=timeout, force_udp=False, ommit_ping=False)
        conn = zk.connect()
        if conn:
            logs = conn.get_attendance()
            conn.disconnect()
            return logs
    except Exception as e:
        log_error(f"fetch_attendance_from_device failed for {ip}:{port} - {e}", "Device Fetch")
    return []

def process_attendance_logs(ip, logs):
    """
    Save logs in JSON file and create Employee Checkin records.
    Returns list of new records added.
    """
    if not logs:
        return []

    existing = load_attendance_data(ip)
    existing_keys = {(r.get("user_id"), r.get("timestamp")) for r in existing}
    new_records = []

    # Map device IDs to employees
    user_ids = [str(log.user_id) for log in logs]
    employee_map = {
        r.attendance_device_id: r.name
        for r in frappe.get_all(
            "Employee",
            filters={"attendance_device_id": ["in", user_ids], "status": "Active"},
            fields=["name", "attendance_device_id"]
        )
    }

    for log in logs:
        ts = get_datetime(log.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        key = (str(log.user_id), ts)
        if key in existing_keys:
            continue

        rec = {
            "uid": getattr(log, "uid", None),
            "user_id": str(getattr(log, "user_id", None)),
            "timestamp": ts,
            "status": getattr(log, "status", None),
            "punch": getattr(log, "punch", None),
            "punch_type": PUNCH_MAPPING.get(getattr(log, "punch", None), "Unknown"),
            "device_ip": ip
        }
        existing.append(rec)
        new_records.append(rec)

        # --- Create Employee Checkin if employee exists ---
        employee = employee_map.get(str(log.user_id))
        if employee:
            log_type = "IN" if log.punch in [0, 4] else "OUT"
            try:
                frappe.get_doc({
                    "doctype": "Employee Checkin",
                    "employee": employee,
                    "time": ts,
                    "log_type": log_type,
                    "device_id": log.user_id,
                    "device_ip": ip,
                    "latitude": "0.0",
                    "longitude": "0.0",
                }).insert(ignore_permissions=True)
            except Exception as e:
                log_error(f"Failed to insert checkin for employee {employee}: {e}", "Checkin Insert Error")

    if new_records:
        save_attendance_data(ip, existing)
        frappe.db.commit()

    return new_records
