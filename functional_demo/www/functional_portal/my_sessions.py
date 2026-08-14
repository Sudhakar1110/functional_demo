# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import consultant_of_user, portal_context

SESSION_STATUSES = [
	"Scheduled", "In Progress", "Completed", "Rescheduled",
	"Cancelled", "Follow-up Required", "Closed",
]


def get_context(context):
	portal_context(
		context,
		_("My Demo Sessions"),
		["Sales User", "Sales Manager", "Functional Consultant", "Functional Team Manager"],
		active="sessions",
		subtitle=_("Sessions assigned to you"),
	)
	consultant = consultant_of_user()
	status = frappe.form_dict.get("status") or ""
	filters = {}
	if consultant:
		filters["functional_consultant"] = consultant
	if status:
		filters["demo_status"] = status

	context.sessions = frappe.get_all(
		"Demo Session",
		filters=filters,
		fields=[
			"name", "customer", "lead", "sales_person", "scheduled_date", "start_time", "end_time",
			"demo_status", "demo_type", "final_result", "demo_request",
		],
		order_by="scheduled_date desc",
		limit_page_length=200,
	) or []
	context.status = status
	context.status_options = SESSION_STATUSES
	context.consultant = consultant
