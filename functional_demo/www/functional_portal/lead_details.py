# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import portal_context


def get_context(context):
	portal_context(
		context,
		_("Lead Details"),
		["Sales User", "Sales Manager", "Functional Consultant", "Functional Team Manager"],
		active="sessions",
		subtitle=_("Functional view of the lead - template, dates and requirements"),
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

	# Functional view only: names / dates / requirements - deliberately NO
	# contact person, contact number or email (sales-private data).
	context.request = doc
	# Additional leads are listed as names only - their contact details stay
	# visible only on the sales portal lead-details page.
	context.additional_leads = [
		{"customer": row.get("customer"), "notes": row.get("notes")}
		for row in (doc.get("additional_leads") or [])
		if row.get("customer") or row.get("notes")
	]
	context.sessions = frappe.get_all(
		"Demo Session",
		filters={"demo_request": doc.name},
		fields=["name", "customer", "interested_module", "scheduled_date", "start_time", "demo_status", "final_result"],
		order_by="scheduled_date desc",
		limit_page_length=50,
	) or []
	return context
