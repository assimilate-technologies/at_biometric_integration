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

        if (frm.doc.employee && frm.doc.date) await handle_full_flow(frm);
    },

    refresh: async function (frm) {
        apply_read_only_rules(frm);
        if (frm.doc.employee && frm.doc.date) await handle_full_flow(frm);
    },

    employee: async function (frm) {
        if (frm.doc.employee && frm.doc.date) await handle_full_flow(frm);
    },

    date: async function (frm) {
        if (frm.doc.employee && frm.doc.date) await handle_full_flow(frm);
    },

    validate(frm) {
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
    await check_employee_monthly_limit(frm);
}


// -------------------- Read-Only Based on Workflow --------------------
function apply_read_only_rules(frm) {
    const read_only_states = ["Approved By HR", "Rejected By HR"];
    const read_only = read_only_states.includes(frm.doc.workflow_state);

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
            frm.set_value("system_in_time", null);
            frm.set_value("system_out_time", null);
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

        frm.set_value("system_in_time", in_val);
        frm.set_value("system_out_time", out_val);

        if (in_val && !frm.doc.in_time) frm.set_value("in_time", in_val);
        if (out_val && !frm.doc.out_time) frm.set_value("out_time", out_val);

    } catch (err) {
        console.error("Checkin Fetch Error:", err);
        frm.set_value("system_in_time", null);
        frm.set_value("system_out_time", null);
    }
}
