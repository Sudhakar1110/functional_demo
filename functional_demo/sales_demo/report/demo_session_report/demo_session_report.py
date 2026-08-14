# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Demo Session"), "fieldname": "name", "fieldtype": "Link", "options": "Demo Session", "width": 140},
		{"label": _("Demo Request"), "fieldname": "demo_request", "fieldtype": "Link", "options": "Demo Request", "width": 140},
		{"label": _("Leads"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
		{"label": _("Sales Person"), "fieldname": "sales_person", "fieldtype": "Link", "options": "User", "width": 130},
		{"label": _("Consultant"), "fieldname": "functional_consultant", "fieldtype": "Link", "options": "Functional Consultant", "width": 150},
		{"label": _("Template"), "fieldname": "demo_template", "fieldtype": "Link", "options": "Functional Demo Template", "width": 150},
		{"label": _("Date"), "fieldname": "scheduled_date", "fieldtype": "Date", "width": 100},
		{"label": _("Start Time"), "fieldname": "start_time", "fieldtype": "Time", "width": 90},
		{"label": _("End Time"), "fieldname": "end_time", "fieldtype": "Time", "width": 90},
		{"label": _("Demo Status"), "fieldname": "demo_status", "fieldtype": "Data", "width": 120},
		{"label": _("Interested?"), "fieldname": "interested", "fieldtype": "Data", "width": 100},
		{"label": _("Follow-up Required"), "fieldname": "follow_up_required", "fieldtype": "Check", "width": 100},
		{"label": _("Final Result"), "fieldname": "final_result", "fieldtype": "Data", "width": 110},
	]

	conditions = ["docstatus = 0"]
	if filters.get("from_date"):
		conditions.append("scheduled_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("scheduled_date <= %(to_date)s")
	for key in ("demo_status", "sales_person", "functional_consultant", "customer", "demo_type"):
		if filters.get(key):
			conditions.append("{0} = %({0})s".format(key))

	data = frappe.db.sql(
		"""
		select name, demo_request, customer, sales_person, functional_consultant, demo_template,
			scheduled_date, start_time, end_time, demo_status, interested, follow_up_required, final_result
		from `tabDemo Session`
		where {conditions}
		order by scheduled_date desc, start_time
		""".format(conditions=" and ".join(conditions)),
		filters,
		as_dict=1,
	)
	return columns, data
