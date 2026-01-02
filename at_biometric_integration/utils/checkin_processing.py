import os
import json
import frappe
from .helpers import log_error
from frappe.utils import get_datetime, getdate, add_days, nowdate
from .biometric_sync import load_attendance_data


def create_frappe_checkins_from_devices(devices):
    created = []

    for dev in devices:
        # Support both document objects and dict-like objects from scheduler
        ip = getattr(dev, "device_ip", None) or (dev.get("device_ip") if isinstance(dev, dict) else None)
        
        if not ip:
            continue
            
        # Instead of just today, let's look at the last 7 days of JSON logs
        # to catch any that were fetched but never successfully created as Checkins.
        
        all_records = []
        for i in range(7):
            date_str = getdate(add_days(nowdate(), -i)).strftime("%Y-%m-%d")
            path = frappe.get_site_path("public", "files", "attendance_logs", f"attendance_{ip}_{date_str}.json")
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        day_records = json.load(f)
                        if isinstance(day_records, list):
                            all_records.extend(day_records)
                except Exception as e:
                    log_error(e, f"Error reading log file {path}")

        if not all_records:
            continue

        user_ids = list({str(r["user_id"]).strip() for r in all_records if r.get("user_id")})
        if not user_ids:
            continue

        # Fetch all active employees that could match the user_ids
        # We also fetch all active employees to handle leading zero mismatches in memory
        employees = frappe.get_all(
            "Employee",
            filters={"status": "Active"},
            fields=["name", "attendance_device_id"],
            limit_page_length=0
        )

        # Build map with multiple keys to handle '1' vs '01'
        emp_map = {}
        for e in employees:
            if e.attendance_device_id:
                d_id = str(e.attendance_device_id).strip()
                emp_map[d_id] = e.name
                if d_id.isdigit():
                    emp_map[str(int(d_id))] = e.name # Add key without leading zeros

        # Collect timestamps to fetch existing check-ins in one go
        timestamps = [r["timestamp"] for r in all_records]
        existing = set()
        
        if timestamps:
            # Fetch ALL existing check-ins in the range to avoid duplicates
            existing_checkins = frappe.get_all(
                "Employee Checkin",
                filters={
                    "time": ["between", [min(timestamps), max(timestamps)]]
                },
                fields=["employee", "time"],
                limit_page_length=0
            )

            for c in existing_checkins:
                if c.time:
                    # Standardize format for set comparison
                    ts_str = c.time.strftime("%Y-%m-%d %H:%M:%S") if not isinstance(c.time, str) else c.time
                    existing.add((c.employee, ts_str))

        for r in all_records:
            u_id = str(r["user_id"]).strip()
            emp = emp_map.get(u_id)
            
            # Fallback for numeric IDs if direct match fails
            if not emp and u_id.isdigit():
                emp = emp_map.get(str(int(u_id)))

            if not emp:
                continue

            # Ensure timestamp is formatted correctly
            ts = r["timestamp"]
            key = (emp, ts)
            
            if key in existing:
                continue

            punch = r.get("punch")
            # Log Type Mapping: 0, 3, 4 are treated as IN; others as OUT
            log_type = "IN" if punch in (0, 3, 4) else "OUT"

            try:
                checkin = frappe.get_doc({
                    "doctype": "Employee Checkin",
                    "employee": emp,
                    "time": ts,
                    "log_type": log_type,
                    "device_id": r.get("uid"),
                    "device_ip": ip,
                    "latitude": "0.0",
                    "longitude": "0.0",
                    "skip_attendance": 0
                })
                checkin.insert(ignore_permissions=True)
                created.append(checkin.name)
                
                # Add to local existing set to prevent double creation if log duplicates in JSON
                existing.add(key)

            except Exception as e:
                log_error(e, f"Checkin Creation Failed: {emp} at {ts}")

    if created:
        frappe.db.commit()

    return created
