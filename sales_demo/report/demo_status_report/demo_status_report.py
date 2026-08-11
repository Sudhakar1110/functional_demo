# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 180},
		{"label": _("Count"), "fieldname": "count", "fieldtype": "Int", "width": 100},
		{"label": _("Percentage (%)"), "fieldname": "percentage", "fieldtype": "Percent", "width": 120},
	]

	conditions = ["docstatus = 0"]
	if filters.get("from_date"):
		conditions.append("(preferred_demo_date >= %(from_date)s or creation >= %(from_date)s)")
	if filters.get("to_date"):
		conditions.append("(preferred_demo_date <= %(to_date)s or creation <= %(to_date)s)")
	if filters.get("sales_person"):
		conditions.append("sales_person = %(sales_person)s")
	if filters.get("functional_consultant"):
		conditions.append("functional_consultant = %(functional_consultant)s")
	if filters.get("status"):
		conditions.append("status = %(status)s")

	data = frappe.db.sql(
		"""
		select status, count(*) as count
		from `tabDemo Request`
		where {conditions}
		group by status
		order by count desc
		""".format(conditions=" and ".join(conditions)),
		filters,
		as_dict=1,
	)
	total = sum(row["count"] for row in data) or 1
	for row in data:
		row["percentage"] = round(row["count"] * 100.0 / total, 1)
	return columns, data
