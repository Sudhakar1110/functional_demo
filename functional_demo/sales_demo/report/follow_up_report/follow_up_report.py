# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Follow-up"), "fieldname": "name", "fieldtype": "Link", "options": "Demo Follow Up", "width": 130},
		{"label": _("Demo Session"), "fieldname": "demo_session", "fieldtype": "Link", "options": "Demo Session", "width": 140},
		{"label": _("Leads"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
		{"label": _("Assigned To"), "fieldname": "assigned_to", "fieldtype": "Link", "options": "User", "width": 130},
		{"label": _("Follow-up Date"), "fieldname": "follow_up_date", "fieldtype": "Date", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": _("Outcome"), "fieldname": "outcome", "fieldtype": "Data", "width": 150},
		{"label": _("Next Action"), "fieldname": "next_action", "fieldtype": "Data", "width": 220},
		{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 200},
	]

	conditions = ["docstatus = 0"]
	if filters.get("from_date"):
		conditions.append("follow_up_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("follow_up_date <= %(to_date)s")
	for key in ("status", "assigned_to", "outcome", "customer"):
		if filters.get(key):
			conditions.append("{0} = %({0})s".format(key))

	data = frappe.db.sql(
		"""
		select name, demo_session, customer, assigned_to, follow_up_date, status, outcome, next_action, remarks
		from `tabDemo Follow Up`
		where {conditions}
		order by follow_up_date asc
		""".format(conditions=" and ".join(conditions)),
		filters,
		as_dict=1,
	)
	return columns, data
