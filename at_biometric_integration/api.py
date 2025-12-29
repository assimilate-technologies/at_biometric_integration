# at_biometric_integration/api.py
import frappe
from .utils import biometric_sync, checkin_processing, attendance_processing, auto_submit, cleanup
from frappe import _

@frappe.whitelist()
def fetch_and_upload_attendance():
    response = {
        "processed": [],
        "created_checkins": [],
        "created_attendance": [],
        "submitted": [],
        "errors": []
    }

    devices = frappe.get_all(
        "Biometric Device Settings",
        fields=["device_ip", "device_port"]
    )

    if not devices:
        response["errors"].append("No biometric devices configured")
        return response

    # -------------------------
    # PHASE 1: DEVICE → JSON
    # -------------------------
    for dev in devices:
        ip = dev.device_ip
        port = dev.device_port or 4370

        try:
            logs = biometric_sync.fetch_attendance_from_device(ip, port)
            biometric_sync.process_attendance_logs(ip, logs)
            response["processed"].append(ip)
        except Exception as e:
            frappe.log_error(str(e), "Biometric Sync")
            response["errors"].append(f"{ip}: {e}")

    # -------------------------
    # PHASE 2: JSON → CHECKINS
    # -------------------------
    try:
        created = checkin_processing.create_frappe_checkins_from_devices(devices)
        response["created_checkins"] = created
    except Exception as e:
        frappe.log_error(str(e), "Checkin Creation")
        response["errors"].append(str(e))

    # -------------------------
    # PHASE 3: ATTENDANCE (ONCE)
    # -------------------------
    try:
        created_att = attendance_processing.process_attendance_realtime()
        if created_att:
            response["created_attendance"] = created_att
    except Exception as e:
        frappe.log_error(str(e), "Attendance Processing")
        response["errors"].append(str(e))

    # -------------------------
    # PHASE 4: AUTO SUBMIT
    # -------------------------
    try:
        submitted = auto_submit.auto_submit_due_attendances()
        if submitted:
            response["submitted"] = submitted
    except Exception as e:
        frappe.log_error(str(e), "Auto Submit")

    # -------------------------
    # PHASE 5: CLEANUP
    # -------------------------
    cleanup.cleanup_old_attendance_logs()

    return response


@frappe.whitelist()
def mark_attendance(from_date=None, to_date=None):
    """
    Dynamically process attendance for all dates with checkins.
    If dates provided, processes that specific range.
    If no dates provided, automatically finds and processes ALL dates with checkins.
    This ensures no dates are missed, including dates like Dec 26th after holidays.
    """
    from frappe.utils import getdate
    
    if from_date:
        from_date = getdate(from_date)
    if to_date:
        to_date = getdate(to_date)
    
    processed = attendance_processing.process_attendance_realtime(from_date, to_date)
    return {
        "message": "Marked attendance (realtime)",
        "processed_count": len(processed) if processed else 0,
        "processed": processed
    }


@frappe.whitelist()
def backfill_all_attendance():
    """
    Comprehensive backfill function to create attendance for ALL past dates with checkins.
    This ensures no dates are missed, even if they were skipped in previous runs.
    Use this to fix missing attendance records in both local and production.
    """
    try:
        processed = attendance_processing.backfill_all_missing_attendance()
        return {
            "message": "Backfill completed successfully",
            "processed_count": len(processed) if processed else 0,
            "processed": processed[:100] if len(processed) > 100 else processed  # Limit response size
        }
    except Exception as e:
        frappe.log_error(str(e), "Backfill Attendance API Error")
        return {
            "message": f"Backfill error: {str(e)}",
            "processed_count": 0,
            "error": str(e)
        }


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
