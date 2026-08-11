# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Template"), "fieldname": "name", "fieldtype": "Link", "options": "Functional Demo Template", "width": 190},
		{"label": _("Template Name"), "fieldname": "template_name", "fieldtype": "Data", "width": 180},
		{"label": _("Consultant"), "fieldname": "functional_consultant", "fieldtype": "Link", "options": "Functional Consultant", "width": 150},
		{"label": _("Module"), "fieldname": "erpnext_module", "fieldtype": "Data", "width": 110},
		{"label": _("Active"), "fieldname": "is_active", "fieldtype": "Check", "width": 70},
		{"label": _("Times Used"), "fieldname": "usage_count", "fieldtype": "Int", "width": 100},
		{"label": _("Last Used"), "fieldname": "last_used", "fieldtype": "Date", "width": 110},
	]

	conditions = ["t.docstatus = 0"]
	if filters.get("functional_consultant"):
		conditions.append("t.functional_consultant = %(functional_consultant)s")
	if filters.get("template"):
		conditions.append("t.name = %(template)s")
	if filters.get("from_date"):
		conditions.append("(ds.scheduled_date >= %(from_date)s or ds.scheduled_date is null)")
	if filters.get("to_date"):
		conditions.append("(ds.scheduled_date <= %(to_date)s or ds.scheduled_date is null)")

	data = frappe.db.sql(
		"""
		select t.name, t.template_name, t.functional_consultant, t.erpnext_module, t.is_active,
			count(ds.name) as usage_count,
			max(ds.scheduled_date) as last_used
		from `tabFunctional Demo Template` t
		left join `tabDemo Session` ds on ds.demo_template = t.name and ds.docstatus = 0
		where {conditions}
		group by t.name
		order by usage_count desc
		""".format(conditions=" and ".join(conditions)),
		filters,
		as_dict=1,
	)
	return columns, data
