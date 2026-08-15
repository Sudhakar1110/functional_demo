# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import list_note, portal_context

STATUS_OPTIONS = [
	"Draft", "Requested", "Assigned", "Scheduled", "Demo In Progress",
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
		limit_page_length=1000,
	) or []
	for r in context.requests:
		r["created_display"] = frappe.utils.format_date(r.get("creation"), "medium") if r.get("creation") else "-"
	context.status = status
	context.status_options = STATUS_OPTIONS
	context.list_note = list_note(
		len(context.requests), frappe.db.count("Demo Request", filters), _("demo requests")
	)
	# consultants for the bulk-assign action (excludes only Inactive records;
	# filtered in Python because an unset status is stored as NULL and SQL
	# status filters would silently hide those consultants)
	_consultants = frappe.get_all(
		"Functional Consultant",
		fields=["name", "consultant_name", "specialization", "status"],
		order_by="consultant_name asc",
		ignore_permissions=True,
	) or []
	context.consultants = [c for c in _consultants if (c.get("status") or "") != "Inactive"]

	# templates per consultant (child table) for the assign dropdown
	_consultant_names = [c["name"] for c in context.consultants]
	if _consultant_names:
		_templates = {}
		for row in frappe.get_all(
			"Consultant Module",
			filters={"parent": ["in", _consultant_names]},
			fields=["parent", "module"],
		):
			_templates.setdefault(row.parent, []).append(row.module)
		for c in context.consultants:
			c["modules"] = _templates.get(c["name"]) or []
