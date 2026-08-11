# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Sales Person"), "fieldname": "sales_person", "fieldtype": "Link", "options": "User", "width": 160},
		{"label": _("Total Requests"), "fieldname": "total_requests", "fieldtype": "Int", "width": 100},
		{"label": _("Scheduled"), "fieldname": "scheduled", "fieldtype": "Int", "width": 90},
		{"label": _("Demos Completed"), "fieldname": "completed", "fieldtype": "Int", "width": 110},
		{"label": _("Follow-ups"), "fieldname": "follow_ups", "fieldtype": "Int", "width": 90},
		{"label": _("Converted"), "fieldname": "converted", "fieldtype": "Int", "width": 90},
		{"label": _("Not Interested"), "fieldname": "not_interested", "fieldtype": "Int", "width": 110},
		{"label": _("Conversion Rate (%)"), "fieldname": "conversion_rate", "fieldtype": "Percent", "width": 120},
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
	if filters.get("module"):
		conditions.append("interested_module = %(module)s")

	data = frappe.db.sql(
		"""
		select sales_person,
			count(*) as total_requests,
			sum(case when status = 'Scheduled' or status = 'Demo In Progress' then 1 else 0 end) as scheduled,
			sum(case when status = 'Demo Completed' then 1 else 0 end) as completed,
			sum(case when status = 'Follow-up Required' then 1 else 0 end) as follow_ups,
			sum(case when status = 'Converted' then 1 else 0 end) as converted,
			sum(case when status = 'Not Interested' then 1 else 0 end) as not_interested
		from `tabDemo Request`
		where {conditions}
		group by sales_person
		order by total_requests desc
		""".format(conditions=" and ".join(conditions)),
		filters,
		as_dict=1,
	)
	for row in data:
		row["conversion_rate"] = round(row["converted"] * 100.0 / row["total_requests"], 1) if row["total_requests"] else 0
	return columns, data
