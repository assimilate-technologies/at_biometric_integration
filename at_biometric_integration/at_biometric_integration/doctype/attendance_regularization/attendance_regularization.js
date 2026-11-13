// -------------------- Attendance Regularization Client Script (Final) --------------------
frappe.ui.form.on("Attendance Regularization", {
    onload: async function (frm) {
        apply_read_only_rules(frm);

        // Auto-fill employee if logged-in user is an employee
        if (frappe.user.has_role("Employee") && !frm.doc.employee) {
            const emp = await frappe.db.get_value(
                "Employee",
                { user_id: frappe.session.user },
                "name"
            );
            if (emp?.message?.name) frm.set_value("employee", emp.message.name);
        }

        // Note: handle_full_flow is intentionally NOT called here.
        // `refresh` fires on every page load (right after onload) and also on
        // every re-save, so running it here would execute the flow twice.
    },

    refresh: async function (frm) {
        apply_read_only_rules(frm);
        // Sync checkbox to match persisted attendance_status on load
        if (frm.doc.attendance_status === "Work From Home" && !frm.doc.is_work_from_home) {
            frm.set_value("is_work_from_home", 1);
        }
        toggle_time_mandatory(frm);
        if (frm.doc.employee && frm.doc.date) await handle_full_flow(frm);
    },

    // 'attendance_status' is now read-only (auto-calculated) — no manual trigger needed.
    // Use 'is_work_from_home' checkbox to toggle WFH status.
    is_work_from_home: function (frm) {
        if (frm.doc.is_work_from_home) {
            // User checked WFH → force status to Work From Home
            frm.set_value("attendance_status", "Work From Home");
        } else {
            // User unchecked WFH → recalculate from times
            update_attendance_status_from_times(frm);
        }
        toggle_time_mandatory(frm);
    },

    employee: async function (frm) {
        if (frm.doc.employee && frm.doc.date) await handle_full_flow(frm);
    },

    date: async function (frm) {
        if (frm.doc.employee && frm.doc.date) await handle_full_flow(frm);
    },

    in_time: function (frm) {
        if (!frm.doc.is_work_from_home) {
            update_attendance_status_from_times(frm);
        }
    },

    out_time: function (frm) {
        if (!frm.doc.is_work_from_home) {
            update_attendance_status_from_times(frm);
        }
    },

    before_save: function (frm) {
        if (!frm.doc.is_work_from_home) {
            update_attendance_status_from_times(frm);
        }
    },

    validate(frm) {
        toggle_time_mandatory(frm);

        if (!frm.doc.is_work_from_home) {
            update_attendance_status_from_times(frm);
            if (!frm.doc.in_time || !frm.doc.out_time) {
                frappe.validated = false;
                frappe.msgprint({
                    title: __("Missing Mandatory Fields"),
                    message: __("In Time and Out Time are mandatory when Attendance Status is not Work From Home."),
                    indicator: "red"
                });
                return;
            }
        }

        // Block saving when limit reached
        if (frm.doc.__disable_save_by_limit) {
            frappe.validated = false;
            frappe.msgprint({
                title: "Monthly Limit Reached",
                message: frm.doc.__month_limit_message || "Monthly limit reached.",
                indicator: "red"
            });
        }
    }
});


// -------------------- Combined Flow (Checkins → Limit Check) --------------------
async function handle_full_flow(frm) {
    await fetch_system_checkin_times(frm);
    if (!frm.doc.is_work_from_home) {
        update_attendance_status_from_times(frm);
    }
    await check_employee_monthly_limit(frm);
}

// -------------------- Toggle In/Out Time Mandatory Based on WFH --------------------
function toggle_time_mandatory(frm) {
    const is_wfh = frm.doc.is_work_from_home ? true : (frm.doc.attendance_status === "Work From Home");
    frm.set_df_property("in_time", "reqd", is_wfh ? 0 : 1);
    frm.set_df_property("out_time", "reqd", is_wfh ? 0 : 1);
}

// -------------------- Auto-update Attendance Status from Times --------------------
function update_attendance_status_from_times(frm) {
    if (frm.doc.is_work_from_home) return;
    if (!frm.doc.in_time || !frm.doc.out_time) return;

    function parse_to_seconds(t) {
        if (!t) return 0;
        const parts = String(t).trim().split(":");
        const h = parseInt(parts[0], 10) || 0;
        const m = parseInt(parts[1], 10) || 0;
        const s = parseInt(parts[2], 10) || 0;
        return h * 3600 + m * 60 + s;
    }

    const in_sec = parse_to_seconds(frm.doc.in_time);
    const out_sec = parse_to_seconds(frm.doc.out_time);

    let diff = out_sec - in_sec;
    if (diff < 0) {
        diff += 24 * 3600;
    }

    const FIVE_HOURS = 5 * 3600;                 // 18,000 seconds (5:00:00)
    const EIGHT_FORTY_FIVE = 8 * 3600 + 45 * 60; // 31,500 seconds (8:45:00)

    let status = "Present";
    if (diff < FIVE_HOURS) {
        status = "Absent";
    } else if (diff < EIGHT_FORTY_FIVE) {
        status = "Half Day";
    } else {
        status = "Present";
    }

    if (frm.doc.attendance_status !== status) {
        frm.set_value("attendance_status", status);
    }
}


