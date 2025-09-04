// This will be loaded whenever Payroll Entry form is opened
frappe.ui.form.on('Payroll Entry', {
    refresh: function(frm) {
        console.log('Payroll Entry form loaded - from totalleavdays app');
        console.log('Form is new?', frm.is_new());
        
        try {
            // Run automatic leave summary update when form loads
            auto_update_leave_summaries(frm);
        } catch (error) {
            console.error('Error in auto_update_leave_summaries:', error);
        }
        
    }
});

// Function to automatically update leave summaries without user interaction
function auto_update_leave_summaries(frm) {
    console.log('Auto-update function called');
    
    // Check if frm is valid
    if (!frm || !frm.doc) {
        console.error('Form is not valid');
        return;
    }
    
    // Only run for new Payroll Entries or based on your business logic
    if (frm.is_new()) {
        console.log('Auto-updating leave summaries for new Payroll Entry');
        
        frappe.call({
            method: 'totalleavdays.totalleavdays.doctype.employee_leave_summary.employee_leave_summary.get_latest_leave_period',
            callback: function(r) {
                console.log('get_latest_leave_period response:', r);
                
                if (r.message) {
                    const leave_period = r.message;
                    console.log('Latest leave period:', leave_period);
                    
                    frappe.call({
                        method: 'totalleavdays.totalleavdays.doctype.employee_leave_summary.employee_leave_summary.bulk_update_all_employees',
                        args: {
                            leave_period: leave_period
                        },
                        callback: function(r) {
                            console.log('bulk_update_all_employees response:', r);
                            
                            if (r.message) {
                                console.log('Auto-updated leave summaries for', r.message, 'employees');
                                // Optional: Show a subtle notification instead of intrusive popup
                                frappe.show_alert({
                                    message: __('Auto-updated leave summaries for {} employees', [r.message]),
                                    indicator: 'green'
                                }, 5);
                            }
                        },
                        error: function(err) {
                            console.error('Error in bulk_update_all_employees:', err);
                        }
                    });
                }
            },
            error: function(err) {
                console.error('Error in get_latest_leave_period:', err);
            }
        });
    } else {
        console.log('Not a new form, skipping auto-update');
    }
}