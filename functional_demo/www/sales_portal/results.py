# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import portal_context, sales_stats


def get_context(context):
	portal_context(
		context,
		_("Demo Results"),
		["Sales User", "Sales Manager"],
		active="results",
		subtitle=_("Completed demos, customer feedback and conversion"),
	)
	context.stats = sales_stats()
	context.results = frappe.get_all(
		"Demo Session",
		filters={"demo_status": ["in", ["Completed", "Follow-up Required", "Closed"]]},
		fields=[
			"name", "customer", "sales_person", "scheduled_date", "demo_status", "interested",
			"requirements_met", "overall_feedback", "follow_up_required",
			"final_result", "functional_consultant", "demo_request",
		],
		order_by="scheduled_date desc",
		limit_page_length=100,
	) or []
	context.converted = frappe.get_all(
		"Demo Request",
		filters={"status": "Converted"},
		fields=["name", "customer", "lead", "functional_consultant", "priority", "creation"],
		order_by="creation desc",
		limit_page_length=50,
	) or []
	for c in context.converted:
		c["creation_display"] = (
			frappe.utils.format_date(c.get("creation"), "medium") if c.get("creation") else "-"
		)
	return context
