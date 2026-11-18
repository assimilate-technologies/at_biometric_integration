frappe.ui.form.on('Attendance', {
    refresh: function(frm) {
        // Preload the status thresholds from Attendance Settings
        load_status_thresholds();

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
    // working_hours < half_day_from (5 hr default)                  → Absent
    // working_hours half_day_from .. half_day_to (9 hr default)     → Absent-Half Day
    //   (grace window → Present, max 3 per month, applied server-side)
    // working_hours >= half_day_to                                 → Present
    // Range comes from Attendance Settings.half_day_from / half_day_to.
    if (frm.doc.status !== "On Leave") {
        if (!status_thresholds_loaded) {
            // Load the configured range first, then apply the status
            load_status_thresholds().then(() => apply_status_by_working_hours(frm, diffSeconds));
            return;
        }
        apply_status_by_working_hours(frm, diffSeconds);
    }
}

// Status thresholds in seconds. The Absent-Half Day window is bounded by
// Attendance Settings.half_day_from .. half_day_to (Time fields). When those
// are empty the Float fields min_working_hour_for_half_day / min_working_hours
// are used, then the 5 hr / 9 hr defaults (same as the server).
let full_seconds = 9 * 3600;
let floor_seconds = 5 * 3600;
let status_thresholds_loaded = false;

function time_to_seconds(value) {
    if (!value) return 0;
    const parts = String(value).split(":");
    const h = parseFloat(parts[0]) || 0;
    const m = parseFloat(parts[1]) || 0;
    const s = parseFloat(parts[2]) || 0;
    return h * 3600 + m * 60 + s;
}

function load_status_thresholds() {
    const settings = "Attendance Settings";
    return Promise.all([
        frappe.db.get_single_value(settings, "half_day_from"),
        frappe.db.get_single_value(settings, "half_day_to"),
        frappe.db.get_single_value(settings, "min_working_hour_for_half_day"),
        frappe.db.get_single_value(settings, "min_working_hours"),
    ])
        .then(([halfDayFrom, halfDayTo, minHalfDay, minWorking]) => {
            const halfDayFromSeconds = time_to_seconds(halfDayFrom);
            const halfDayToSeconds = time_to_seconds(halfDayTo);

            const fallbackFloor = parseFloat(minHalfDay);
            const fallbackFull = parseFloat(minWorking);

            floor_seconds = halfDayFromSeconds > 0
                ? halfDayFromSeconds
                : (fallbackFloor > 0 ? fallbackFloor : 5) * 3600;
            full_seconds = halfDayToSeconds > 0
                ? halfDayToSeconds
                : (fallbackFull > 0 ? fallbackFull : 9) * 3600;
        })
        .catch(() => {
            // keep defaults on error
        })
        .then(() => {
            status_thresholds_loaded = true;
            return full_seconds;
        });
}

function apply_status_by_working_hours(frm, diffSeconds) {
    const fullSeconds = full_seconds;
    const floorSeconds = floor_seconds;
    const graceStartSeconds = fullSeconds - 20 * 60; // 20-minute grace window

    let newStatus = "Present";
    if (diffSeconds < floorSeconds) {
        newStatus = "Absent";
    } else if (diffSeconds < graceStartSeconds) {
        newStatus = "Absent-Half Day";
    } else if (diffSeconds < fullSeconds) {
        // Grace window: ask server for the monthly quota status
        frappe.call({
            method: "at_biometric_integration.utils.attendance_processing.get_status_for_grace_check",
            args: {
                employee: frm.doc.employee,
                attendance_date: frm.doc.attendance_date,
                work_seconds: diffSeconds
            },
            async: false,
            callback: function(r) {
                if (r.message && frm.doc.status !== r.message) {
                    frm.set_value('status', r.message);
                }
            }
        });
        return;
    } else {
        newStatus = "Present";
    }
    if (frm.doc.status !== newStatus) {
        frm.set_value('status', newStatus);
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

