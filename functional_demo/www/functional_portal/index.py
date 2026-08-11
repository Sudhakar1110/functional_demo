# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import functional_stats, portal_context


def get_context(context):
	portal_context(
		context,
		_("Functional Home"),
		["Functional Consultant", "Functional Team Manager"],
		active="functional",
		subtitle=_("Your demos, templates and follow_ups"),
	)
	context.stats = functional_stats()
	context.consultant_name = None
	if context.stats.get("consultant"):
		context.consultant_name = frappe.db.get_value(
			"Functional Consultant", context.stats.get("consultant"), "consultant_name"
		)
