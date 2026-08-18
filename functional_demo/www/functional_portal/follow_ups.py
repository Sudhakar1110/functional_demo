# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import list_note, portal_context

STATUS_OPTIONS = ["Open", "In Progress", "Completed", "Overdue"]
OUTCOME_OPTIONS = [
	"Pending", "Additional Discussion", "Additional Demo Required",
	"Converted", "Not Interested", "Closed",
]


def get_context(context):
	# Follow-ups are sales-team-only - the functional team never sees this page.
	portal_context(
		context,
		_("Follow-ups"),
		["Sales User", "Sales Manager"],
		active="follow_ups",
		subtitle=_("Follow-ups on your demo requests"),
	)
	# Row-level permission filters (see demo_follow_up.has_permission) restrict
	# the list to follow-ups the sales user is assigned to or owns - no extra
	# filtering needed here.
	context.follow_ups = frappe.get_all(
		"Demo Follow Up",
		fields=[
			"name", "demo_request", "demo_session", "customer", "follow_up_date",
			"status", "outcome", "next_action", "remarks", "assigned_to",
		],
		order_by="follow_up_date asc",
		limit_page_length=1000,
	) or []
	for fu in context.follow_ups:
		fu["due_display"] = frappe.utils.format_date(fu.get("follow_up_date"), "medium") if fu.get("follow_up_date") else "-"
	context.status_options = STATUS_OPTIONS
	context.outcome_options = OUTCOME_OPTIONS
	context.list_note = list_note(
		len(context.follow_ups), frappe.db.count("Demo Follow Up"), _("follow-ups")
	)
