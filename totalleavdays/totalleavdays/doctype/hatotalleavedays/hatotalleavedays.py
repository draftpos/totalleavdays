import frappe
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, flt, today, nowdate
from datetime import datetime, timedelta

class HatotalLeaveDays(Document):
    def validate(self):
        self.validate_dates()
        self.calculate_leave_days()
        self.update_leave_balances()
        self.validate_leave_balance()
    
    def on_submit(self):
        if self.status == "Approved":
            self.update_leave_balance()
    
    def on_cancel(self):
        if self.status == "Approved":
            self.reverse_leave_balance()
    
    def validate_dates(self):
        if getdate(self.from_date) > getdate(self.to_date):
            frappe.throw("From Date cannot be after To Date")
    
    def calculate_leave_days(self):
        """Calculate number of leave days between dates"""
        if self.from_date and self.to_date:
            from_date = getdate(self.from_date)
            to_date = getdate(self.to_date)
            
            total_days = date_diff(to_date, from_date) + 1
            
            # Subtract weekends (Saturday=5, Sunday=6)
            weekend_days = 0
            current_date = from_date
            while current_date <= to_date:
                if current_date.weekday() in [5, 6]:
                    weekend_days += 1
                current_date += timedelta(days=1)
            
            working_days = total_days - weekend_days
            
            # Apply half day logic
            if self.half_day and self.half_day_date:
                half_day_date = getdate(self.half_day_date)
                if from_date <= half_day_date <= to_date:
                    working_days -= 0.5
            
            self.leave_days = flt(working_days, 1)
    
    def update_leave_balances(self):
        """Update all leave balance totals for the employee"""
        if self.employee:
            balance_data = get_all_leave_balances_data(self.employee, self.leave_period)
            
            self.total_allocated_days = balance_data["total_allocated"]
            self.total_used_days = balance_data["total_used"]
            self.total_remaining_days = balance_data["total_remaining"]
    
    def validate_leave_balance(self):
        """Validate that applied leave doesn't exceed balance for the specific type"""
        if self.leave_days > 0 and self.leave_type:
            specific_balance = get_leave_type_balance_data(self.employee, self.leave_type, self.leave_period)
            
            if self.leave_days > specific_balance["remaining_days"]:
                frappe.throw(
                    "Leave days ({}) cannot exceed remaining balance of {} days for {} leave".format(
                        self.leave_days, specific_balance["remaining_days"], self.leave_type
                    )
                )
    
    def update_leave_balance(self):
        """Update the is_approved flag when leave is approved"""
        self.db_set("is_approved", 1)
    
    def reverse_leave_balance(self):
        """Reverse the approval when leave is cancelled"""
        self.db_set("is_approved", 0)
        self.db_set("status", "Cancelled")

# NEW FUNCTIONS for comprehensive leave management

def get_all_leave_balances_data(employee, leave_period=None):
    """Get comprehensive leave balance data for all leave types"""
    leave_types = frappe.get_all("Leave Type", pluck="name")
    breakdown = []
    total_allocated = 0
    total_used = 0
    
    for leave_type in leave_types:
        balance_data = get_leave_type_balance_data(employee, leave_type, leave_period)
        if balance_data["allocated_days"] > 0:  # Only include leave types with allocation
            breakdown.append({
                "leave_type": leave_type,
                "allocated_days": balance_data["allocated_days"],
                "used_days": balance_data["used_days"],
                "remaining_days": balance_data["remaining_days"]
            })
            total_allocated += balance_data["allocated_days"]
            total_used += balance_data["used_days"]
    
    return {
        "total_allocated": total_allocated,
        "total_used": total_used,
        "total_remaining": total_allocated - total_used,
        "breakdown": breakdown
    }

def get_leave_type_balance_data(employee, leave_type, leave_period=None):
    """Get balance data for a specific leave type"""
    allocated = get_allocated_days(employee, leave_type, leave_period)
    used = get_used_days(employee, leave_type, leave_period)
    
    return {
        "allocated_days": allocated,
        "used_days": used,
        "remaining_days": allocated - used
    }

def get_allocated_days(employee, leave_type, leave_period=None):
    """Get allocated days considering leave period"""
    filters = {
        "employee": employee,
        "leave_type": leave_type,
        "docstatus": 1
    }
    
    if leave_period:
        filters["leave_period"] = leave_period
    
    allocation = frappe.get_all("Leave Allocation",
        filters=filters,
        fields=["SUM(total_leaves_allocated) as total_allocated"]
    )
    
    if allocation and allocation[0].get("total_allocated"):
        return flt(allocation[0].get("total_allocated"))
    
    return 0.0

def get_used_days(employee, leave_type, leave_period=None):
    """Get used days considering leave period"""
    filters = {
        "employee": employee,
        "leave_type": leave_type,
        "status": "Approved",
        "docstatus": 1
    }
    
    if leave_period:
        # If leave period is specified, filter by creation date within period
        period_doc = frappe.get_doc("Leave Period", leave_period)
        filters["from_date"] = [">=", period_doc.from_date]
        filters["to_date"] = ["<=", period_doc.to_date]
    
    used_days = frappe.get_all("HatotalLeaveDays",
        filters=filters,
        fields=["SUM(leave_days) as total_used"]
    )
    
    if used_days and used_days[0].get("total_used"):
        return flt(used_days[0].get("total_used"))
    
    return 0.0

