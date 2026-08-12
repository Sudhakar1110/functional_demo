# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import portal_context

STATUS_OPTIONS = [
	"Draft", "Requested", "Approved", "Assigned", "Scheduled", "Demo In Progress",
	"Demo Completed", "Follow-up Required", "Converted", "Not Interested",
	"Cancelled", "Closed",
]


def get_context(context):
	portal_context(
		context,
		_("Demo Requests"),
		["Sales User", "Sales Manager"],
		active="requests",
		subtitle=_("All demo requests you can see"),
	)
	status = frappe.form_dict.get("status") or ""
	filters = {}
	if status:
		filters["status"] = status

	context.requests = frappe.get_all(
		"Demo Request",
		filters=filters,
		fields=[
			"name", "customer", "lead", "status", "priority", "interested_module",
			"preferred_demo_date", "functional_consultant", "sales_person",
			"follow_up_date", "creation", "sla_due_date", "sla_breached",
		],
		order_by="creation desc",
		limit_page_length=200,
	) or []
	for r in context.requests:
		r["created_display"] = frappe.utils.format_date(r.get("creation"), "medium") if r.get("creation") else "-"
	context.status = status
	context.status_options = STATUS_OPTIONS
	# active consultants for the bulk-assign action
	context.consultants = frappe.get_all(
		"Functional Consultant",
		filters={"status": "Active"},
		fields=["name", "consultant_name", "specialization"],
		order_by="consultant_name asc",
	) or []
