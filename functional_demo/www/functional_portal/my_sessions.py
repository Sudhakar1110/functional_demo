# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import (
	consultant_of_user, is_functional_manager, list_note, portal_context,
)

SESSION_STATUSES = [
	"Scheduled", "In Progress", "Completed", "Rescheduled",
	"Cancelled", "Closed",
]


def get_context(context):
	is_mgr = is_functional_manager()
	subtitle = (
		_("All demo sessions across consultants")
		if is_mgr
		else _("Sessions and demos assigned to you")
	)
	portal_context(
		context,
		_("My Demo Sessions"),
		["Sales User", "Sales Manager", "Functional Consultant", "Functional Team Manager"],
		active="sessions",
		subtitle=subtitle,
	)
	consultant = consultant_of_user()
	status = frappe.form_dict.get("status") or ""
	filters = {}
	# Functional Team Managers see ALL sessions (not just their own) so they
	# can track demos they assigned to consultants, including rescheduled ones.
	if consultant and not is_functional_manager():
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
	# Functional Team Managers see ALL pending requests across all consultants.
	assigned_requests = []
	if not status:
		request_filters = {"status": "Assigned"}
		if consultant and not is_functional_manager():
			request_filters["functional_consultant"] = consultant
		# Find demo request names that already have an active session
		session_filters = {"demo_status": ["in", ["Scheduled", "In Progress", "Rescheduled"]]}
		if consultant and not is_functional_manager():
			session_filters["functional_consultant"] = consultant
		active_session_requests = frappe.get_all(
			"Demo Session",
			filters=session_filters,
			fields=["demo_request"],
			pluck="demo_request",
		) or []
		if active_session_requests:
			request_filters["name"] = ["not in", active_session_requests]
		assigned_requests = frappe.get_all(
			"Demo Request",
			filters=request_filters,
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
	# For managers showing all sessions, use the total DB count (unfiltered)
	# so the note reflects the true total rather than the filtered subset.
	total_count = (
		frappe.db.count("Demo Session")
		if is_mgr
		else frappe.db.count("Demo Session", filters)
	)
	context.list_note = list_note(
		len(context.sessions), total_count, _("demo sessions")
	)