@frappe.whitelist()
def get_all_leave_balances(employee, leave_period=None):
    """API endpoint to get all leave balances"""
    return get_all_leave_balances_data(employee, leave_period)

@frappe.whitelist()
def get_leave_type_balance(employee, leave_type, leave_period=None):
    """API endpoint to get specific leave type balance"""
    return get_leave_type_balance_data(employee, leave_type, leave_period)

@frappe.whitelist()
def calculate_leave_days(from_date, to_date, half_day=0, half_day_date=None):
    """Calculate number of leave days between dates"""
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    
    if from_date > to_date:
        return {"leave_days": 0}
    
    total_days = date_diff(to_date, from_date) + 1
    weekend_days = 0
    current_date = from_date
    
    while current_date <= to_date:
        if current_date.weekday() in [5, 6]:
            weekend_days += 1
        current_date += timedelta(days=1)
    
    working_days = total_days - weekend_days
    
    if half_day and half_day_date:
        half_day_date = getdate(half_day_date)
        if from_date <= half_day_date <= to_date:
            working_days -= 0.5
    
    return {"leave_days": flt(working_days, 1)}

# ... rest of the existing functions (bulk_fetch_employees, etc.) remain the same
# but update them to use the new comprehensive balance functions





















@frappe.whitelist()
def bulk_fetch_employees(number_of_employees, leave_type, fetch_method="active"):
    """Bulk fetch employees with their leave data"""
    try:
        number_of_employees = int(number_of_employees)
    except:
        number_of_employees = 10
    
    # Build query based on fetch method
    filters = {"status": "Active"} if fetch_method == "active" else {}
    order_by = "creation DESC" if fetch_method == "recent" else "RAND()"
    
    employees = frappe.get_all("Employee",
        filters=filters,
        fields=["name", "employee_name", "status"],
        limit=number_of_employees,
        order_by=order_by
    )
    
    employees_data = []
    for emp in employees:
        leave_data = get_leave_balance_data(emp.name, leave_type)
        employees_data.append({
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "leave_type": leave_type,
            "allocated_days": leave_data["allocated_days"],
            "used_days": leave_data["used_days"],
            "remaining_days": leave_data["remaining_days"],
            "status": emp.status
        })
    
    return employees_data

def get_leave_balance_data(employee, leave_type):
    """Get leave balance data for an employee"""
    allocated = get_allocated_days(employee, leave_type)
    used = get_used_days(employee, leave_type)
    
    return {
        "allocated_days": allocated,
        "used_days": used,
        "remaining_days": allocated - used
    }

@frappe.whitelist()
def create_bulk_leave_records(employees_data, leave_type):
    """Create multiple leave records from bulk data"""
    if isinstance(employees_data, str):
        employees_data = frappe.parse_json(employees_data)
    
    created_count = 0
    
    for emp_data in employees_data:
        try:
            # Create a new leave record
            leave_doc = frappe.get_doc({
                "doctype": "HatotalLeaveDays",
                "employee": emp_data["employee"],
                "employee_name": emp_data["employee_name"],
                "leave_type": leave_type,
                "allocated_days": emp_data["allocated_days"],
                "used_days": emp_data["used_days"],
                "remaining_days": emp_data["remaining_days"],
                "from_date": nowdate(),
                "to_date": nowdate(),
                "leave_days": 0,
                "status": "Draft",
                "date_created": nowdate()
            })
            
            leave_doc.insert(ignore_permissions=True)
            created_count += 1
            
        except Exception as e:
            frappe.log_error(f"Error creating leave record for {emp_data['employee']}: {str(e)}")
            continue
    
    return created_count

@frappe.whitelist()
def get_employee_leave_dashboard():
    """Get dashboard data for all employees"""
    employees = frappe.get_all("Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "department", "designation"]
    )
    
    dashboard_data = []
    for emp in employees:
        # Get leave summary for all leave types
        leave_types = frappe.get_all("Leave Type", pluck="name")
        leave_summary = []
        
        for leave_type in leave_types:
            balance_data = get_leave_balance_data(emp.name, leave_type)
            if balance_data["allocated_days"] > 0:  # Only show leave types with allocation
                leave_summary.append({
                    "leave_type": leave_type,
                    **balance_data
                })
        
        dashboard_data.append({
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "department": emp.department,
            "designation": emp.designation,
            "leave_summary": leave_summary
        })
    
    return dashboard_data

# Add this to the existing HatotalLeaveDays class if you want a method to update multiple records
@frappe.whitelist()
def bulk_update_leave_status(leave_names, status):
    """Bulk update leave status"""
    if isinstance(leave_names, str):
        leave_names = frappe.parse_json(leave_names)
    
    updated_count = 0
    for leave_name in leave_names:
        try:
            doc = frappe.get_doc("HatotalLeaveDays", leave_name)
            doc.status = status
            doc.is_approved = 1 if status == "Approved" else 0
            doc.save()
            updated_count += 1
        except:
            continue
    
    return updated_count