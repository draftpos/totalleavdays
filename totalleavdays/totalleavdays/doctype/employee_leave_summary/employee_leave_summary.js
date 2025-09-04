frappe.ui.form.on('Employee Leave Summary', {
    refresh: function(frm) {
        // Add update button
        frm.add_custom_button(__('Update Leave Summary'), function() {
            update_leave_summary(frm);
        }).addClass('btn-primary');
        
        // Add bulk update button for all employees
        frm.add_custom_button(__('Bulk Update All Employees'), function() {
            bulk_update_all_employees(frm);
        }).addClass('btn-info');
        
        // If document is new, auto-fetch data when employee is selected
        if (frm.is_new() && frm.doc.employee && frm.doc.leave_period) {
            update_leave_summary(frm);
        }
    },

    employee: function(frm) {
        if (frm.doc.employee && frm.doc.leave_period) {
            update_leave_summary(frm);
        }
    },

    leave_period: function(frm) {
        if (frm.doc.employee && frm.doc.leave_period) {
            update_leave_summary(frm);
        }
    }
});

function update_leave_summary(frm) {
    if (!frm.doc.employee || !frm.doc.leave_period) {
        frappe.msgprint(__('Please select Employee and Leave Period first'));
        return;
    }
    
    frappe.call({
        method: 'totalleavdays.totalleavdays.doctype.employee_leave_summary.employee_leave_summary.update_employee_leave_summary',
        args: {
            employee: frm.doc.employee,
            leave_period: frm.doc.leave_period,
            docname: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Updating leave summary...'),
        callback: function(r) {
            if (r.message) {
                frm.refresh();
                frappe.msgprint({
                    title: __('Success'),
                    message: __('Leave summary updated successfully'),
                    indicator: 'green'
                });
            }
        }
    });
}

function bulk_update_all_employees(frm) {
    frappe.confirm(
        __('This will update leave summaries for all active employees. Continue?'),
        function() {
            frappe.call({
                method: 'totalleavdays.totalleavdays.doctype.employee_leave_summary.employee_leave_summary.bulk_update_all_employees',
                args: {
                    leave_period: frm.doc.leave_period
                },
                freeze: true,
                freeze_message: __('Updating all employees...'),
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('Success'),
                            message: __('Updated leave summaries for {} employees', [r.message]),
                            indicator: 'green'
                        });
                    }
                }
            });
        }
    );
}