# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import portal_context


def get_context(context):
	"""Assigned Demo page — shows all demo requests that have been assigned
	to Functional Consultants by the Functional Team Manager."""
	portal_context(
		context,
		_(("Assign Demo")),
		["Functional Team Manager"],
		active="assigned_demo",
		subtitle=_(("Review and assign demo requests to functional consultants")),
	)

	today = frappe.utils.today()

	# Get all demo requests that need attention: "Manager Review" (awaiting
	# consultant assignment) and "Assigned" (consultant assigned, awaiting
	# scheduling). When the Functional Team Manager assigns a consultant
	# from the Manager Dashboard, the request status becomes "Assigned"
	# and appears here automatically.
	assigned_requests = frappe.get_all(
		"Demo Request",
		filters={"status": ["in", ["Manager Review", "Assigned"]]},
		fields=[
			"name", "customer", "lead", "sales_person", "interested_module",
			"priority", "preferred_demo_date", "functional_consultant", "creation",
		],
		order_by="preferred_demo_date asc, creation desc",
		limit_page_length=500,
	) or []	for r in assigned_requests:
	r["created_display"] = (
		frappe.utils.format_date(r.get("creation"), "medium")
		if r.get("creation")
		else "-"
	)
	r["demo_date_display"] = (
		frappe.utils.format_date(r.get("preferred_demo_date"), "medium")
		if r.get("preferred_demo_date")
		else "-"
	)
	# Pass raw date value for the schedule modal pre-fill
	r["preferred_demo_date_raw"] = str(r.get("preferred_demo_date") or "")
	r["preferred_demo_time_raw"] = str(r.get("preferred_demo_time") or "")
		if r.get("functional_consultant"):
			r["consultant_name"] = frappe.db.get_value(
				"Functional Consultant", r["functional_consultant"], "consultant_name"
			) or r["functional_consultant"]
		else:
			r["consultant_name"] = "-"

		# Check if a demo session already exists for this request
		session = frappe.get_all(
			"Demo Session",
			filters={"demo_request": r.name},
			fields=["name", "demo_status", "scheduled_date"],
			limit=1,
		)
		if session:
			r["session_name"] = session[0].name
			r["session_status"] = session[0].demo_status
			r["session_date"] = (
				frappe.utils.format_date(session[0].scheduled_date, "medium")
				if session[0].scheduled_date
				else "-"
			)
		else:
			r["session_name"] = None
			r["session_status"] = None
			r["session_date"] = None

	# Consultants list for reference and assign dropdown
	consultants_list = frappe.get_all(
		"Functional Consultant",
		fields=["name", "consultant_name", "specialization", "availability"],
		order_by="consultant_name asc",
		ignore_permissions=True,
	) or []
	context.consultant_map = {c.name: c.consultant_name for c in consultants_list}
	context.consultants = [c for c in consultants_list if (c.get("status") or "") != "Inactive"]

	# Summary counts
	total_assigned = len(assigned_requests)
	with_session = sum(1 for r in assigned_requests if r.get("session_name"))
	without_session = total_assigned - with_session
	pending_review = sum(1 for r in assigned_requests if r.get("status") == "Manager Review")

	context.assigned_requests = assigned_requests
	context.total_assigned = total_assigned
	context.with_session = with_session
	context.without_session = without_session
	context.pending_review = pending_review

	return context
