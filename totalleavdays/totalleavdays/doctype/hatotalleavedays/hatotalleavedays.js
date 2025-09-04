frappe.ui.form.on('HatotalLeaveDays', {
    onload: function(frm) {
        setup_date_calculation(frm);
    },

    refresh: function(frm) {
        if (frm.doc.employee) {
            load_all_leave_balances(frm);
        }
        
        // Add custom buttons
        if(!frm.is_new()) {
            frm.add_custom_button(__('Refresh Leave Balance'), function() {
                load_all_leave_balances(frm);
            });
            
            frm.add_custom_button(__('View All Leaves'), function() {
                view_employee_leaves(frm);
            });
        }
        
        // Add bulk fetch button
        frm.add_custom_button(__('Bulk Fetch Employees'), function() {
            show_bulk_fetch_dialog(frm);
        }).addClass('btn-info');
        
        // Add approve/reject buttons for managers
        if (frm.doc.status === 'Draft' && frappe.user.has_role('HR Manager')) {
            frm.add_custom_button(__('Approve'), function() {
                approve_leave(frm);
            }).addClass('btn-primary');
            
            frm.add_custom_button(__('Reject'), function() {
                reject_leave(frm);
            }).addClass('btn-danger');
        }
    },

    employee: function(frm) {
        if (frm.doc.employee) {
            frappe.model.with_doc('Employee', frm.doc.employee, function() {
                var employee = frappe.model.get_doc('Employee', frm.doc.employee);
                frm.set_value('employee_name', employee.employee_name);
            });
            
            load_all_leave_balances(frm);
        }
    },

    leave_type: function(frm) {
        // When leave type changes, validate against that specific type's balance
        if (frm.doc.employee && frm.doc.leave_type) {
            validate_specific_leave_balance(frm);
        }
    },

    from_date: function(frm) {
        calculate_leave_days(frm);
    },

    to_date: function(frm) {
        calculate_leave_days(frm);
    },

    half_day: function(frm) {
        calculate_leave_days(frm);
    },

    half_day_date: function(frm) {
        calculate_leave_days(frm);
    },

    validate: function(frm) {
        // Validate against the specific leave type's balance
        if (frm.doc.leave_days > 0 && frm.doc.leave_type) {
            validate_specific_leave_balance(frm, true);
        }
        
        if (frm.doc.from_date && frm.doc.to_date && frm.doc.from_date > frm.doc.to_date) {
            frappe.msgprint(__('From Date cannot be after To Date'));
            frappe.validated = false;
        }
    }
});

// NEW FUNCTION: Load all leave balances for the employee
function load_all_leave_balances(frm) {
    if (frm.doc.employee) {
        frappe.call({
            method: 'totalleavdays.totalleavdays.doctype.hatotalleavedays.hatotalleavedays.get_all_leave_balances',
            args: {
                employee: frm.doc.employee,
                leave_period: frm.doc.leave_period
            },
            callback: function(r) {
                if (r.message) {
                    update_leave_totals(frm, r.message);
                    render_leave_breakdown(frm, r.message.breakdown);
                }
            }
        });
    }
}

// NEW FUNCTION: Update total leave values
function update_leave_totals(frm, data) {
    frm.set_value('total_allocated_days', data.total_allocated);
    frm.set_value('total_used_days', data.total_used);
    frm.set_value('total_remaining_days', data.total_remaining);
}

// NEW FUNCTION: Render leave breakdown table
function render_leave_breakdown(frm, breakdown) {
    let html = `
        <div class="leave-breakdown-table">
            <table class="table table-bordered" style="width: 100%; font-size: 12px;">
                <thead>
                    <tr style="background-color: #f5f5f5;">
                        <th>Leave Type</th>
                        <th>Allocated</th>
                        <th>Used</th>
                        <th>Remaining</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    breakdown.forEach(leave => {
        const status = leave.remaining_days > 0 ? 'Available' : 'Exhausted';
        const rowClass = leave.remaining_days <= 0 ? 'text-danger' : '';
        
        html += `
            <tr class="${rowClass}">
                <td><strong>${leave.leave_type}</strong></td>
                <td>${leave.allocated_days}</td>
                <td>${leave.used_days}</td>
                <td><strong>${leave.remaining_days}</strong></td>
                <td>${status}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    frm.fields_dict.leave_breakdown.$wrapper.html(html);
}

