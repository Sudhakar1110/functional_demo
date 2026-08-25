# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import consultant_of_user, portal_context

MODULES = [
	"", "Law Management", "Hospitality", "Medical Store", "Retail & Supermarket",
	"Manufacturing", "Education", "Healthcare", "Real Estate", "Logistics & Transport",
	"Agriculture", "IT Services", "Banking & Finance", "Food & Beverage",
	"Construction", "Energy & Utilities", "Other",
]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
DEMO_TYPES = ["Standard Demo", "Customized Demo", "Walkthrough", "Deep Dive", "Follow-up Demo"]


def _consultants_with_templates():
	"""Active consultants with their templates (child table) for dropdowns."""
	_consultants = frappe.get_all(
		"Functional Consultant",
		fields=["name", "consultant_name", "specialization", "availability", "experience_years", "status"],
		order_by="consultant_name asc",
		ignore_permissions=True,
	) or []
	consultants = [c for c in _consultants if (c.get("status") or "") != "Inactive"]
	names = [c["name"] for c in consultants]
	if names:
		templates = {}
		for row in frappe.get_all(
			"Consultant Module",
			filters={"parent": ["in", names]},
			fields=["parent", "module"],
		):
			templates.setdefault(row.parent, []).append(row.module)
		for c in consultants:
			c["modules"] = templates.get(c["name"]) or []
	return consultants


def get_context(context):
	portal_context(
		context,
		_("Demo Request"),
		["Sales User", "Sales Manager", "Functional Team Manager"],
		active="requests",
		subtitle=_("Create or review a demo request"),
	)
	name = frappe.form_dict.get("name") or ""
	context.create_mode = bool(frappe.form_dict.get("new") == "1" or not name)
	context.modules = MODULES
	context.priorities = PRIORITIES
	context.demo_types = DEMO_TYPES

	if context.create_mode:
		context.lead_param = frappe.form_dict.get("lead") or ""
		# sales_person is auto-set to the logged-in user — no dropdown needed
		context.current_user = frappe.session.user
		context.current_user_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
		context.customers = frappe.get_all(
			"Customer",
			fields=["name", "customer_name"],
			order_by="creation desc",
			limit_page_length=200,
		) or []
		context.companies = frappe.get_all("Company", fields=["name"], order_by="name asc") or []
		# Functional Consultant is mandatory when creating a demo request
		# If the current user is Administrator, make sure at least one consultant
		# record exists (the auto-created admin profile) so the dropdown is never
		# empty for the site admin - a common cause of the recurring
		# 'Consultant Required' error when testing the portal.
		consultant_of_user()  # side effect: auto-creates the Administrator profile

		# Availability is filtered in Python: an unset status is stored as NULL
		# and SQL status filters would silently hide those consultants.
		context.consultants = _consultants_with_templates()
		# One-click pre-fill: arriving from My Leads (?lead=), a customer
		# (?customer=) or an ERPNext Opportunity (?opportunity=) pulls the
		# contact / company details from the CRM record into the form.
		context.prefill = _lead_opportunity_prefill()
		return context

	# get_doc applies the app's row-level + document-level permissions automatically
	doc = frappe.get_doc("Demo Request", name)
	context.doc = doc
	context.activity = doc.get("demo_request_activity") or []
	context.session_name = frappe.db.get_value(
		"Demo Session",
		{"demo_request": doc.name, "demo_status": ["in", ["Scheduled", "In Progress"]]},
		"name",
	)
	context.consultants = _consultants_with_templates()
	context.consultant_names = {c["name"]: c["consultant_name"] for c in context.consultants}
	# A follow-up already exists for this request - the Create Follow-up
	# button must not show again (no duplicate follow-ups).
	context.has_follow_up = bool(
		frappe.db.exists("Demo Follow Up", {"demo_request": doc.name})
	)
	# Resolve the functional consultant's display name and email so the
	# template can show "Consultant" instead of the raw sales_person link.
	if doc.functional_consultant:
		c_info = frappe.db.get_value(
			"Functional Consultant", doc.functional_consultant,
			["consultant_name", "email"], as_dict=True,
		)
		context.consultant_display = (
			(c_info.consultant_name or "") + (" \u2014 " + c_info.email if c_info and c_info.email else "")
			if c_info else context.consultant_names.get(doc.functional_consultant, "")
		)
	else:
		context.consultant_display = ""
	# Resolve the sales person's display name from the User record
	if doc.sales_person:
		context.sales_person_name = frappe.db.get_value("User", doc.sales_person, "full_name") or doc.sales_person
	else:
		context.sales_person_name = ""
	return context


def _lead_opportunity_prefill():
	"""Resolve the party + contact details to pre-fill when the create form is
	opened from a Customer or an Opportunity."""
	prefill = {
		"customer": "",
		"company": "",
		"contact_person": "",
		"contact_number": "",
		"email": "",
	}
	opportunity = frappe.form_dict.get("opportunity") or ""
	customer = frappe.form_dict.get("customer") or ""

	if opportunity and frappe.db.exists("Opportunity", opportunity):
		opp = frappe.db.get_value(
			"Opportunity",
			opportunity,
			["opportunity_from", "party_name", "lead", "contact_person", "contact_email", "contact_mobile", "company"],
			as_dict=True,
		)
		if opp:
			if opp.get("opportunity_from") == "Lead" and opp.get("lead"):
				# Opportunity linked to a Lead — skip lead prefill, just get company
				pass
			elif opp.get("party_name"):
				prefill["customer"] = opp.get("party_name")
			if frappe.db.exists("Company", opp.get("company") or ""):
				prefill["company"] = opp.get("company") or ""
			if opp.get("contact_person"):
				prefill["contact_person"] = opp.get("contact_person")
			if opp.get("contact_email"):
				prefill["email"] = opp.get("contact_email")
			if opp.get("contact_mobile"):
				prefill["contact_number"] = opp.get("contact_mobile")
	elif customer and frappe.db.exists("Customer", customer):
		prefill["customer"] = customer

	return prefill
