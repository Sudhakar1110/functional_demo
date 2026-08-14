# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import portal_context


def get_context(context):
	portal_context(
		context,
		_("Consultant Profiles"),
		["Functional Team Manager"],
		active="consultants",
		subtitle=_("All functional consultants and their profiles"),
	)

	consultants = frappe.get_all(
		"Functional Consultant",
		fields=[
			"name",
			"consultant_name",
			"user",
			"specialization",
			"experience_years",
			"availability",
			"status",
			"email",
			"phone",
			"notes",
		],
		order_by="consultant_name asc",
	) or []

	# count active (scheduled / in progress) demos per consultant
	active_counts = dict(
		frappe.db.sql(
			"""
			select functional_consultant, count(*)
			from `tabDemo Session`
			where demo_status in ('Scheduled', 'In Progress')
			group by functional_consultant
			"""
		)
	)

	for c in consultants:
		c["active_demos"] = active_counts.get(c.name, 0) or 0
		c["email"] = c.get("email") or frappe.db.get_value("User", c.get("user"), "email") or ""
		c["phone"] = c.get("phone") or frappe.db.get_value("User", c.get("user"), "mobile_no") or ""

	context.consultants = consultants
