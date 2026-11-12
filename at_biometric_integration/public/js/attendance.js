frappe.ui.form.on('Attendance', {
    refresh: function(frm) {
        calculate_working_hours_live(frm);
    },
    in_time: function(frm) {
        calculate_working_hours_live(frm);
    },
    out_time: function(frm) {
        calculate_working_hours_live(frm);
    }
});

function calculate_working_hours_live(frm) {
    if (frm.doc.in_time && frm.doc.out_time) {
        const in_time = moment(frm.doc.in_time);
        const out_time = moment(frm.doc.out_time);
        
        if (out_time.isSameOrAfter(in_time)) {
            const diffSeconds = out_time.diff(in_time, 'seconds');
            const hours = String(Math.floor(diffSeconds / 3600)).padStart(2, '0');
            const minutes = String(Math.floor((diffSeconds % 3600) / 60)).padStart(2, '0');
            const seconds = String(diffSeconds % 60).padStart(2, '0');
            const formatted = `${hours}:${minutes}:${seconds}`;
            
            if (frm.doc.working_hours !== formatted) {
                frm.set_value('working_hours', formatted);
            }
        }
    }
}

