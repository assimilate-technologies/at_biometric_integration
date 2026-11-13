frappe.ui.form.on('Attendance', {
    refresh: function(frm) {
        // If in_time or out_time not set, but child checkins exist, sync from first and last checkin
        if ((!frm.doc.in_time || !frm.doc.out_time) && frm.doc.employee_checkin && frm.doc.employee_checkin.length > 0) {
            sync_times_from_child_checkins(frm);
        } else {
            show_working_hours_live(frm);
        }
    },
    employee: function(frm) {
        // Attendance status starts as Absent until employee checkin is created
    },
    in_time: function(frm) {
        // User explicitly changed in_time — recalculate and save to doc
        calculate_and_set_working_hours(frm);
    },
    out_time: function(frm) {
        // User explicitly changed out_time — recalculate and save to doc
        calculate_and_set_working_hours(frm);
    }
});

function sync_times_from_child_checkins(frm) {
    const rows = frm.doc.employee_checkin || [];
    const checkin_names = rows.map(r => r.checkin).filter(Boolean);
    if (!checkin_names.length) return;

    frappe.db.get_list('Employee Checkin', {
        filters: {'name': ['in', checkin_names]},
        fields: ['name', 'time'],
        order_by: 'time asc',
        limit: 500
    }).then(records => {
        if (!records || !records.length) return;
        const valid_times = records.map(r => r.time).filter(Boolean);
        if (!valid_times.length) return;

        const first_time = valid_times[0];
        const last_time = valid_times[valid_times.length - 1];

        frm.set_value('in_time', first_time);
        frm.set_value('out_time', last_time);

        if (first_time === last_time) {
            frm.set_value('working_hours', '00:00:00');
            if (frm.doc.status !== "On Leave") {
                frm.set_value('status', 'Absent');
            }
        } else {
            const formatted = get_duration_hms(moment(first_time), moment(last_time));
            frm.set_value('working_hours', formatted);
            calculate_and_set_working_hours(frm);
        }
    });
}

/**
 * Called only when user changes in_time / out_time.
 * Uses frm.set_value() so the value is properly saved on next Save.
 */
function calculate_and_set_working_hours(frm) {
    // When in_time and out_time are identical (e.g. only one check-in record)
    if (frm.doc.in_time && frm.doc.out_time && frm.doc.in_time === frm.doc.out_time) {
        if (frm.doc.working_hours !== "00:00:00") {
            frm.set_value('working_hours', "00:00:00");
        }
        if (frm.doc.status !== "On Leave" && frm.doc.status !== "Absent") {
            frm.set_value('status', 'Absent');
        }
        return;
    }

    // On Leave: keep status as-is, do NOT check working_hours condition
    if (frm.doc.status === "On Leave") {
        if (frm.doc.in_time && frm.doc.out_time) {
            const in_time = moment(frm.doc.in_time);
            const out_time = moment(frm.doc.out_time);
            if (out_time.isSameOrAfter(in_time)) {
                const formatted = get_duration_hms(in_time, out_time);
                if (frm.doc.working_hours !== formatted) {
                    frm.set_value('working_hours', formatted);
                }
            }
        }
        return;
    }

    // If in_time or out_time not present -> update status = Absent
    if (!frm.doc.in_time || !frm.doc.out_time) {
        if (frm.doc.status !== "On Leave" && frm.doc.status !== "Absent") {
            frm.set_value('status', 'Absent');
        }
        if (frm.doc.working_hours && frm.doc.working_hours !== "00:00:00") {
            frm.set_value('working_hours', '00:00:00');
        }
        return;
    }

    const in_time = moment(frm.doc.in_time);
    const out_time = moment(frm.doc.out_time);

    if (!out_time.isSameOrAfter(in_time)) {
        if (frm.doc.status !== "On Leave" && frm.doc.status !== "Absent") {
            frm.set_value('status', 'Absent');
        }
        return;
    }

    const diffSeconds = out_time.diff(in_time, 'seconds');
    const formatted = get_duration_hms(in_time, out_time);
    if (frm.doc.working_hours !== formatted) {
        frm.set_value('working_hours', formatted);
    }

    // Update status based on working_hours:
    // working_hours < 5 hr                 → Absent
    // working_hours in between 5 to 8.44 hr → Half Day
    // working_hours >= 8:45 hr             → Present
    if (frm.doc.status !== "On Leave") {
        let newStatus = "Present";
        if (diffSeconds < 5 * 3600) {
            newStatus = "Absent";
        } else if (diffSeconds < (8 * 3600 + 45 * 60)) {
            newStatus = "Half Day";
        } else {
            newStatus = "Present";
        }
        if (frm.doc.status !== newStatus) {
            frm.set_value('status', newStatus);
        }
    }
}

/**
 * Called on form refresh.
 * Only updates the displayed value in the field widget, does NOT
 * call frm.set_value(), so the form stays clean (no "Not Saved").
 */
function show_working_hours_live(frm) {
    if (!frm.doc.in_time || !frm.doc.out_time) return;

    if (frm.doc.in_time === frm.doc.out_time) {
        if (frm.doc.working_hours !== "00:00:00") {
            frm.doc.working_hours = "00:00:00";
            frm.refresh_field('working_hours');
        }
        return;
    }

    const in_time = moment(frm.doc.in_time);
    const out_time = moment(frm.doc.out_time);

    if (!out_time.isSameOrAfter(in_time)) return;

    const formatted = get_duration_hms(in_time, out_time);

    // Update the internal doc value silently (no dirty flag)
    frm.doc.working_hours = formatted;

    // Refresh only the field widget display — does NOT mark form dirty
    frm.refresh_field('working_hours');
}

function get_duration_hms(in_moment, out_moment) {
    const diffSeconds = out_moment.diff(in_moment, 'seconds');
    const h = String(Math.floor(diffSeconds / 3600)).padStart(2, '0');
    const m = String(Math.floor((diffSeconds % 3600) / 60)).padStart(2, '0');
    const s = String(diffSeconds % 60).padStart(2, '0');
    return `${h}:${m}:${s}`;
}

