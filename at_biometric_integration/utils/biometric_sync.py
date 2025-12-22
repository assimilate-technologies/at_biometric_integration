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
    if not logs:
        return []

    existing = load_attendance_data(ip)
    existing_keys = {
        (str(r.get("user_id")), str(r.get("timestamp")))
        for r in existing if isinstance(r, dict)
    }

    new_records = []

    for log in logs:
        ts = get_datetime(log.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        key = (str(log.user_id), ts)

        if key in existing_keys:
            continue

        rec = {
            "uid": getattr(log, "uid", None),
            "user_id": str(log.user_id),
            "timestamp": ts,
            "punch": getattr(log, "punch", None),
            "punch_type": PUNCH_MAPPING.get(log.punch, "Unknown"),
            "device_ip": ip,
        }

        existing.append(rec)
        existing_keys.add(key)
        new_records.append(rec)

    if new_records:
        save_attendance_data(ip, existing)

    return new_records
