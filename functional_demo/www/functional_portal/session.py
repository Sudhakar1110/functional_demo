# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.api import get_demo_execution_data
from functional_demo.portal import portal_context


def get_context(context):
	portal_context(
		context,
		_("Conduct Demo"),
		["Functional Consultant", "Functional Team Manager"],
		active="sessions",
		subtitle=_("Everything you need for this demo on one screen"),
	)
	name = frappe.form_dict.get("name") or ""
	if not name:
		context.missing = True
		return context

	# get_demo_execution_data enforces document-level read permission
	data = get_demo_execution_data(name)
	if data.get("session") and data["session"].get("scheduled_date"):
		data["session"]["scheduled_date"] = frappe.utils.format_date(
			data["session"]["scheduled_date"], "medium"
		)
	context.data = data
	return context
