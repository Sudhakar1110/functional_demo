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
	# Pending Manager Review requests (for Functional Team Manager)
	pending = frappe.get_all(
		"Demo Request",
		filters={"workflow_state": "Manager Review"},
		fields=[
			"name", "customer", "lead", "interested_module", "priority",
			"sales_person", "creation",
		],
		order_by="creation desc",
		limit_page_length=50,
	) or []
	for r in pending:
		r["created_display"] = (
			frappe.utils.format_date(r.get("creation"), "medium") if r.get("creation") else "-"
		)
	context.stats["pending_review_requests"] = pending
	context.stats["pending_manager_review"] = len(pending)
	return context
