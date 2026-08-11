# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import consultant_of_user, portal_context

STATUS_OPTIONS = ["Open", "In Progress", "Completed", "Overdue"]
OUTCOME_OPTIONS = [
	"Pending", "Additional Discussion", "Additional Demo Required",
	"Converted", "Not Interested", "Closed",
]


def get_context(context):
	portal_context(
		context,
		_("Follow-ups"),
		["Functional Consultant", "Functional Team Manager"],
		active="follow_ups",
		subtitle=_("Follow-ups on your demos"),
	)
	consultant = consultant_of_user()
	filters = {}
	if consultant:
		filters["functional_consultant"] = consultant

	context.follow_ups = frappe.get_all(
		"Demo Follow Up",
		filters=filters,
		fields=[
			"name", "demo_request", "demo_session", "customer", "follow_up_date",
			"status", "outcome", "next_action", "remarks", "assigned_to",
		],
		order_by="follow_up_date asc",
		limit_page_length=200,
	) or []
	for fu in context.follow_ups:
		fu["due_display"] = frappe.utils.format_date(fu.get("follow_up_date"), "medium") if fu.get("follow_up_date") else "-"
	context.consultant = consultant
	context.status_options = STATUS_OPTIONS
	context.outcome_options = OUTCOME_OPTIONS
