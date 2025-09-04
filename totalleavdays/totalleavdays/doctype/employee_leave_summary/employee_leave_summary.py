import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt, nowdate, now_datetime
from datetime import datetime
import json

class EmployeeLeaveSummary(Document):
    def validate(self):
        # Auto-update when saving if employee and leave period are set
        if self.employee and self.leave_period and (self.is_new() or not self.leave_types):
            self.update_summary_data()
    
    def update_summary_data(self):
        """Update the leave summary data for this employee"""
        summary_data = get_employee_leave_summary_data(self.employee, self.leave_period)
        
        self.total_allocated_days = summary_data["total_allocated"]
        self.total_used_days = summary_data["total_used"]
        self.total_remaining_days = summary_data["total_remaining"]
        self.last_updated = now_datetime()
        
        # Store leave types for searching
        leave_types_list = [lt["leave_type"] for lt in summary_data["breakdown"]]
        self.leave_types = ", ".join(leave_types_list)
        
        # Create HTML breakdown
        self.create_breakdown_html(summary_data["breakdown"])
    
    def create_breakdown_html(self, breakdown):
        """Create HTML table for leave breakdown"""
        html = """
        <div class="leave-breakdown">
            <h4>Leave Breakdown by Type</h4>
            <table class="table table-bordered" style="width: 100%; font-size: 12px;">
                <thead>
                    <tr style="background-color: #f5f5f5;">
                        <th>Leave Type</th>
                        <th>Allocated</th>
                        <th>Used</th>
                        <th>Remaining</th>
                        <th>Utilization %</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for leave in breakdown:
            utilization = (leave["used"] / leave["allocated"] * 100) if leave["allocated"] > 0 else 0
            utilization_class = "text-danger" if utilization > 80 else "text-warning" if utilization > 50 else "text-success"
            
            html += f"""
                <tr>
                    <td><strong>{leave['leave_type']}</strong></td>
                    <td>{leave['allocated']}</td>
                    <td>{leave['used']}</td>
                    <td><strong>{leave['remaining']}</strong></td>
                    <td class="{utilization_class}">{utilization:.1f}%</td>
                </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        """
        
        self.leave_breakdown = html

@frappe.whitelist()
def search_employee_summaries(search_term=None, company=None, department=None, leave_period=None, leave_type=None):
    """Search employee summaries with various filters"""
    filters = {}
    
    if company:
        filters["company"] = company
    
    if department:
        filters["department"] = ["like", f"%{department}%"]
    
    if leave_period:
        filters["leave_period"] = leave_period
    
    if leave_type:
        filters["leave_types"] = ["like", f"%{leave_type}%"]
    
    if search_term:
        # Search in employee_name, department, or leave_types
        or_filters = {
            "employee_name": ["like", f"%{search_term}%"],
            "department": ["like", f"%{search_term}%"],
            "leave_types": ["like", f"%{search_term}%"]
        }
    else:
        or_filters = None
    
    results = frappe.get_all("Employee Leave Summary",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "employee", "employee_name", "department", "company", 
                "leave_period", "total_allocated_days", "total_used_days", 
                "total_remaining_days", "leave_types", "last_updated"],
        order_by="employee_name"
    )
    
    return results

@frappe.whitelist()
def get_employees_by_leave_type(leave_type, leave_period=None):
    """Get all employees who have a specific leave type"""
    filters = {"leave_types": ["like", f"%{leave_type}%"]}
    
    if leave_period:
        filters["leave_period"] = leave_period
    
    employees = frappe.get_all("Employee Leave Summary",
        filters=filters,
        fields=["employee", "employee_name", "department", "total_allocated_days", 
                "total_used_days", "total_remaining_days"],
        order_by="employee_name"
    )
    
    return employees

@frappe.whitelist()
def get_departments_with_leave_type(leave_type, leave_period=None):
    """Get departments that have employees with a specific leave type"""
    filters = {"leave_types": ["like", f"%{leave_type}%"]}
    
    if leave_period:
        filters["leave_period"] = leave_period
    
    departments = frappe.get_all("Employee Leave Summary",
        filters=filters,
        fields=["department", "COUNT(*) as employee_count"],
        group_by="department",
        order_by="employee_count DESC"
    )
    
    return departments

# The rest of the functions remain the same as previous version...
@frappe.whitelist()
def update_employee_leave_summary(employee, leave_period, docname=None):
    """Update or create employee leave summary"""
    try:
        if docname:
            doc = frappe.get_doc("Employee Leave Summary", docname)
        else:
            existing = frappe.get_all("Employee Leave Summary",
                filters={"employee": employee, "leave_period": leave_period},
                limit=1
            )
            
            if existing:
                doc = frappe.get_doc("Employee Leave Summary", existing[0].name)
            else:
                doc = frappe.new_doc("Employee Leave Summary")
                doc.employee = employee
                doc.leave_period = leave_period
        
        doc.update_summary_data()
        doc.save()
        return True
        
    except Exception as e:
        frappe.log_error(f"Error updating leave summary for {employee}: {str(e)}")
        return False

@frappe.whitelist()
def bulk_update_all_employees(leave_period):
    """Update leave summaries for all active employees"""
    active_employees = frappe.get_all("Employee",
        filters={"status": "Active"},
        fields=["name"]
    )
    
    updated_count = 0
    
    for emp in active_employees:
        try:
            existing = frappe.get_all("Employee Leave Summary",
                filters={"employee": emp.name, "leave_period": leave_period},
                limit=1
            )
            
            if existing:
                doc = frappe.get_doc("Employee Leave Summary", existing[0].name)
            else:
                doc = frappe.new_doc("Employee Leave Summary")
                doc.employee = emp.name
                doc.leave_period = leave_period
            
            doc.update_summary_data()
            doc.save()
            updated_count += 1
            
        except Exception as e:
            frappe.log_error(f"Error updating leave summary for {emp.name}: {str(e)}")
            continue
    
    return updated_count

def get_employee_leave_summary_data(employee, leave_period):
    """Get comprehensive leave summary data for an employee"""
    period_doc = frappe.get_doc("Leave Period", leave_period)
    from_date = period_doc.from_date
    to_date = period_doc.to_date
    
    allocations = frappe.get_all("Leave Allocation",
        filters={
            "employee": employee,
            "docstatus": 1,
            "from_date": [">=", from_date],
            "to_date": ["<=", to_date]
        },
        fields=["leave_type", "total_leaves_allocated"]
    )
    
    breakdown = []
    total_allocated = 0
    total_used = 0
    
    for allocation in allocations:
        used_leaves = get_used_leaves(employee, allocation.leave_type, from_date, to_date)
        remaining = allocation.total_leaves_allocated - used_leaves
        
        breakdown.append({
            "leave_type": allocation.leave_type,
            "allocated": flt(allocation.total_leaves_allocated, 2),
            "used": flt(used_leaves, 2),
            "remaining": flt(remaining, 2)
        })
        
        total_allocated += allocation.total_leaves_allocated
        total_used += used_leaves
    
    return {
        "total_allocated": flt(total_allocated, 2),
        "total_used": flt(total_used, 2),
        "total_remaining": flt(total_allocated - total_used, 2),
        "breakdown": breakdown
    }

def get_used_leaves(employee, leave_type, from_date, to_date):
    """Get total used leaves for an employee and leave type within period"""
    used_leaves = frappe.db.sql("""
        SELECT SUM(total_leave_days) as total_used
        FROM `tabLeave Application` 
        WHERE employee = %s
        AND leave_type = %s
        AND docstatus = 1
        AND status = 'Approved'
        AND from_date >= %s
        AND to_date <= %s
    """, (employee, leave_type, from_date, to_date))
    
    return flt(used_leaves[0][0]) if used_leaves and used_leaves[0][0] else 0.0

@frappe.whitelist()
def update_employee_leave_summary(employee, leave_period, docname=None):
    """Update or create employee leave summary"""
    try:
        if docname:
            # Update existing document
            doc = frappe.get_doc("Employee Leave Summary", docname)
        else:
            # Check if summary already exists
            existing = frappe.get_all("Employee Leave Summary",
                filters={"employee": employee, "leave_period": leave_period},
                limit=1
            )
            
            if existing:
                doc = frappe.get_doc("Employee Leave Summary", existing[0].name)
            else:
                # Create new document
                doc = frappe.new_doc("Employee Leave Summary")
                doc.employee = employee
                doc.leave_period = leave_period
        
        doc.update_summary_data()
        doc.save()
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Error updating leave summary for {employee}: {str(e)}")
        return False

@frappe.whitelist()
def bulk_update_all_employees(leave_period):
    """Update leave summaries for all active employees"""
    active_employees = frappe.get_all("Employee",
        filters={"status": "Active"},
        fields=["name"]
    )
    
    updated_count = 0
    
    for emp in active_employees:
        try:
            # Check if summary already exists
            existing = frappe.get_all("Employee Leave Summary",
                filters={"employee": emp.name, "leave_period": leave_period},
                limit=1
            )
            
            if existing:
                doc = frappe.get_doc("Employee Leave Summary", existing[0].name)
            else:
                doc = frappe.new_doc("Employee Leave Summary")
                doc.employee = emp.name
                doc.leave_period = leave_period
            
            doc.update_summary_data()
            doc.save()
            updated_count += 1
            
        except Exception as e:
            frappe.log_error(f"Error updating leave summary for {emp.name}: {str(e)}")
            continue
    
    return updated_count

@frappe.whitelist()
def get_employee_leave_summary_data(employee, leave_period):
    """Get comprehensive leave summary data for an employee"""
    # Get leave period dates
    period_doc = frappe.get_doc("Leave Period", leave_period)
    from_date = period_doc.from_date
    to_date = period_doc.to_date
    
    # Get all leave allocations for this employee in the period
    allocations = frappe.get_all("Leave Allocation",
        filters={
            "employee": employee,
            "docstatus": 1,
            "from_date": [">=", from_date],
            "to_date": ["<=", to_date]
        },
        fields=["leave_type", "total_leaves_allocated"]
    )
    
    breakdown = []
    total_allocated = 0
    total_used = 0
    
    for allocation in allocations:
        used_leaves = get_used_leaves(employee, allocation.leave_type, from_date, to_date)
        remaining = allocation.total_leaves_allocated - used_leaves
        
        breakdown.append({
            "leave_type": allocation.leave_type,
            "allocated": flt(allocation.total_leaves_allocated, 2),
            "used": flt(used_leaves, 2),
            "remaining": flt(remaining, 2)
        })
        
        total_allocated += allocation.total_leaves_allocated
        total_used += used_leaves
    
    return {
        "total_allocated": flt(total_allocated, 2),
        "total_used": flt(total_used, 2),
        "total_remaining": flt(total_allocated - total_used, 2),
        "breakdown": breakdown
    }

def get_used_leaves(employee, leave_type, from_date, to_date):
    """Get total used leaves for an employee and leave type within period"""
    used_leaves = frappe.db.sql("""
        SELECT SUM(total_leave_days) as total_used
        FROM `tabLeave Application` 
        WHERE employee = %s
        AND leave_type = %s
        AND docstatus = 1
        AND status = 'Approved'
        AND from_date >= %s
        AND to_date <= %s
    """, (employee, leave_type, from_date, to_date))
    
    return flt(used_leaves[0][0]) if used_leaves and used_leaves[0][0] else 0.0

@frappe.whitelist()
def create_summaries_for_period(leave_period):
    """Create leave summaries for all employees for a given period"""
    return bulk_update_all_employees(leave_period)

@frappe.whitelist()
def get_employee_summary(employee, leave_period):
    """API to get employee summary data"""
    return get_employee_leave_summary_data(employee, leave_period)






















@frappe.whitelist()
def get_latest_leave_period():
    """Get the latest leave period by from_date"""
    try:
        latest_period = frappe.get_all("Leave Period",
            fields=["name", "from_date"],
            order_by="from_date DESC",
            limit=1
        )
        
        if latest_period:
            return latest_period[0].name
        else:
            return None
            
    except Exception as e:
        frappe.log_error(f"Error getting latest leave period: {str(e)}")
        return None

@frappe.whitelist()
def bulk_update_all_employees(leave_period):
    """Update leave summaries for all active employees"""
    active_employees = frappe.get_all("Employee",
        filters={"status": "Active"},
        fields=["name"]
    )
    
    updated_count = 0
    
    for emp in active_employees:
        try:
            # Check if summary already exists
            existing = frappe.get_all("Employee Leave Summary",
                filters={"employee": emp.name, "leave_period": leave_period},
                limit=1
            )
            
            if existing:
                doc = frappe.get_doc("Employee Leave Summary", existing[0].name)
            else:
                doc = frappe.new_doc("Employee Leave Summary")
                doc.employee = emp.name
                doc.leave_period = leave_period
            
            doc.update_summary_data()
            doc.save()
            updated_count += 1
            
        except Exception as e:
            frappe.log_error(f"Error updating leave summary for {emp.name}: {str(e)}")
            continue
    
    return updated_count

# Optional: Add automatic period detection based on payroll dates
@frappe.whitelist()
def get_leave_period_for_dates(start_date, end_date):
    """Get leave period that covers the given date range"""
    try:
        period = frappe.get_all("Leave Period",
            filters={
                "from_date": ["<=", start_date],
                "to_date": [">=", end_date]
            },
            fields=["name"],
            limit=1
        )
        
        if period:
            return period[0].name
        else:
            # Fallback to latest period if no exact match
            return get_latest_leave_period()
            
    except Exception as e:
        frappe.log_error(f"Error getting leave period for dates: {str(e)}")
        return get_latest_leave_period()



















import frappe
from frappe import _

@frappe.whitelist()
def handle_payroll_event(docname, event_type):
    """Handle events from Payroll Entry"""
    try:
        payroll_entry = frappe.get_doc('Payroll Entry', docname)
        frappe.msgprint(_('Processing payroll entry: {0}').format(docname))
        
        # Your custom logic here
        if event_type == 'process_leave_days':
            process_leave_days_for_payroll(payroll_entry)
            
        return True
    except Exception as e:
        frappe.log_error(_('Error processing payroll event'), str(e))
        return False

@frappe.whitelist()
def handle_payroll_submission(payroll_entry, company, start_date, end_date):
    """Handle payroll submission automatically"""
    try:
        frappe.logger().info(f"Payroll submitted: {payroll_entry}, Company: {company}")
        
        # Example: Update leave balances for this payroll period
        update_leave_balances_for_period(company, start_date, end_date)
        
        return True
    except Exception as e:
        frappe.log_error(_('Error in payroll submission handler'), str(e))
        return False

def process_leave_days_for_payroll(payroll_entry):
    """Process leave days for a payroll entry"""
    # Your implementation here
    frappe.msgprint(_('Processing leave days for payroll period'))

def update_leave_balances_for_period(company, start_date, end_date):
    """Update leave balances for a specific period"""
    # Your implementation here
    frappe.logger().info(f"Updating leave balances for {company} from {start_date} to {end_date}")