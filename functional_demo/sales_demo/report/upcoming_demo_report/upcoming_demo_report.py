# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _
from frappe.utils import today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Demo Session"), "fieldname": "name", "fieldtype": "Link", "options": "Demo Session", "width": 140},
		{"label": _("Leads"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
		{"label": _("Contact Number"), "fieldname": "contact_number", "fieldtype": "Data", "width": 120},
		{"label": _("Consultant"), "fieldname": "functional_consultant", "fieldtype": "Link", "options": "Functional Consultant", "width": 150},
		{"label": _("Sales Person"), "fieldname": "sales_person", "fieldtype": "Link", "options": "User", "width": 130},
		{"label": _("Date"), "fieldname": "scheduled_date", "fieldtype": "Date", "width": 100},
		{"label": _("Start Time"), "fieldname": "start_time", "fieldtype": "Time", "width": 90},
		{"label": _("End Time"), "fieldname": "end_time", "fieldtype": "Time", "width": 90},
		{"label": _("Meeting Link"), "fieldname": "meeting_link", "fieldtype": "Data", "width": 180},
		{"label": _("Demo Status"), "fieldname": "demo_status", "fieldtype": "Data", "width": 120},
	]

	conditions = ["docstatus = 0", "scheduled_date >= %(from_date)s", "demo_status in ('Scheduled', 'In Progress')"]
	if filters.get("to_date"):
		conditions.append("scheduled_date <= %(to_date)s")
	for key in ("functional_consultant", "sales_person", "customer", "demo_type"):
		if filters.get(key):
			conditions.append("{0} = %({0})s".format(key))

	data = frappe.db.sql(
		"""
		select name, customer, contact_number, functional_consultant, sales_person,
			scheduled_date, start_time, end_time, meeting_link, demo_status
		from `tabDemo Session`
		where {conditions}
		order by scheduled_date asc, start_time
		""".format(conditions=" and ".join(conditions)),
		filters,
		as_dict=1,
	)
	return columns, data
