# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _
from frappe.utils import add_days, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	as_on = filters.get("as_on") or today()
	week_end = add_days(as_on, 7)

	columns = [
		{"label": _("Consultant"), "fieldname": "functional_consultant", "fieldtype": "Link", "options": "Functional Consultant", "width": 180},
		{"label": _("Specialization"), "fieldname": "specialization", "fieldtype": "Data", "width": 120},
		{"label": _("Availability"), "fieldname": "availability", "fieldtype": "Data", "width": 100},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
		{"label": _("Active Demos"), "fieldname": "active_demos", "fieldtype": "Int", "width": 100},
		{"label": _("Today's Demos"), "fieldname": "todays_demos", "fieldtype": "Int", "width": 100},
		{"label": _("Next 7 Days"), "fieldname": "week_demos", "fieldtype": "Int", "width": 100},
		{"label": _("Completed"), "fieldname": "completed_demos", "fieldtype": "Int", "width": 90},
		{"label": _("Open Templates"), "fieldname": "templates", "fieldtype": "Int", "width": 110},
	]

	conditions = []
	if filters.get("functional_consultant"):
		conditions.append("fc.name = %(functional_consultant)s")
	where_clause = (" and " + " and ".join(conditions)) if conditions else ""

	consultants = frappe.db.sql(
		"""
		select fc.name as functional_consultant, fc.specialization, fc.availability, fc.status,
			sum(case when ds.demo_status in ('Scheduled', 'In Progress') then 1 else 0 end) as active_demos,
			sum(case when ds.scheduled_date = %(as_on)s then 1 else 0 end) as todays_demos,
			sum(case when ds.scheduled_date between %(as_on)s and %(week_end)s then 1 else 0 end) as week_demos,
			sum(case when ds.demo_status = 'Completed' then 1 else 0 end) as completed_demos
		from `tabFunctional Consultant` fc
		left join `tabDemo Session` ds on ds.functional_consultant = fc.name and ds.docstatus = 0
		where fc.docstatus = 0{where_clause}
		group by fc.name
		order by fc.consultant_name
		""".format(where_clause=where_clause),
		{
			"as_on": as_on,
			"week_end": week_end,
			"functional_consultant": filters.get("functional_consultant"),
		},
		as_dict=1,
	)

	template_counts = dict(
		frappe.db.sql(
			"""select functional_consultant, count(*) from `tabFunctional Demo Template`
			where is_active = 1 and docstatus = 0 group by functional_consultant"""
		)
	)
	for row in consultants:
		row["templates"] = int(template_counts.get(row["functional_consultant"]) or 0)
	return columns, consultants
