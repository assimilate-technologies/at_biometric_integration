# at_biometric_integration/api.py
import frappe
from .utils import biometric_sync, checkin_processing, attendance_processing, auto_submit, cleanup
from frappe import _

@frappe.whitelist()
def fetch_and_upload_attendance():
    """
    Master controller called by scheduler:
      - fetch logs from devices
      - store JSON
      - create checkins
      - build attendance
      - try auto-submit
      - cleanup
    """
    response = {"processed": [], "created_checkins": [], "created_attendance": [], "submitted": [], "errors": []}

    devices = frappe.get_all("Biometric Device Settings", fields=["device_ip", "device_port", "name"])
    if not devices:
        response["errors"].append("No biometric devices configured.")
        return response

    for dev in devices:
        ip = dev.get("device_ip")
        port = dev.get("device_port") or 4370
        try:
            # fetch ALL logs from device
            logs = biometric_sync.fetch_attendance_from_device(ip, port)
            if not logs:
                # still try to create checkins from existing JSON if present
                created = checkin_processing.create_frappe_checkins_from_devices([dev])
                if created:
                    response["created_checkins"].extend(created)
                response["processed"].append(ip)
                continue

            # process logs into JSON store
            new = biometric_sync.process_attendance_logs(ip, logs)
            # create checkins from JSON
            created = checkin_processing.create_frappe_checkins_from_devices([dev])
            if created:
                response["created_checkins"].extend(created)
            # build attendance for today
            processed = attendance_processing.process_attendance_realtime()
            if processed:
                response["created_attendance"].extend(processed)
            response["processed"].append(ip)
        except Exception as e:
            frappe.log_error(e, "fetch_and_upload_attendance")
            response["errors"].append(str(e))

    # try auto-submit due attendances
    try:
        submitted = auto_submit.auto_submit_due_attendances()
        if submitted:
            response["submitted"].extend(submitted)
    except Exception as e:
        frappe.log_error(e, "auto_submit")
        response["errors"].append(str(e))

    # cleanup old json files
    try:
        cleanup.cleanup_old_attendance_logs()
    except Exception as e:
        frappe.log_error(e, "cleanup")

    return response

@frappe.whitelist()
def mark_attendance():
    """Backward-compatible endpoint"""
    attendance_processing.process_attendance_realtime()
    return {"message": "Marked attendance (realtime)"}


@frappe.whitelist()
def sync_all_biometric_data():
    """
    Sync ALL biometric data from all devices.
    This ensures all check-in records are synced, including historical data.
    """
    response = {"processed": [], "created_checkins": [], "created_attendance": [], "errors": []}
    
    devices = frappe.get_all("Biometric Device Settings", fields=["device_ip", "device_port", "name"])
    if not devices:
        response["errors"].append("No biometric devices configured.")
        return response
    
    for dev in devices:
        ip = dev.get("device_ip")
        port = dev.get("device_port") or 4370
        try:
            # Sync all historical data from device
            new_records = biometric_sync.sync_all_historical_data(ip, port)
            
            # Create checkins from ALL JSON files (not just today's)
            created = checkin_processing.create_frappe_checkins_from_devices([dev])
            if created:
                response["created_checkins"].extend(created)
            
            # Process attendance for all dates
            processed = attendance_processing.process_attendance_realtime()
            if processed:
                response["created_attendance"].extend(processed)
            
            response["processed"].append({
                "device": ip,
                "new_records": len(new_records),
                "created_checkins": len(created) if created else 0
            })
        except Exception as e:
            frappe.log_error(e, f"sync_all_biometric_data - {ip}")
            response["errors"].append(f"{ip}: {str(e)}")
    
    return response
