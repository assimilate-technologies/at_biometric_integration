# at_biometric_integration/utils/cleanup.py
import os
import frappe
from frappe.utils import nowdate
from .biometric_sync import ATTENDANCE_DIR
from .helpers import log_error

def cleanup_old_attendance_logs(retain_days=7):
    """
    Remove attendance_<ip>_<date>.json files older than retain_days
    """
    try:
        if not os.path.exists(ATTENDANCE_DIR):
            return
        cutoff = frappe.utils.add_days(nowdate(), -retain_days)
        for filename in os.listdir(ATTENDANCE_DIR):
            if filename.endswith(".json"):
                # filename pattern: attendance_<ip>_YYYY-MM-DD.json
                parts = filename.split("_")
                if len(parts) < 3:
                    continue
                date_part = parts[-1].replace(".json", "")
                try:
                    if date_part < cutoff:
                        os.remove(os.path.join(ATTENDANCE_DIR, filename))
                except Exception:
                    # skip invalid date parses
                    continue
    except Exception as e:
        log_error(e, "cleanup_old_attendance_logs")
