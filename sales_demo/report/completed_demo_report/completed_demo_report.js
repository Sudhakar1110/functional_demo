frappe.query_reports["Completed Demo Report"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -3)},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today()},
		{"fieldname": "functional_consultant", "label": __("Functional Consultant"), "fieldtype": "Link", "options": "Functional Consultant"},
		{"fieldname": "sales_person", "label": __("Sales Person"), "fieldtype": "Link", "options": "User"},
		{"fieldname": "customer", "label": __("Customer"), "fieldtype": "Link", "options": "Customer"},
		{"fieldname": "interested", "label": __("Interested?"), "fieldtype": "Select", "options": "\nInterested\nNot Interested\nUndecided"},
		{"fieldname": "final_result", "label": __("Final Result"), "fieldtype": "Select", "options": "\nPending\nConverted\nNot Interested\nClosed"},
	],
};
