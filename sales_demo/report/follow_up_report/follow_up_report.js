frappe.query_reports["Follow-up Report"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -3)},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today()},
		{"fieldname": "status", "label": __("Status"), "fieldtype": "Select", "options": "\nOpen\nIn Progress\nCompleted\nOverdue"},
		{"fieldname": "assigned_to", "label": __("Assigned To"), "fieldtype": "Link", "options": "User"},
		{"fieldname": "outcome", "label": __("Outcome"), "fieldtype": "Select", "options": "\nPending\nAdditional Discussion\nAdditional Demo Required\nConverted\nNot Interested\nClosed"},
		{"fieldname": "customer", "label": __("Customer"), "fieldtype": "Link", "options": "Customer"},
	],
};
