frappe.query_reports["Demo Session Report"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -3)},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today()},
		{"fieldname": "demo_status", "label": __("Demo Status"), "fieldtype": "Select", "options": "\nScheduled\nIn Progress\nCompleted\nRescheduled\nCancelled\nFollow-up Required\nClosed"},
		{"fieldname": "sales_person", "label": __("Sales Person"), "fieldtype": "Link", "options": "User"},
		{"fieldname": "functional_consultant", "label": __("Functional Consultant"), "fieldtype": "Link", "options": "Functional Consultant"},
		{"fieldname": "customer", "label": __("Customer"), "fieldtype": "Link", "options": "Customer"},
		{"fieldname": "demo_type", "label": __("Demo Type"), "fieldtype": "Select", "options": "\nStandard Demo\nCustomized Demo\nWalkthrough\nDeep Dive\nFollow-up Demo"},
	],
};
