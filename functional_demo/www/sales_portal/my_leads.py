# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import list_note, portal_context

LEAD_STATUSES = ["Lead", "Open", "Replied", "Opportunity", "Quotation", "Interested", "Converted", "Do Not Contact"]


def get_context(context):
	portal_context(
		context,
		_("Sales"),
		["Sales User", "Sales Manager"],
		active="leads",
		subtitle=_("Search and manage your sales"),
	)
	q = (frappe.form_dict.get("q") or "").strip()
	status = frappe.form_dict.get("status") or ""
	filters = []
	if q:
		filters.append(["lead_name", "like", "%{0}%".format(q)])
	if status:
		filters.append(["status", "=", status])

	context.leads = frappe.get_all(
		"Lead",
		filters=filters or None,
		fields=["name", "lead_name", "company_name", "email_id", "status", "source", "creation", "owner"],
		order_by="creation desc",
		limit_page_length=1000,
	) or []
	for lead in context.leads:
		lead["created_display"] = frappe.utils.format_date(lead.get("creation"), "medium") if lead.get("creation") else "-"
		# The ERPNext Lead doctype stores its default status as "Lead"; show it
		# as "Sales Person" in the portal (stored value stays untouched).
		lead["status_display"] = "Sales Person" if lead.get("status") == "Lead" else (lead.get("status") or "-")
	context.q = q
	context.status = status
	context.status_options = LEAD_STATUSES
	context.list_note = list_note(
		len(context.leads), frappe.db.count("Lead", filters or None), _("sales people")
	)
