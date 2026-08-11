frappe.query_reports["Demo Request Report"] = {
	"filters": [
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -3)},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today()},
		{"fieldname": "status", "label": __("Status"), "fieldtype": "Select", "options": "\nDraft\nRequested\nAssigned\nScheduled\nDemo In Progress\nDemo Completed\nFollow-up Required\nConverted\nNot Interested\nCancelled\nClosed"},
		{"fieldname": "sales_person", "label": __("Sales Person"), "fieldtype": "Link", "options": "User"},
		{"fieldname": "functional_consultant", "label": __("Functional Consultant"), "fieldtype": "Link", "options": "Functional Consultant"},
		{"fieldname": "customer", "label": __("Customer"), "fieldtype": "Link", "options": "Customer"},
		{"fieldname": "module", "label": __("Module"), "fieldtype": "Select", "options": "\nAccounting\nCRM\nSelling\nBuying\nStock\nManufacturing\nHR & Payroll\nProjects\nHealthcare\nEducation\nAgriculture\nCustom Application"},
		{"fieldname": "priority", "label": __("Priority"), "fieldtype": "Select", "options": "\nLow\nMedium\nHigh\nCritical"},
		{"fieldname": "demo_type", "label": __("Demo Type"), "fieldtype": "Select", "options": "\nStandard Demo\nCustomized Demo\nWalkthrough\nDeep Dive\nFollow-up Demo"},
	],
};
