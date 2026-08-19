# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import list_note, portal_context


def get_context(context):
	portal_context(
		context,
		_("Sales"),
		["Sales User", "Sales Manager"],
		active="leads",
		subtitle=_(("Search and manage your sales team")),
	)
	q = (frappe.form_dict.get("q") or "").strip()

	# Show users with Sales User or Sales Manager role as Sales Persons
	sales_roles = ["Sales User", "Sales Manager"]
	filters = [["Has Role", "role", "in", sales_roles]]
	if q:
		filters.append(["full_name", "like", "%{0}%".format(q)])

	users = frappe.get_all(
		"User",
		filters=filters,
		fields=["name", "full_name", "email", "user_image", "creation", "last_active"],
		order_by="full_name asc",
		limit_page_length=1000,
	) or []

	context.leads = []
	for u in users:
		if u.name in ("Administrator", "Guest"):
			continue
		# Get roles for this user
		user_roles = frappe.get_roles(u.name)
		role_display = []
		if "Sales Manager" in user_roles:
			role_display.append("Sales Manager")
		if "Sales User" in user_roles:
			role_display.append("Sales User")

		context.leads.append({
			"name": u.name,
			"full_name": u.full_name or u.name,
			"email": u.email or "-",
			"roles": ", ".join(role_display),
			"last_active": frappe.utils.format_datetime(u.last_active, "dd MMM yyyy, hh:mm a") if u.last_active else "Never",
			"created_display": frappe.utils.format_date(u.creation, "medium") if u.creation else "-",
		})

	context.q = q
	context.list_note = list_note(
		len(context.leads),
		frappe.db.count("User", [["Has Role", "role", "in", sales_roles]]) or 0,
		_("sales team members"),
	)
