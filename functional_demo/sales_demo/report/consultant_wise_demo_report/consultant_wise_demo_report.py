# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Functional Consultant"), "fieldname": "functional_consultant", "fieldtype": "Link", "options": "Functional Consultant", "width": 180},
		{"label": _("Total Demos"), "fieldname": "total_demos", "fieldtype": "Int", "width": 90},
		{"label": _("Scheduled"), "fieldname": "scheduled", "fieldtype": "Int", "width": 90},
		{"label": _("In Progress"), "fieldname": "in_progress", "fieldtype": "Int", "width": 90},
		{"label": _("Completed"), "fieldname": "completed", "fieldtype": "Int", "width": 90},
		{"label": _("Cancelled"), "fieldname": "cancelled", "fieldtype": "Int", "width": 90},
		{"label": _("Follow-ups"), "fieldname": "follow_ups", "fieldtype": "Int", "width": 90},
		{"label": _("Converted"), "fieldname": "converted", "fieldtype": "Int", "width": 90},
		{"label": _("Conversion Rate (%)"), "fieldname": "conversion_rate", "fieldtype": "Percent", "width": 120},
	]

	conditions = ["docstatus = 0", "functional_consultant is not null"]
	if filters.get("from_date"):
		conditions.append("scheduled_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("scheduled_date <= %(to_date)s")
	if filters.get("functional_consultant"):
		conditions.append("functional_consultant = %(functional_consultant)s")

	data = frappe.db.sql(
		"""
		select functional_consultant,
			count(*) as total_demos,
			sum(case when demo_status = 'Scheduled' then 1 else 0 end) as scheduled,
			sum(case when demo_status = 'In Progress' then 1 else 0 end) as in_progress,
			sum(case when demo_status = 'Completed' then 1 else 0 end) as completed,
			sum(case when demo_status = 'Cancelled' then 1 else 0 end) as cancelled,
			(select count(*) from `tabDemo Follow Up` fu where fu.demo_session = `tabDemo Session`.name) as follow_ups,
			sum(case when final_result = 'Converted' then 1 else 0 end) as converted
		from `tabDemo Session`
		where {conditions}
		group by functional_consultant
		order by total_demos desc
		""".format(conditions=" and ".join(conditions)),
		filters,
		as_dict=1,
	)
	for row in data:
		row["conversion_rate"] = round(row["converted"] * 100.0 / row["total_demos"], 1) if row["total_demos"] else 0
	return columns, data
