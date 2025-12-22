# at_biometric_integration/utils/auto_submit.py
import frappe
from .attendance_processing import auto_submit_due_attendances as robust_auto_submit

def auto_submit_due_attendances():
    """
    Deprecated: This module is replaced by the robust logic in attendance_processing.
    Proxies to at_biometric_integration.utils.attendance_processing.auto_submit_due_attendances
    """
    return robust_auto_submit()
