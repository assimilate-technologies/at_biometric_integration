# at_biometric_integration/scheduler.py
import frappe
from .utils import biometric_sync, checkin_processing, attendance_processing, auto_submit, cleanup
from frappe.utils import now

def run_attendance_scheduler():
    summary = {"time": now(), "devices": [], "created_checkins": 0, "created_attendance": 0, "submitted": 0, "errors": []}
    devices = frappe.get_all("Biometric Device Settings", fields=["device_ip", "device_port", "name"])
    if not devices:
        return summary

    for dev in devices:
        ip = dev.get("device_ip")
        port = dev.get("device_port") or 4370
        try:
            logs = biometric_sync.fetch_attendance_from_device(ip, port)
            if logs:
                biometric_sync.process_attendance_logs(ip, logs)
            created = checkin_processing.create_frappe_checkins_from_devices([dev])
            summary["created_checkins"] += len(created)
            # process today's attendance
            processed = attendance_processing.process_attendance_realtime()
            summary["created_attendance"] += len(processed)
            summary["devices"].append(ip)
        except Exception as e:
            frappe.log_error(e, "run_attendance_scheduler")
            summary["errors"].append(str(e))

    # auto submit
    try:
        submitted = auto_submit.auto_submit_due_attendances()
        summary["submitted"] = len(submitted)
    except Exception as e:
        frappe.log_error(e, "run_attendance_scheduler auto_submit")
        summary["errors"].append(str(e))

    # cleanup
    try:
        cleanup.cleanup_old_attendance_logs()
    except Exception as e:
        frappe.log_error(e, "run_attendance_scheduler cleanup")
        summary["errors"].append(str(e))

    return summary
