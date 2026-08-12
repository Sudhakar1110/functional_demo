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


def get_context(context):
	portal_context(
		context,
		_("Demo Request"),
		["Sales User", "Sales Manager"],
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
		context.leads = frappe.get_all(
			"Lead",
			fields=["name", "lead_name", "company_name"],
			order_by="creation desc",
			limit_page_length=200,
		) or []
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

		context.consultants = frappe.get_all(
			"Functional Consultant",
			filters=[["status", "not in", ["Inactive", None]]],
			fields=["name", "consultant_name", "specialization", "availability", "experience_years"],
			order_by="consultant_name asc",
		) or []
		# Diagnostic: every consultant record (incl. Inactive / no status) so the
		# form can show exactly what the portal sees when the dropdown is empty
		context.consultant_diag = frappe.get_all(
			"Functional Consultant",
			fields=["name", "consultant_name", "status"],
			order_by="consultant_name asc",
		) or []
		# One-click pre-fill: arriving from My Leads (?lead=), a customer
		# (?customer=) or an ERPNext Opportunity (?opportunity=) pulls the
		# contact / company details from the CRM record into the form.
		context.prefill = _lead_opportunity_prefill()
		# Reusable request templates (industry presets) - Feature: Request Templates
		context.request_templates = frappe.get_all(
			"Demo Request Template",
			filters={"is_active": 1},
			fields=["name", "template_name"],
			order_by="template_name asc",
		) or []
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
	context.consultants = frappe.get_all(
		"Functional Consultant",
		filters=[["status", "not in", ["Inactive", None]]],
		fields=["name", "consultant_name", "specialization", "availability", "experience_years"],
		order_by="consultant_name asc",
	) or []
	context.consultant_names = {c["name"]: c["consultant_name"] for c in context.consultants}
	return context


def _lead_opportunity_prefill():
	"""Resolve the party + contact details to pre-fill when the create form is
	opened from a Lead, a Customer or an Opportunity."""
	prefill = {
		"customer": "",
		"lead": "",
		"company": "",
		"contact_person": "",
		"contact_number": "",
		"email": "",
	}
	opportunity = frappe.form_dict.get("opportunity") or ""
	lead = frappe.form_dict.get("lead") or ""
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
				prefill["lead"] = opp.get("lead")
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
	elif lead and frappe.db.exists("Lead", lead):
		ld = frappe.db.get_value(
			"Lead", lead, ["lead_name", "email_id", "phone", "mobile_no", "company_name"], as_dict=True
		)
		prefill["lead"] = lead
		if ld:
			if frappe.db.exists("Company", ld.get("company_name") or ""):
				prefill["company"] = ld.get("company_name") or ""
			prefill["contact_number"] = ld.get("mobile_no") or ld.get("phone") or ""
			prefill["email"] = ld.get("email_id") or ""
	elif customer and frappe.db.exists("Customer", customer):
		prefill["customer"] = customer

	return prefill
