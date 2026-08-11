# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Module"), "fieldname": "interested_module", "fieldtype": "Data", "width": 160},
		{"label": _("Requests"), "fieldname": "request_count", "fieldtype": "Int", "width": 90},
		{"label": _("Scheduled"), "fieldname": "scheduled_count", "fieldtype": "Int", "width": 90},
		{"label": _("Completed"), "fieldname": "completed_count", "fieldtype": "Int", "width": 90},
		{"label": _("Converted"), "fieldname": "converted_count", "fieldtype": "Int", "width": 90},
		{"label": _("Conversion Rate (%)"), "fieldname": "conversion_rate", "fieldtype": "Percent", "width": 120},
	]

	conditions = ["docstatus = 0", "interested_module is not null and interested_module != ''"]
	if filters.get("from_date"):
		conditions.append("(preferred_demo_date >= %(from_date)s or creation >= %(from_date)s)")
	if filters.get("to_date"):
		conditions.append("(preferred_demo_date <= %(to_date)s or creation <= %(to_date)s)")
	if filters.get("module"):
		conditions.append("interested_module = %(module)s")
	if filters.get("sales_person"):
		conditions.append("sales_person = %(sales_person)s")

	data = frappe.db.sql(
		"""
		select interested_module,
			count(*) as request_count,
			sum(case when status in ('Scheduled', 'Demo In Progress') then 1 else 0 end) as scheduled_count,
			sum(case when status = 'Demo Completed' or status = 'Follow-up Required' then 1 else 0 end) as completed_count,
			sum(case when status = 'Converted' then 1 else 0 end) as converted_count
		from `tabDemo Request`
		where {conditions}
		group by interested_module
		order by request_count desc
		""".format(conditions=" and ".join(conditions)),
		filters,
		as_dict=1,
	)
	for row in data:
		row["conversion_rate"] = round(row["converted_count"] * 100.0 / row["request_count"], 1) if row["request_count"] else 0
	return columns, data
