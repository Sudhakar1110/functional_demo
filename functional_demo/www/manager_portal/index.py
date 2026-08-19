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
	context.stats = manager_stats()
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