// NEW FUNCTION: Validate specific leave type balance
function validate_specific_leave_balance(frm, showError = false) {
    if (frm.doc.employee && frm.doc.leave_type) {
        frappe.call({
            method: 'totalleavdays.totalleavdays.doctype.hatotalleavedays.hatotalleavedays.get_leave_type_balance',
            args: {
                employee: frm.doc.employee,
                leave_type: frm.doc.leave_type,
                leave_period: frm.doc.leave_period
            },
            callback: function(r) {
                if (r.message && showError) {
                    const remaining = r.message.remaining_days;
                    if (frm.doc.leave_days > remaining) {
                        frappe.msgprint({
                            title: __('Insufficient Leave Balance'),
                            message: __(`You only have ${remaining} days remaining for ${frm.doc.leave_type} leave`),
                            indicator: 'red'
                        });
                        frappe.validated = false;
                    }
                }
            }
        });
    }
}


function setup_date_calculation(frm) {
    if (!frm.doc.from_date) {
        frm.set_value('from_date', frappe.datetime.get_today());
    }
    if (!frm.doc.to_date) {
        frm.set_value('to_date', frappe.datetime.get_today());
    }
}

function calculate_leave_days(frm) {
    if (frm.doc.from_date && frm.doc.to_date) {
        frappe.call({
            method: 'totalleavdays.totalleavdays.doctype.hatotalleavedays.hatotalleavedays.calculate_leave_days',
            args: {
                from_date: frm.doc.from_date,
                to_date: frm.doc.to_date,
                half_day: frm.doc.half_day,
                half_day_date: frm.doc.half_day_date
            },
            callback: function(r) {
                if (r.message) {
                    frm.set_value('leave_days', r.message.leave_days);
                }
            }
        });
    }
}

function load_allocation_details(frm) {
    frappe.call({
        method: 'totalleavdays.totalleavdays.doctype.hatotalleavedays.hatotalleavedays.get_leave_balance',
        args: {
            employee: frm.doc.employee,
            leave_type: frm.doc.leave_type
        },
        callback: function(r) {
            if (r.message) {
                frm.set_value('allocated_days', r.message.allocated_days || 0);
                frm.set_value('used_days', r.message.used_days || 0);
                frm.set_value('remaining_days', r.message.remaining_days || 0);
            }
        }
    });
}

function show_leave_balance(frm) {
    frappe.call({
        method: 'totalleavdays.totalleavdays.doctype.hatotalleavedays.hatotalleavedays.get_leave_balance',
        args: {
            employee: frm.doc.employee,
            leave_type: frm.doc.leave_type
        },
        callback: function(r) {
            if (r.message) {
                frappe.msgprint({
                    title: __('Leave Balance'),
                    message: __(`
                        <b>Leave Balance for ${frm.doc.employee_name}</b><br>
                        Leave Type: ${frm.doc.leave_type}<br>
                        Allocated: ${r.message.allocated_days} days<br>
                        Used: ${r.message.used_days} days<br>
                        Remaining: ${r.message.remaining_days} days
                    `),
                    indicator: 'green'
                });
            }
        }
    });
}

function view_employee_leaves(frm) {
    // Open list view filtered by employee
    frappe.set_route('List', 'HatotalLeaveDays', {
        employee: frm.doc.employee
    });
}

function approve_leave(frm) {
    frappe.call({
        method: 'totalleavdays.totalleavdays.doctype.hatotalleavedays.hatotalleavedays.approve_leave',
        args: {
            docname: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frm.reload_doc();
                frappe.msgprint(__('Leave approved successfully'));
            }
        }
    });
}

function reject_leave(frm) {
    frappe.prompt(__('Reason for rejection:'), 
        function(values) {
            frappe.call({
                method: 'totalleavdays.totalleavdays.doctype.hatotalleavedays.hatotalleavedays.reject_leave',
                args: {
                    docname: frm.doc.name,
                    reason: values.value
                },
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                        frappe.msgprint(__('Leave rejected'));
                    }
                }
            });
        },
        __('Reject Leave'),
        __('Reason')
    );
}









// NEW FUNCTION: Show bulk fetch dialog
function show_bulk_fetch_dialog(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __('Bulk Fetch Employees'),
        fields: [
            {
                fieldname: 'number_of_employees',
                fieldtype: 'Int',
                label: __('Number of Employees'),
                reqd: 1,
                description: __('Enter how many employees to fetch for leave data')
            },
            {
                fieldname: 'leave_type',
                fieldtype: 'Link',
                label: __('Leave Type'),
                options: 'Leave Type',
                reqd: 1
            },
            {
                fieldname: 'fetch_method',
                fieldtype: 'Select',
                label: __('Fetch Method'),
                options: [
                    {value: 'recent', label: __('Most Recent Employees')},
                    {value: 'active', label: __('Active Employees')},
                    {value: 'random', label: __('Random Selection')}
                ],
                default: 'active'
            }
        ],
        primary_action: function(values) {
            bulk_fetch_employees(frm, values);
            dialog.hide();
        },
        primary_action_label: __('Fetch Employees')
    });
    
    dialog.show();
}

