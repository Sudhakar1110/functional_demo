# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.api import get_demo_execution_data
from functional_demo.portal import portal_context


def get_context(context):
	portal_context(
		context,
		_("Demo Session"),
		["Sales User", "Sales Manager", "Functional Consultant", "Functional Team Manager", "Developer"],
		active="sessions",
		subtitle=_("Session details, demo feedback and actions"),
	)
	name = frappe.form_dict.get("name") or ""
	if not name:
		context.missing = True
		return context

	# get_demo_execution_data enforces document-level read permission. When the
	# page is opened from Demo Feedback or Results for a session the current
	# user cannot read, show a friendly card instead of a raw error.
	try:
		data = get_demo_execution_data(name)
	except Exception:
		context.access_denied = True
		return context
	if data.get("session") and data["session"].get("scheduled_date"):
		data["session"]["scheduled_date"] = frappe.utils.format_date(
			data["session"]["scheduled_date"], "medium"
		)
	context.data = data
	return context
