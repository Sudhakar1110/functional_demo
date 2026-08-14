frappe.query_reports["Leads Demo History"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -6)},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today()},
		{"fieldname": "customer", "label": __("Customer"), "fieldtype": "Link", "options": "Customer"},
		{"fieldname": "sales_person", "label": __("Sales Person"), "fieldtype": "Link", "options": "User"},
	],
};
