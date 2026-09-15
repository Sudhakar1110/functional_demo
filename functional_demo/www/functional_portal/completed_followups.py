# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import list_note, portal_context


def get_context(context):
	portal_context(
		context,
		_("Follow-ups Completed"),
		["Sales Manager"],
		active="completed_followups",
		subtitle=_("All completed follow-ups across demo requests"),
	)
	follow_ups = frappe.get_all(
		"Demo Follow Up",
		filters={"status": "Completed"},
		fields=[
			"name", "demo_request", "demo_session", "customer",
			"follow_up_date", "creation", "modified",
			"status", "outcome", "next_action", "remarks",
			"assigned_to", "sales_person", "description",
		],
		order_by="modified desc",
		limit_page_length=1000,
		ignore_permissions=True,
	) or []
	for fu in follow_ups:
		fu["due_display"] = (
			frappe.utils.format_date(fu.get("follow_up_date"), "medium")
			if fu.get("follow_up_date") else "-"
		)
		fu["created_display"] = (
			frappe.utils.format_datetime(fu.get("creation"), "dd MMM yyyy, hh:mm a")
			if fu.get("creation") else "-"
		)
		fu["completed_display"] = (
			frappe.utils.format_datetime(fu.get("modified"), "dd MMM yyyy, hh:mm a")
			if fu.get("modified") else "-"
		)
		if fu.get("assigned_to"):
			fu["assigned_display"] = (
				frappe.db.get_value("User", fu["assigned_to"], "full_name")
				or fu["assigned_to"]
			)
		else:
			fu["assigned_display"] = "-"
		if fu.get("sales_person"):
			fu["sales_person_display"] = (
				frappe.db.get_value("User", fu["sales_person"], "full_name")
				or fu["sales_person"]
			)
		else:
			fu["sales_person_display"] = "-"
	context.follow_ups = follow_ups
	context.list_note = list_note(
		len(context.follow_ups),
		frappe.db.count("Demo Follow Up", {"status": "Completed"}),
		_("completed follow-ups"),
	)
