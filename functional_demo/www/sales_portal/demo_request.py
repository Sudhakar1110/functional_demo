# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import portal_context

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
		# Functional Consultant is mandatory when creating a demo request
		context.consultants = frappe.get_all(
			"Functional Consultant",
			filters={"status": "Active"},
			fields=["name", "consultant_name", "specialization", "availability", "experience_years"],
			order_by="consultant_name asc",
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
		filters={"status": "Active"},
		fields=["name", "consultant_name", "specialization", "availability", "experience_years"],
		order_by="consultant_name asc",
	) or []
	context.consultant_names = {c["name"]: c["consultant_name"] for c in context.consultants}
	return context
