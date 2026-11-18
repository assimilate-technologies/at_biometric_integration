frappe.ui.form.on("Interview", {
    refresh(frm) {

        // Override the standard HRMS feedback dialog
        frm.events.show_feedback_dialog = async function(frm, data) {

            // Get standard HRMS Skill Assessment fields
            let fields = await frm.events.get_fields_for_feedback();

            let dialog = new frappe.ui.Dialog({
                title: __("Submit Feedback"),

                fields: [
                    {
                        fieldname: "skill_set",
                        fieldtype: "Table",
                        label: __("Skill Assessment"),
                        cannot_add_rows: false,
                        in_editable_grid: true,
                        reqd: 1,
                        fields: fields,
                        data: data
                    },
                    {
                        fieldname: "result",
                        fieldtype: "Select",
                        options: ["", "Cleared", "Rejected"],
                        label: __("Result"),
                        reqd: 1
                    },
                    {
                        fieldname: "feedback",
                        fieldtype: "Small Text",
                        label: __("Feedback"),
                        reqd: 1
                    }
                ],

                size: "large",
                minimizable: true,
                static: true,

                primary_action_label: __("Submit"),

                primary_action: async function(values) {

                    // Get feedback text
                    let feedback = (values.feedback || "").trim();

                    // Count characters
                    let char_count = feedback.length;

                    // Minimum 500 characters validation
                    if (char_count < 500) {

                        frappe.msgprint({
                            title: __("Feedback Required"),
                            indicator: "red",
                            message: __(
                                "Feedback must be at least {0} characters.",
                                [500]
                            )
                        });

                        return;
                    }

                    // Disable submit button while saving
                    dialog.get_primary_btn().prop("disabled", true);

                    try {

                        // Call standard HRMS method
                        await frappe.call({
                            method: "hrms.hr.doctype.interview.interview.create_interview_feedback",
                            args: {
                                data: values,
                                interview_name: frm.doc.name,
                                interviewer: frappe.session.user,
                                job_applicant: frm.doc.job_applicant
                            }
                        });

                        // Close dialog after successful save
                        dialog.hide();

                        // Reload Interview document
                        await frm.reload_doc();

                    } catch (error) {

                        // Enable button if saving fails
                        dialog.get_primary_btn().prop("disabled", false);

                    }
                }
            });

            dialog.show();
            dialog.get_close_btn().show();
        };
    }
});
