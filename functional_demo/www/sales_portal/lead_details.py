# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import portal_context


def get_context(context):
	portal_context(
		context,
		_("Lead Details"),
		["Sales User", "Sales Manager"],
		active="requests",
		subtitle=_("Full lead & contact details for a demo request"),
	)
	name = frappe.form_dict.get("request") or ""
	if not name:
		context.missing = True
		return context

	# get_doc applies the app's row-level + document-level permissions
	# automatically - a missing / non-readable request shows a friendly card.
	try:
		doc = frappe.get_doc("Demo Request", name)
	except Exception:
		context.access_denied = True
		return context

	context.request = doc
	context.additional_leads = doc.get("additional_leads") or []
	context.sessions = frappe.get_all(
		"Demo Session",
		filters={"demo_request": doc.name},
		fields=["name", "customer", "interested_module", "scheduled_date", "start_time", "demo_status", "final_result"],
		order_by="scheduled_date desc",
		limit_page_length=50,
	) or []
	context.follow_ups = frappe.get_all(
		"Demo Follow Up",
		filters={"demo_request": doc.name},
		fields=["name", "follow_up_date", "status", "next_action"],
		order_by="follow_up_date desc",
		limit_page_length=50,
	) or []
	return context
