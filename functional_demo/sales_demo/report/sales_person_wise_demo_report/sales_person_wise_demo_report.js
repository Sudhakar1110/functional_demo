frappe.query_reports["Sales Person-wise Demo Report"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -3)},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today()},
		{"fieldname": "sales_person", "label": __("Sales Person"), "fieldtype": "Link", "options": "User"},
		{"fieldname": "functional_consultant", "label": __("Functional Consultant"), "fieldtype": "Link", "options": "Functional Consultant"},
		{"fieldname": "module", "label": __("Module"), "fieldtype": "Select", "options": "\nAccounting\nCRM\nSelling\nBuying\nStock\nManufacturing\nHR & Payroll\nProjects\nHealthcare\nEducation\nAgriculture\nCustom Application"},
	],
};
