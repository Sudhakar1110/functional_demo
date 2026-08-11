frappe.query_reports["Upcoming Demo Report"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.get_today()},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date"},
		{"fieldname": "functional_consultant", "label": __("Functional Consultant"), "fieldtype": "Link", "options": "Functional Consultant"},
		{"fieldname": "sales_person", "label": __("Sales Person"), "fieldtype": "Link", "options": "User"},
		{"fieldname": "customer", "label": __("Customer"), "fieldtype": "Link", "options": "Customer"},
		{"fieldname": "demo_type", "label": __("Demo Type"), "fieldtype": "Select", "options": "\nStandard Demo\nCustomized Demo\nWalkthrough\nDeep Dive\nFollow-up Demo"},
	],
};
