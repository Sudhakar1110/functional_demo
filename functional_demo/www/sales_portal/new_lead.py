# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import is_mail_notifications_enabled, portal_context

LEAD_STATUSES = ["Lead", "Open", "Replied", "Opportunity", "Quotation", "Interested", "Converted", "Do Not Contact"]
# Fallback sources for sites where the Lead doctype has no source options yet
DEFAULT_SOURCES = ["Website", "Referral", "Cold Call", "Existing Customer", "Social Media", "Trade Show", "Walk In", "Advertisement", "Other"]


def get_context(context):
	if not is_mail_notifications_enabled():
		frappe.local.flags.redirect_location = "/demo_portal"
		raise frappe.Redirect
	portal_context(
		context,
		_("New Sales Person"),
		["Sales User", "Sales Manager"],
		active="leads",
		subtitle=_("Create a sales person right here - no need to open ERPNext"),
	)
	# Source options come from the Lead doctype itself (the same list the desk
	# accepts), so the dropdown can never drift from what ERPNext validates.
	source_field = frappe.get_meta("Lead").get_field("source")
	meta_options = ((source_field.options if source_field else "") or "").split("\n")
	context.sources = [s for s in meta_options if s] or DEFAULT_SOURCES
	context.status_options = LEAD_STATUSES
	# Pre-fill from the URL (?company_name=..., ?email=..., ?phone=...) so the
	# page can be opened pre-populated from elsewhere in the portal later.
	context.prefill = {
		"lead_name": frappe.form_dict.get("lead_name") or "",
		"company_name": frappe.form_dict.get("company_name") or "",
		"email": frappe.form_dict.get("email") or "",
		"phone": frappe.form_dict.get("phone") or "",
	}
