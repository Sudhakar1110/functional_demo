# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
		{"label": _("Total Requests"), "fieldname": "total_requests", "fieldtype": "Int", "width": 110},
		{"label": _("Demos Completed"), "fieldname": "completed", "fieldtype": "Int", "width": 120},
		{"label": _("Follow-ups"), "fieldname": "follow_ups", "fieldtype": "Int", "width": 100},
		{"label": _("Converted"), "fieldname": "converted", "fieldtype": "Int", "width": 90},
		{"label": _("Last Demo Date"), "fieldname": "last_demo_date", "fieldtype": "Date", "width": 110},
		{"label": _("Last Status"), "fieldname": "last_status", "fieldtype": "Data", "width": 130},
	]

	conditions = ["dr.docstatus = 0"]
	if filters.get("customer"):
		conditions.append("dr.customer = %(customer)s")
	if filters.get("from_date"):
		conditions.append("(dr.preferred_demo_date >= %(from_date)s or dr.creation >= %(from_date)s)")
	if filters.get("to_date"):
		conditions.append("(dr.preferred_demo_date <= %(to_date)s or dr.creation <= %(to_date)s)")
	if filters.get("sales_person"):
		conditions.append("dr.sales_person = %(sales_person)s")

	data = frappe.db.sql(
		"""
		select dr.customer as customer,
			count(distinct dr.name) as total_requests,
			sum(case when dr.status = 'Demo Completed' then 1 else 0 end) as completed,
			sum(case when dr.status = 'Follow-up Required' then 1 else 0 end) as follow_ups,
			sum(case when dr.status = 'Converted' then 1 else 0 end) as converted,
			max(ds.scheduled_date) as last_demo_date,
			(select status from `tabDemo Request` dr2
				where dr2.customer = dr.customer order by dr2.creation desc limit 1) as last_status
		from `tabDemo Request` dr
		left join `tabDemo Session` ds on ds.demo_request = dr.name
		where {conditions}
		group by dr.customer
		order by last_demo_date desc
		""".format(conditions=" and ".join(conditions)),
		filters,
		as_dict=1,
	)
	return columns, data
