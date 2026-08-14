# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import portal_context


def get_context(context):
	portal_context(
		context,
		_("New Consultant Profile"),
		["Functional Team Manager"],
		active="consultants",
		subtitle=_("Create a consultant profile on the portal - it is saved in the desk automatically"),
	)
	context.can_manage_consultants = True

	# users who don't have a consultant profile yet - the consultant must be a
	# real User so they can log in and conduct demos
	linked = {
		row[0]
		for row in frappe.db.sql(
			"select user from `tabFunctional Consultant` where ifnull(user, '') != ''"
		)
	}
	users = frappe.get_all(
		"User",
		filters=[["enabled", "=", 1]],
		fields=["name", "full_name", "email"],
		order_by="full_name asc",
	)
	context.users = [
		{
			"user": u.name,
			"full_name": u.full_name or u.name,
			"email": u.email or "",
		}
		for u in users
		if u.name not in ("Guest", "Administrator") and u.name not in linked
	]

	# Templates come from the Consultant Module child table options so the
	# portal can never drift from what the desk accepts.
	context.templates = [
		s
		for s in (
			frappe.get_meta("Consultant Module").get_field("module").options or ""
		).split("\n")
		if s
	]
