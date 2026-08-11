frappe.query_reports["Consultant-wise Demo Report"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -3)},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today()},
		{"fieldname": "functional_consultant", "label": __("Functional Consultant"), "fieldtype": "Link", "options": "Functional Consultant"},
	],
};
