# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Demo Session"), "fieldname": "name", "fieldtype": "Link", "options": "Demo Session", "width": 140},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
		{"label": _("Consultant"), "fieldname": "functional_consultant", "fieldtype": "Link", "options": "Functional Consultant", "width": 150},
		{"label": _("Sales Person"), "fieldname": "sales_person", "fieldtype": "Link", "options": "User", "width": 130},
		{"label": _("Scheduled Date"), "fieldname": "scheduled_date", "fieldtype": "Date", "width": 110},
		{"label": _("Completed On"), "fieldname": "completed_on", "fieldtype": "Datetime", "width": 140},
		{"label": _("Interested?"), "fieldname": "interested", "fieldtype": "Data", "width": 100},
		{"label": _("Requirements Met"), "fieldname": "requirements_met", "fieldtype": "Data", "width": 120},
		{"label": _("Follow-up Required"), "fieldname": "follow_up_required", "fieldtype": "Check", "width": 100},
		{"label": _("Follow-up Date"), "fieldname": "follow_up_date", "fieldtype": "Date", "width": 110},
		{"label": _("Final Result"), "fieldname": "final_result", "fieldtype": "Data", "width": 110},
		{"label": _("Overall Feedback"), "fieldname": "overall_feedback", "fieldtype": "Data", "width": 220},
	]

	conditions = ["docstatus = 0", "demo_status = 'Completed'"]
	if filters.get("from_date"):
		conditions.append("(completed_on >= %(from_date)s or scheduled_date >= %(from_date)s)")
	if filters.get("to_date"):
		conditions.append("(completed_on <= %(to_date)s or scheduled_date <= %(to_date)s)")
	for key in ("functional_consultant", "sales_person", "customer", "interested", "final_result"):
		if filters.get(key):
			conditions.append("{0} = %({0})s".format(key))

	data = frappe.db.sql(
		"""
		select name, customer, functional_consultant, sales_person, scheduled_date, completed_on,
			interested, requirements_met, follow_up_required, follow_up_date, final_result, overall_feedback
		from `tabDemo Session`
		where {conditions}
		order by completed_on desc
		""".format(conditions=" and ".join(conditions)),
		filters,
		as_dict=1,
	)
	return columns, data