// -------------------- Read-Only Based on Workflow --------------------
function apply_read_only_rules(frm) {
    const read_only_states = ["Approved By HR", "Rejected By HR"];
    const read_only = read_only_states.includes(frm.doc.workflow_state);

    // attendance_status is ALWAYS read-only — it is auto-calculated from in/out times.
    // Use the 'Work From Home' checkbox to set WFH status manually.
    frm.set_df_property("attendance_status", "read_only", 1);

    frm.set_df_property("in_time", "read_only", read_only);
    frm.set_df_property("out_time", "read_only", read_only);
}


// -------------------- Monthly Limit Check (Instant on change) --------------------
async function check_employee_monthly_limit(frm) {
    try {
        const res = await frappe.db.get_value(
            "Attendance Settings",
            null,
            ["enable_regularization", "max_requests_per_month"]
        );

        const s = res?.message || {};

        const enabled = cint(s.enable_regularization);
        const limit = cint(s.max_requests_per_month) || 3;

        if (!enabled) return reset_limit_flags(frm);

        if (!frm.doc.employee || !frm.doc.date)
            return reset_limit_flags(frm);

        const month_start = frappe.datetime.month_start(frm.doc.date);
        const month_end = frappe.datetime.month_end(frm.doc.date);

        const approved_count = await frappe.db.count("Attendance Regularization", {
            filters: {
                employee: frm.doc.employee,
                workflow_state: "Approved By HR",
                docstatus: 1,
                date: ["between", [month_start, month_end]]
            }
        });

        if (approved_count >= limit) {
            const month_name = new Date(`${frm.doc.date}T00:00:00`)
                .toLocaleString("en-US", { month: "long" });

            const msg = `${month_name} month limit used. You cannot create a new regularization request.`;

            frm.__disable_save_by_limit = true;
            frm.__month_limit_message = msg;

            frm.disable_save();
            frm.set_intro(msg, "red");

            // Delay required because Frappe loads buttons after refresh
            setTimeout(() => {
                if (frm.page?.hide_save_button) frm.page.hide_save_button();
                if (frm.page?.hide_actions_menu_item) frm.page.hide_actions_menu_item("Submit");
            }, 250);

            frappe.msgprint({
                title: "Monthly Limit Reached",
                message: msg,
                indicator: "red"
            });

        } else {
            reset_limit_flags(frm);
        }

    } catch (err) {
        console.error("Monthly Limit Error:", err);
        reset_limit_flags(frm);
    }
}

function reset_limit_flags(frm) {
    frm.__disable_save_by_limit = false;
    frm.__month_limit_message = "";
    frm.enable_save();
    frm.set_intro("");

    // Show save buttons again
    setTimeout(() => {
        if (frm.page?.show_save_button) frm.page.show_save_button();
    }, 250);
}


// -------------------- Fetch Check-in/Check-out --------------------
// Sync a read-only, system-owned field without marking the form dirty.
// `frm.set_value` triggers frm.dirty() (→ doc.__unsaved = 1 → "Not Saved"
// indicator) whenever the value differs from the loaded one — including the
// "" vs null mismatch, which shows "Not Saved" even though nothing changed.
function sync_readonly(frm, fieldname, value) {
    const current = frm.doc[fieldname] || "";
    const next = value || "";

    if (current === next) return; // identical → nothing to write

    // 4th arg = skip_dirty_trigger: refreshes the control but does not set
    // doc.__unsaved, so a saved Draft still shows its real status.
    frm.set_value(fieldname, value || null, null, true);
}

async function fetch_system_checkin_times(frm) {
    if (!frm.doc.employee || !frm.doc.date) return;

    const start = `${frm.doc.date} 00:00:00`;
    const end = `${frm.doc.date} 23:59:59`;

    try {
        const logs = await frappe.db.get_list("Employee Checkin", {
            filters: {
                employee: frm.doc.employee,
                time: ["between", [start, end]]
            },
            fields: ["time"],
            order_by: "time asc",
            limit: 500
        });

        if (!logs.length) {
            sync_readonly(frm, "system_in_time", null);
            sync_readonly(frm, "system_out_time", null);
            return;
        }

        const first = logs[0].time;
        const last = logs[logs.length - 1].time;

        const extract = (dt) => {
            if (!dt) return null;
            if (dt.includes(" ")) return dt.split(" ")[1].split(".")[0];
            const m = dt.match(/T?(\d{2}:\d{2}:\d{2})/);
            return m ? m[1] : null;
        };

        const in_val = extract(first);
        const out_val = extract(last);

        sync_readonly(frm, "system_in_time", in_val);
        sync_readonly(frm, "system_out_time", out_val);

        // in_time / out_time are intentionally NOT auto-filled.
        // The user must enter them manually.

    } catch (err) {
        console.error("Checkin Fetch Error:", err);
        sync_readonly(frm, "system_in_time", null);
        sync_readonly(frm, "system_out_time", null);
    }
}
