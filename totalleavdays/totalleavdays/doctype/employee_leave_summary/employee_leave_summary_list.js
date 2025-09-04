frappe.listview_settings['Employee Leave Summary'] = {
    add_fields: ["employee", "employee_name", "total_allocated_days", "total_used_days", "total_remaining_days", "last_updated"],
    
    get_indicator: function(doc) {
        var utilization = (doc.total_used_days / doc.total_allocated_days) * 100;
        
        if (utilization > 80) {
            return [__("High Utilization"), "red", "status,=,Active"];
        } else if (utilization > 50) {
            return [__("Medium Utilization"), "orange", "status,=,Active"];
        } else {
            return [__("Low Utilization"), "green", "status,=,Active"];
        }
    },
    
    onload: function(listview) {
        // Add bulk update button to list view
        listview.page.add_menu_item(__('Bulk Update All'), function() {
            frappe.prompt({
                fieldtype: 'Link',
                label: __('Leave Period'),
                fieldname: 'leave_period',
                options: 'Leave Period',
                reqd: 1
            }, function(values) {
                frappe.call({
                    method: 'totalleavdays.totalleavdays.doctype.employee_leave_summary.employee_leave_summary.bulk_update_all_employees',
                    args: {
                        leave_period: values.leave_period
                    },
                    freeze: true,
                    callback: function(r) {
                        frappe.msgprint(__('Updated {0} employee summaries', [r.message]));
                        listview.refresh();
                    }
                });
            }, __('Select Leave Period'), __('Update'));
        });
    }
};