# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import manager_stats, portal_context


def get_context(context):
	portal_context(
		context,
		_("Manager Dashboard"),
		["Sales Manager", "Functional Team Manager"],
		active="manager",
		subtitle=_("Monitor the whole demo pipeline"),
	)
	# Determine which sections to show based on role
	from functional_demo.portal import is_sales, is_functional
	user_roles_set = frappe.get_roles()
	context.is_sales_manager = "Sales Manager" in user_roles_set
	context.is_functional_manager = "Functional Team Manager" in user_roles_set
	# Pass role to filter stats (functional = consultant data, sales = sales data)
	role = "functional" if context.is_functional_manager and not context.is_sales_manager else "sales" if context.is_sales_manager and not context.is_functional_manager else None
	context.stats = manager_stats(role)
	# Pending Manager Review requests
	pending = frappe.get_all(
		"Demo Request",
		filters={"workflow_state": "Manager Review"},
		fields=[
			"name", "customer", "lead", "interested_module", "priority",
			"sales_person", "creation", "functional_consultant",
		],
		order_by="creation desc",
		limit_page_length=50,
	) or []
	for r in pending:
		r["created_display"] = (
			frappe.utils.format_date(r.get("creation"), "medium") if r.get("creation") else "-"
		)
		if r.get("functional_consultant"):
			r["consultant_name"] = frappe.db.get_value(
				"Functional Consultant", r["functional_consultant"], "consultant_name"
			) or r["functional_consultant"]
		else:
			r["consultant_name"] = "-"
	context.stats["pending_review_requests"] = pending
	context.stats["pending_manager_review"] = len(pending)
	# ALL active demo requests (Manager can see and manage all)
	all_requests = frappe.get_all(
		"Demo Request",
		filters={"status": ["not in", ["Cancelled", "Closed", "Converted", "Not Interested"]]},
		fields=[
			"name", "customer", "lead", "interested_module", "priority",
			"sales_person", "functional_consultant", "status", "workflow_state",
			"preferred_demo_date", "creation",
		],
		order_by="creation desc",
		limit_page_length=100,
	) or []
	for r in all_requests:
		r["created_display"] = (
			frappe.utils.format_date(r.get("creation"), "medium") if r.get("creation") else "-"
		)
		if r.get("functional_consultant"):
			r["consultant_name"] = frappe.db.get_value(
				"Functional Consultant", r["functional_consultant"], "consultant_name"
			) or r["functional_consultant"]
		else:
			r["consultant_name"] = "-"
	context.all_requests = all_requests
	# Consultants for the assign dropdown
	consultants = frappe.get_all(
		"Functional Consultant",
		fields=["name", "consultant_name", "specialization", "availability", "status"],
		order_by="consultant_name asc",
		ignore_permissions=True,
	) or []
	context.consultants = [c for c in consultants if (c.get("status") or "") != "Inactive"]
	# Consultant activity details
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
			fields=["name", "customer", "scheduled_date", "start_time"],
			limit=1,
		) or []
		# Upcoming scheduled sessions
		upcoming = frappe.get_all(
			"Demo Session",
			filters={
				"functional_consultant": c.name,
				"demo_status": ["in", ["Scheduled", "Rescheduled"]],
			},
			fields=["name", "customer", "scheduled_date", "start_time"],
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
			fields=["name", "customer", "scheduled_date", "start_time", "demo_status"],
			order_by="start_time asc",
		) or []
		# Total completed
		completed_count = frappe.db.count(
			"Demo Session",
			{"functional_consultant": c.name, "demo_status": "Completed"},
		) or 0
		# Pending assigned requests (no session yet)
		pending_count = frappe.db.count(
		"Demo Request",
		{"functional_consultant": c.name, "status": "Assigned"},
	) or 0
		for sess in upcoming + todays:
			sess["date_display"] = (
				frappe.utils.format_date(sess.get("scheduled_date"), "medium") if sess.get("scheduled_date") else "-"
			)
		for sess in active_session:
			sess["date_display"] = (
				frappe.utils.format_date(sess.get("scheduled_date"), "medium") if sess.get("scheduled_date") else "-"
			)
		consultant_details.append({
			"name": c.name,
			"consultant_name": c.consultant_name,
			"specialization": c.specialization,
			"availability": c.availability,
			"active_session": active_session[0] if active_session else None,
			"upcoming_sessions": upcoming,
			"todays_sessions": todays,
			"completed_count": completed_count,
			"pending_count": pending_count,
		})
	context.consultant_details = consultant_details
	# Recent demo sessions
	sessions = frappe.get_all(
		"Demo Session",
		fields=[
			"name", "demo_request", "customer", "functional_consultant",
			"scheduled_date", "start_time", "demo_status", "final_result",
		],
		order_by="scheduled_date desc",
		limit_page_length=50,
	) or []
	for s in sessions:
		s["date_display"] = (
			frappe.utils.format_date(s.get("scheduled_date"), "medium") if s.get("scheduled_date") else "-"
		)
		if s.get("functional_consultant"):
			s["consultant_name"] = frappe.db.get_value(
				"Functional Consultant", s["functional_consultant"], "consultant_name"
			) or s["functional_consultant"]
		else:
			s["consultant_name"] = "-"
	context.sessions = sessions
	return context
