# Report Code For Displaying Leave Days

<td><strong>Leave Days:</strong> {{ frappe.db.get_value("Employee Leave Summary", {"employee": doc.employee}, "total_allocated_days") or 0 }} </td>