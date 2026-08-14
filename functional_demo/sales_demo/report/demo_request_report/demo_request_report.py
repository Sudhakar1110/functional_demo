# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Demo Request"), "fieldname": "name", "fieldtype": "Link", "options": "Demo Request", "width": 140},
		{"label": _("Leads"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
		{"label": _("Sales Person"), "fieldname": "lead", "fieldtype": "Link", "options": "Lead", "width": 130},
		{"label": _("Sales Person"), "fieldname": "sales_person", "fieldtype": "Link", "options": "User", "width": 130},
		{"label": _("Template"), "fieldname": "interested_module", "fieldtype": "Data", "width": 140},
		{"label": _("Priority"), "fieldname": "priority", "fieldtype": "Data", "width": 80},
		{"label": _("Consultant"), "fieldname": "functional_consultant", "fieldtype": "Link", "options": "Functional Consultant", "width": 150},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": _("Preferred Date"), "fieldname": "preferred_demo_date", "fieldtype": "Date", "width": 100},
		{"label": _("Demo Type"), "fieldname": "demo_type", "fieldtype": "Data", "width": 120},
		{"label": _("Follow-up Date"), "fieldname": "follow_up_date", "fieldtype": "Date", "width": 100},
	]

	conditions = ["docstatus = 0"]
	if filters.get("from_date"):
		conditions.append("(preferred_demo_date >= %(from_date)s or preferred_demo_date is null)")
	if filters.get("to_date"):
		conditions.append("(preferred_demo_date <= %(to_date)s or preferred_demo_date is null)")
	for key in ("status", "sales_person", "functional_consultant", "customer", "priority", "demo_type"):
		if filters.get(key):
			conditions.append("{0} = %({0})s".format(key))
	if filters.get("module"):
		conditions.append("interested_module = %(module)s")

	data = frappe.db.sql(
		"""
		select name, customer, lead, sales_person, interested_module, priority,
			functional_consultant, status, preferred_demo_date, demo_type, follow_up_date
		from `tabDemo Request`
		where {conditions}
		order by creation desc
		""".format(conditions=" and ".join(conditions)),
		filters,
		as_dict=1,
	)
	return columns, data