// NEW FUNCTION: Bulk fetch employees
function bulk_fetch_employees(frm, values) {
    frappe.call({
        method: 'totalleavdays.totalleavdays.doctype.hatotalleavedays.hatotalleavedays.bulk_fetch_employees',
        args: {
            number_of_employees: values.number_of_employees,
            leave_type: values.leave_type,
            fetch_method: values.fetch_method
        },
        freeze: true,
        freeze_message: __('Fetching employee data...'),
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                show_bulk_results(frm, r.message);
            } else {
                frappe.msgprint(__('No employees found or no leave data available'));
            }
        }
    });
}

// NEW FUNCTION: Show bulk fetch results
function show_bulk_results(frm, employees_data) {
    let message = `
        <h4>${__('Bulk Fetch Results')}</h4>
        <p>${__('Found data for %s employees', [employees_data.length])}</p>
        <div style="max-height: 300px; overflow-y: auto;">
        <table class="table table-bordered" style="width: 100%; font-size: 12px;">
            <thead>
                <tr>
                    <th>${__('Employee')}</th>
                    <th>${__('Allocated')}</th>
                    <th>${__('Used')}</th>
                    <th>${__('Remaining')}</th>
                    <th>${__('Status')}</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    employees_data.forEach(emp => {
        message += `
            <tr>
                <td>${emp.employee_name} (${emp.employee})</td>
                <td>${emp.allocated_days}</td>
                <td>${emp.used_days}</td>
                <td>${emp.remaining_days}</td>
                <td>${emp.status}</td>
            </tr>
        `;
    });
    
    message += `</tbody></table></div>`;
    
    frappe.msgprint({
        title: __('Bulk Fetch Results'),
        message: message,
        indicator: 'blue',
        wide: true
    });
    
    // Option to create multiple leave records
    frappe.confirm(
        __('Do you want to create leave records for these employees?'),
        function() {
            create_bulk_leave_records(frm, employees_data);
        },
        function() {
            // Cancel action
        }
    );
}

// NEW FUNCTION: Create bulk leave records
function create_bulk_leave_records(frm, employees_data) {
    frappe.call({
        method: 'totalleavdays.totalleavdays.doctype.hatotalleavedays.hatotalleavedays.create_bulk_leave_records',
        args: {
            employees_data: employees_data,
            leave_type: employees_data[0].leave_type // Assuming all have same leave type
        },
        freeze: true,
        freeze_message: __('Creating leave records...'),
        callback: function(r) {
            if (r.message) {
                frappe.msgprint({
                    title: __('Success'),
                    message: __('Created %s leave records successfully', [r.message]),
                    indicator: 'green'
                });
                
                // Refresh the list view
                frappe.set_route('List', 'HatotalLeaveDays');
            }
        }
    });
}




























// frappe.pages['leave-dashboard'].on_page_load = function(wrapper) {
//     var page = frappe.ui.make_app_page({
//         parent: wrapper,
//         title: 'Leave Dashboard',
//         single_column: true
//     });
    

//     page.add_menu_item(__('Refresh'), function() {
//         load_dashboard_data(page);
//     });
    
//     load_dashboard_data(page);
// }

// function load_dashboard_data(page) {
//     frappe.call({
//         method: 'totalleavdays.totalleavdays.doctype.hatotalleavedays.hatotalleavedays.get_employee_leave_dashboard',
//         callback: function(r) {
//             if (r.message) {
//                 render_dashboard(page, r.message);
//             }
//         }
//     });
// }

// function render_dashboard(page, data) {
//     let content = `
//         <div class="dashboard-header">
//             <h3>Employee Leave Dashboard</h3>
//             <p>Total Active Employees: ${data.length}</p>
//         </div>
//         <div class="row">
//     `;
    
//     data.forEach(emp => {
//         content += `
//             <div class="col-sm-6 col-md-4" style="margin-bottom: 20px;">
//                 <div class="card">
//                     <div class="card-body">
//                         <h5 class="card-title">${emp.employee_name}</h5>
//                         <h6 class="card-subtitle mb-2 text-muted">${emp.designation || 'N/A'} - ${emp.department || 'N/A'}</h6>
//                         <div class="leave-summary">
//         `;
        
//         emp.leave_summary.forEach(leave => {
//             content += `
//                 <div class="leave-item">
//                     <strong>${leave.leave_type}:</strong>
//                     ${leave.remaining_days}/${leave.allocated_days} days remaining
//                     <div class="progress" style="height: 5px; margin: 5px 0;">
//                         <div class="progress-bar" style="width: ${(leave.remaining_days/leave.allocated_days)*100}%"></div>
//                     </div>
//                 </div>
//             `;
//         });
        
//         content += `
//                         </div>
//                     </div>
//                 </div>
//             </div>
//         `;
//     });
    
//     content += `</div>`;
    
//     $(page.body).html(content);
// }