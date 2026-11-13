// ======================================================================
// Employee Checkin Form View Customizations
// Ensures only Administrator and WFH employees can create checkins
// ======================================================================

frappe.ui.form.on('Employee Checkin', {
    onload: function (frm) {
        if (frm.is_new() && frappe.session.user !== "Administrator") {
            frappe.call({
                method: "at_biometric_integration.utils.attendance_processing.check_user_wfh_status",
                callback: function (r) {
                    const status = r && r.message;
                    if (!status || !status.can_add) {
                        frappe.msgprint({
                            title: __('Action Not Allowed'),
                            indicator: 'red',
                            message: __('Manual check-in creation is only allowed for Work From Home employees and Administrator. Office employees must punch via biometric devices.')
                        });
                        frappe.set_route('List', 'Employee Checkin');
                    } else if (status.employee && !frm.doc.employee) {
                        frm.set_value('employee', status.employee);
                    }
                }
            });
        }
    },
    refresh: function (frm) {
        if (frappe.session.user !== "Administrator") {
            frappe.call({
                method: "at_biometric_integration.utils.attendance_processing.check_user_wfh_status",
                callback: function (r) {
                    const status = r && r.message;
                    if (!status || !status.can_add) {
                        // Hide "New" and duplicate actions on existing docs
                        frm.page.clear_primary_action();
                        frm.page.wrapper.find('.primary-action').hide();
                        if (frm.is_new()) {
                            frm.disable_save();
                        }
                    } else if (frm.is_new() && status.employee && !frm.doc.employee) {
                        frm.set_value('employee', status.employee);
                    }
                }
            });
        }
    }
});

