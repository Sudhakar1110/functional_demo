frappe.query_reports["Module-wise Demo Report"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -3)},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today()},
		{"fieldname": "module", "label": __("Module"), "fieldtype": "Select", "options": "\nAccounting\nCRM\nSelling\nBuying\nStock\nManufacturing\nHR & Payroll\nProjects\nHealthcare\nEducation\nAgriculture\nCustom Application"},
		{"fieldname": "sales_person", "label": __("Sales Person"), "fieldtype": "Link", "options": "User"},
	],
};
