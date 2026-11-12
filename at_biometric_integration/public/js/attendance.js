frappe.ui.form.on('Attendance', {
    refresh: function(frm) {
        // Only display live calculation, do NOT dirty the form on refresh
        show_working_hours_live(frm);
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

/**
 * Called only when user changes in_time / out_time.
 * Uses frm.set_value() so the value is properly saved on next Save.
 */
function calculate_and_set_working_hours(frm) {
    if (!frm.doc.in_time || !frm.doc.out_time) return;

    const in_time = moment(frm.doc.in_time);
    const out_time = moment(frm.doc.out_time);

    if (!out_time.isSameOrAfter(in_time)) return;

    const formatted = get_duration_hms(in_time, out_time);
    if (frm.doc.working_hours !== formatted) {
        frm.set_value('working_hours', formatted);
    }
}

/**
 * Called on form refresh.
 * Only updates the displayed value in the field widget, does NOT
 * call frm.set_value(), so the form stays clean (no "Not Saved").
 */
function show_working_hours_live(frm) {
    if (!frm.doc.in_time || !frm.doc.out_time) return;

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

