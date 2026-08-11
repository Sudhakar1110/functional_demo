frappe.query_reports["Demo Status Report"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -3)},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today()},
		{"fieldname": "status", "label": __("Status"), "fieldtype": "Select", "options": "\nDraft\nRequested\nAssigned\nScheduled\nDemo In Progress\nDemo Completed\nFollow-up Required\nConverted\nNot Interested\nCancelled\nClosed"},
		{"fieldname": "sales_person", "label": __("Sales Person"), "fieldtype": "Link", "options": "User"},
		{"fieldname": "functional_consultant", "label": __("Functional Consultant"), "fieldtype": "Link", "options": "Functional Consultant"},
	],
};
