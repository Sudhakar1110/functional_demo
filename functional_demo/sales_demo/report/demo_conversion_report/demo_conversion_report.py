# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Stage"), "fieldname": "stage", "fieldtype": "Data", "width": 200},
		{"label": _("Count"), "fieldname": "count", "fieldtype": "Int", "width": 100},
		{"label": _("% of Total"), "fieldname": "percentage", "fieldtype": "Percent", "width": 110},
	]

	conditions = ["docstatus = 0"]
	if filters.get("from_date"):
		conditions.append("(preferred_demo_date >= %(from_date)s or creation >= %(from_date)s)")
	if filters.get("to_date"):
		conditions.append("(preferred_demo_date <= %(to_date)s or creation <= %(to_date)s)")
	for key in ("sales_person", "functional_consultant", "priority", "demo_type"):
		if filters.get(key):
			conditions.append("{0} = %({0})s".format(key))
	if filters.get("module"):
		conditions.append("interested_module = %(module)s")

	where = " and ".join(conditions)
	rows = frappe.db.sql(
		"""
		select
			count(*) as total,
			sum(case when status in ('Draft', 'Requested', 'Assigned') then 1 else 0 end) as pipeline,
			sum(case when status = 'Scheduled' then 1 else 0 end) as scheduled,
			sum(case when status = 'Demo In Progress' then 1 else 0 end) as in_progress,
			sum(case when status in ('Demo Completed', 'Follow-up Required') then 1 else 0 end) as completed,
			sum(case when status = 'Follow-up Required' then 1 else 0 end) as follow_ups,
			sum(case when status = 'Converted' then 1 else 0 end) as converted,
			sum(case when status = 'Not Interested' then 1 else 0 end) as not_interested,
			sum(case when status = 'Cancelled' then 1 else 0 end) as cancelled,
			sum(case when status = 'Closed' then 1 else 0 end) as closed
		from `tabDemo Request`
		where {where}
		""".format(where=where),
		filters,
		as_dict=1,
	)[0]

	total = rows["total"] or 1
	stages = [
		(_("Total Demo Requests"), rows["total"]),
		(_("In Pipeline (Draft/Requested/Assigned)"), rows["pipeline"]),
		(_("Scheduled"), rows["scheduled"]),
		(_("Demo In Progress"), rows["in_progress"]),
		(_("Demos Completed (incl. follow-ups)"), rows["completed"]),
		(_("Follow-ups Required"), rows["follow_ups"]),
		(_("Converted"), rows["converted"]),
		(_("Not Interested"), rows["not_interested"]),
		(_("Cancelled"), rows["cancelled"]),
		(_("Closed"), rows["closed"]),
	]
	data = [{"stage": stage, "count": count, "percentage": round(count * 100.0 / total, 1)} for stage, count in stages]

	# summary row with the conversion rate
	conversion_rate = round(rows["converted"] * 100.0 / total, 1)
	data.append(
		{
			"stage": _("Conversion Rate (Converted / Total)"),
			"count": rows["converted"],
			"percentage": conversion_rate,
		}
	)
	return columns, data
