// ======================================================================
// Employee Checkin List View Custom Actions
// Integrated with at_biometric_integration.api
// ======================================================================

frappe.listview_settings['Employee Checkin'] = {
    onload: function (listview) {
        // Allow only authorized roles, Allow Administrator always
         
        if (frappe.session.user !== "Administrator") {
            // Allow only authorized roles
            const allowed_roles = [
                'System Manager',
                'HR Manager',
                'Biometric Integration Manager',
                'Workspace Manager',
                'HR User',
                'Dashboard Manager',
                'Project Manager',
                'Report Manager'
            ];

            if (!allowed_roles.some(role => frappe.user.has_role(role))) {
                return;
            }
        }


        // Check if any Biometric Device Settings exist before adding buttons
        frappe.db.get_value('Biometric Device Settings', {}, 'name').then(res => {
            if (!res || !res.message || !res.message.name) return;

            // ------------------ SYNC BIOMETRIC DATA ------------------
            listview.page.add_inner_button(__('Sync Biometric Data'), () => {
                show_progress_msg('Syncing biometric data in background...');

                frappe.call({
                    method: "at_biometric_integration.api.fetch_and_upload_attendance",
                    freeze: true,
                    callback: function (r) {
                        frappe.hide_msgprint();
                        if (r.message) show_result_message(r.message);
                    },
                    error: function (err) {
                        frappe.hide_msgprint();
                        frappe.msgprint(__('❌ Error syncing biometric data.'));
                        console.error(err);
                    }
                });
            }, "Tools");

            // ------------------ MARK ATTENDANCE ------------------
            listview.page.add_inner_button(__('Mark Attendance'), () => {
                show_progress_msg('Marking attendance from check-ins...');

                frappe.call({
                    method: "at_biometric_integration.api.mark_attendance",
                    freeze: true,
                    callback: function (r) {
                        frappe.hide_msgprint();
                        frappe.msgprint(__(r.message.message || r.message || 'Process completed.'));
                    },
                    error: function (err) {
                        frappe.hide_msgprint();
                        frappe.msgprint(__('❌ Error marking attendance.'));
                        console.error(err);
                    }
                });
            }, "Tools");

            // ------------------ IMPORT CHECKINS ------------------
            listview.page.add_inner_button('Import Checkins', () => {
                const $input = $('<input type="file" accept=".csv,.xls,.xlsx" style="display:none">');
                $('body').append($input);

                $input.on('change', function (e) {
                    const file = e.target.files[0];
                    if (!file) return;

                    const ext = file.name.split('.').pop().toLowerCase();
                    const reader = new FileReader();

                    if (['xls', 'xlsx'].includes(ext)) {
                        reader.onload = function (e) {
                            const data = new Uint8Array(e.target.result);
                            const workbook = XLSX.read(data, { type: 'array' });
                            const sheet = workbook.Sheets[workbook.SheetNames[0]];
                            const csvData = XLSX.utils.sheet_to_csv(sheet);
                            parseCSVAndImport(csvData);
                        };
                        reader.readAsArrayBuffer(file);
                    } else {
                        reader.onload = function (e) {
                            parseCSVAndImport(e.target.result);
                        };
                        reader.readAsText(file);
                    }
                });

                $input.click();
            }, "Tools");
        });
    }
};

// ======================================================================
// HELPER FUNCTIONS
// ======================================================================

function show_progress_msg(msg) {
    const html = `
        <div>
            <b>Please Wait:</b> ${msg}
            <br><br>
            <div class="progress" style="height: 10px;">
                <div class="progress-bar progress-bar-striped progress-bar-animated"
                     role="progressbar" style="width: 100%"></div>
            </div>
        </div>`;
    frappe.msgprint({ title: __('Processing'), message: html, indicator: 'blue' });
}

function show_result_message(data) {
    let msg = '';
    if (data.success && data.success.length > 0) {
        msg += `<b>✅ Success:</b><br>${data.success.join('<br>')}<br><br>`;
    }
    if (data.errors && data.errors.length > 0) {
        msg += `<b>❌ Errors:</b><br>${data.errors.join('<br>')}`;
    }
    frappe.msgprint(__(msg || 'No updates found.'));
}

// ======================================================================
// CSV / XLSX IMPORT FUNCTIONALITY
// ======================================================================

function parseCSVAndImport(csvText) {
    frappe.confirm(
        'This will import Employee Checkins from the selected file. Continue?',
        () => {
            const rows = csvText.split(/\r?\n/).map(r => r.trim()).filter(r => r);
            const headerIdx = rows.findIndex(r => r.startsWith('No'));
            if (headerIdx === -1) {
                frappe.msgprint('❌ Could not find header row (must start with "No.")');
                return;
            }

            const tableRows = rows.slice(headerIdx);
            const dataRows = tableRows.map(r => r.split(/[\t,]+/));
            const headers = dataRows.shift().map(h => h.trim());

            const dateIdx = headers.indexOf('Date');
            const timeIdx = headers.indexOf('Time');
            const empIdIdx = headers.indexOf('Employee ID');
            const punchIdx = headers.indexOf('Punch State');

            if ([dateIdx, timeIdx, empIdIdx, punchIdx].includes(-1)) {
                frappe.msgprint('❌ Missing required columns: Date, Time, Employee ID, Punch State');
                return;
            }

            frappe.show_progress('Importing Checkins...', 0, dataRows.length, 'Processing records');
            let count = 0;

            const processRow = (i) => {
                if (i >= dataRows.length) {
                    frappe.hide_progress();
                    frappe.msgprint(`✅ Import completed. ${count} check-ins created.`);
                    return;
                }

                const r = dataRows[i].map(v => v.trim());
                const deviceId = r[empIdIdx];
                const date = r[dateIdx];
                const time = r[timeIdx];
                const punch = r[punchIdx];

                if (!deviceId || !date || !time) return processRow(i + 1);

                frappe.db.get_value('Employee', { attendance_device_id: deviceId }, 'name')
                    .then(emp => {
                        if (!emp || !emp.message || !emp.message.name) {
                            console.warn(`⚠️ Employee not found for device ID: ${deviceId}`);
                            return processRow(i + 1);
                        }

                        let formattedDatetime;
                        try {
                            const [day, month, year] = date.split('-');
                            formattedDatetime = `${year}-${month}-${day} ${time}`;
                        } catch {
                            console.error('⚠️ Invalid date format:', date);
                            return processRow(i + 1);
                        }

                        frappe.call({
                            method: 'frappe.client.insert',
                            args: {
                                doc: {
                                    doctype: 'Employee Checkin',
                                    employee: emp.message.name,
                                    time: formattedDatetime,
                                    log_type: punch == '255' ? 'IN' : 'OUT',
                                    device_id: deviceId,
                                    latitude: "0.0",
                                    longitude: "0.0",
                                    skip_auto_attendance: 0
                                }
                            },
                            callback: function (r) {
                                if (!r.exc) count++;
                                frappe.show_progress('Importing Checkins...', i + 1, dataRows.length);
                                processRow(i + 1);
                            },
                            error: function (err) {
                                console.error('Insert error:', err);
                                processRow(i + 1);
                            }
                        });
                    });
            };
            processRow(0);
        }
    );
}

// Load XLSX library for Excel parsing
frappe.require('https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js');
