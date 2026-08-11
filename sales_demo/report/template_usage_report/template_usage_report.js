frappe.query_reports["Template Usage Report"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -6)},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today()},
		{"fieldname": "functional_consultant", "label": __("Functional Consultant"), "fieldtype": "Link", "options": "Functional Consultant"},
		{"fieldname": "template", "label": __("Template"), "fieldtype": "Link", "options": "Functional Demo Template"},
	],
};
