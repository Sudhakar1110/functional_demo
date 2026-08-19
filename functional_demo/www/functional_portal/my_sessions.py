# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import consultant_of_user, list_note, portal_context

SESSION_STATUSES = [
	"Scheduled", "In Progress", "Completed", "Rescheduled",
	"Cancelled", "Closed",
]


def get_context(context):
	portal_context(
		context,
		_("My Demo Sessions"),
		["Sales User", "Sales Manager", "Functional Consultant", "Functional Team Manager"],
		active="sessions",
		subtitle=_("Sessions and demos assigned to you"),
	)
	consultant = consultant_of_user()
	status = frappe.form_dict.get("status") or ""
	filters = {}
	if consultant:
		filters["functional_consultant"] = consultant
	if status:
		filters["demo_status"] = status

	# Sessions are listed by assignment date (newest first), so a freshly
	# assigned demo appears at the top of the list.
	context.sessions = frappe.get_all(
		"Demo Session",
		filters=filters,
		fields=[
			"name", "customer", "lead", "sales_person", "interested_module", "scheduled_date",
			"start_time", "end_time", "demo_status", "final_result", "demo_request", "creation",
		],
		order_by="creation desc",
		limit_page_length=1000,
	) or []
	for s in context.sessions:
		s["assigned_display"] = (
			frappe.utils.format_datetime(s.get("creation"), "dd MMM yyyy, hh:mm a")
			if s.get("creation")
			else "-"
		)
		s["is_session"] = True

	# Also fetch Demo Requests assigned to this consultant that do NOT have
	# an active session yet (i.e. they are in "Assigned" state waiting to
	# be scheduled).  This lets the consultant see new assignments immediately.
	assigned_requests = []
	if consultant and not status:
		# Find demo request names that already have an active session
		active_session_requests = frappe.get_all(
			"Demo Session",
			filters={
				"functional_consultant": consultant,
				"demo_status": ["in", ["Scheduled", "In Progress", "Rescheduled"]],
			},
			fields=["demo_request"],
			pluck="demo_request",
		) or []
		assigned_requests = frappe.get_all(
			"Demo Request",
			filters={
				"functional_consultant": consultant,
				"status": "Assigned",
				"name": ["not in", active_session_requests],
			},
			fields=[
				"name", "customer", "lead", "sales_person", "interested_module",
				"preferred_demo_date", "preferred_demo_time", "status", "creation",
			],
			order_by="creation desc",
			limit_page_length=100,
		) or []
	for r in assigned_requests:
		r["assigned_display"] = (
			frappe.utils.format_datetime(r.get("creation"), "dd MMM yyyy, hh:mm a")
			if r.get("creation")
			else "-"
		)
		r["is_session"] = False
		r["session_name"] = ""

	# Merge sessions and pending requests into one list, newest first
	context.all_items = context.sessions + assigned_requests
	context.all_items.sort(key=lambda x: x.get("creation") or "", reverse=True)

	context.status = status
	context.status_options = SESSION_STATUSES
	context.consultant = consultant
	context.list_note = list_note(
		len(context.sessions), frappe.db.count("Demo Session", filters), _("demo sessions")
	)
