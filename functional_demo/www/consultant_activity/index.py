# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import guard, is_admin, is_manager, portal_context


def get_context(context):
	"""Consultant Activity page — visible only to Functional Team Manager
	(and System Manager / Administrator for convenience)."""
	portal_context(
		context,
		_("Consultant Activity"),
		["Functional Team Manager"],
		active="consultant_activity",
		subtitle=_("Overview of all consultants and their demo activity"),
	)

	# Consultants with full activity details
	consultants = frappe.get_all(
		"Functional Consultant",
		fields=["name", "consultant_name", "specialization", "availability", "status"],
		order_by="consultant_name asc",
		ignore_permissions=True,
	) or []

	consultant_details = []
	for c in consultants:
		if (c.get("status") or "") == "Inactive":
			continue

		# Current active session (In Progress)
		active_session = frappe.get_all(
			"Demo Session",
			filters={
				"functional_consultant": c.name,
				"demo_status": "In Progress",
			},
			fields=["name", "customer", "scheduled_date", "start_time", "interested_module", "demo_request"],
			limit=1,
		) or []

		# Upcoming scheduled sessions
		upcoming = frappe.get_all(
			"Demo Session",
			filters={
				"functional_consultant": c.name,
				"demo_status": ["in", ["Scheduled", "Rescheduled"]],
			},
			fields=["name", "customer", "scheduled_date", "start_time", "interested_module", "demo_request"],
			order_by="scheduled_date asc",
			limit_page_length=10,
		) or []

		# Today's demos
		todays = frappe.get_all(
			"Demo Session",
			filters={
				"functional_consultant": c.name,
				"demo_status": ["in", ["Scheduled", "In Progress"]],
				"scheduled_date": frappe.utils.today(),
			},
			fields=["name", "customer", "scheduled_date", "start_time", "demo_status", "interested_module", "demo_request"],
			order_by="start_time asc",
		) or []

		# Total completed
		completed_count = frappe.db.count(
			"Demo Session",
			{"functional_consultant": c.name, "demo_status": "Completed"},
		) or 0

		# Pending assigned requests (no session yet)
		pending_requests = frappe.get_all(
			"Demo Request",
			filters={"functional_consultant": c.name, "status": "Assigned"},
			fields=["name", "customer", "interested_module", "preferred_demo_date", "sales_person"],
			order_by="preferred_demo_date asc",
		) or []
		pending_count = len(pending_requests)

		# In-progress session count
		in_progress_count = len(active_session)

		# Upcoming scheduled count
		upcoming_count = len(upcoming)

		# Enrich sessions with interested_module from linked demo_request if missing
		all_sessions = active_session + upcoming + todays
		for sess in all_sessions:
			sess["date_display"] = (
				frappe.utils.format_date(sess.get("scheduled_date"), "medium")
				if sess.get("scheduled_date")
				else "-"
			)
			# If interested_module is missing on session, try to get it from demo_request
			if not sess.get("interested_module") and sess.get("demo_request"):
				mod = frappe.db.get_value("Demo Request", sess["demo_request"], "interested_module")
				if mod:
					sess["interested_module"] = mod

		# Enrich pending requests with date display
		for pr in pending_requests:
			pr["date_display"] = (
				frappe.utils.format_date(pr.get("preferred_demo_date"), "medium")
				if pr.get("preferred_demo_date")
				else "-"
			)

		# Determine status badge
		if active_session:
			status_label = "In Progress"
			status_class = "b-demo-in-progress"
		elif upcoming:
			status_label = "Scheduled ({0})".format(upcoming_count)
			status_class = "b-scheduled"
		elif pending_count:
			status_label = "Pending ({0})".format(pending_count)
			status_class = "b-manager-review"
		else:
			status_label = "Free"
			status_class = "b-draft"

		# Next upcoming session details (for the main table row)
		next_session = upcoming[0] if upcoming else None
		next_pending = pending_requests[0] if pending_requests else None

		consultant_details.append({
			"name": c.name,
			"consultant_name": c.consultant_name,
			"specialization": c.specialization or "Generalist",
			"availability": c.availability or "Available",
			"status_label": status_label,
			"status_class": status_class,
			"active_session": active_session[0] if active_session else None,
			"next_session": next_session,
			"next_pending": next_pending,
			"upcoming_sessions": upcoming,
			"todays_sessions": todays,
			"pending_requests": pending_requests,
			"completed_count": completed_count,
			"pending_count": pending_count,
			"in_progress_count": in_progress_count,
			"upcoming_count": upcoming_count,
		})

	context.consultant_details = consultant_details

	# Summary counts
	total_consultants = len(consultant_details)
	total_active = sum(1 for c in consultant_details if c["active_session"])
	total_scheduled = sum(1 for c in consultant_details if c["upcoming_sessions"] and not c["active_session"])
	total_free = sum(1 for c in consultant_details if not c["active_session"] and not c["upcoming_sessions"] and not c["pending_count"])
	total_completed = sum(c["completed_count"] for c in consultant_details)

	context.total_consultants = total_consultants
	context.total_active = total_active
	context.total_scheduled = total_scheduled
	context.total_free = total_free
	context.total_completed = total_completed

	return context
