frappe.query_reports["Consultant Workload Report"] = {
	"filters": [
		{"fieldname": "as_on", "label": __("As On"), "fieldtype": "Date", "default": frappe.datetime.get_today()},
		{"fieldname": "functional_consultant", "label": __("Functional Consultant"), "fieldtype": "Link", "options": "Functional Consultant"},
	],
};
