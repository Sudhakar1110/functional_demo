# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Create realistic sample data for the Sales & Functional Demo Management app.

Usage:

    bench --site your-site execute functional_demo.setup_demo_data.setup_demo_data

The script is idempotent - re-running it skips records that already exist.
It creates consultant users + profiles, customers/leads with contacts, reusable
demo templates, and demo requests/sessions across every workflow state so the
workspaces, dashboards, reports and notifications all have real content.
"""

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime, today

from functional_demo.sales_demo.doctype.demo_request.demo_request import change_status


def setup_demo_data(verbose=True):
	"""Create sample data (idempotent). Run via bench execute."""
	created = {
		"users": [],
		"consultants": [],
		"customers": [],
		"leads": [],
		"contacts": [],
		"templates": [],
		"requests": [],
		"sessions": [],
		"follow_ups": [],
		"opportunities": [],
	}

	# ---------------------------------------------------------------
	# 1. Consultant users + Functional Consultant profiles
	# ---------------------------------------------------------------
	users = [
		{"email": "rahul.kumar@example.com", "first_name": "Rahul", "last_name": "Kumar"},
		{"email": "priya.sharma@example.com", "first_name": "Priya", "last_name": "Sharma"},
		{"email": "arun.patel@example.com", "first_name": "Arun", "last_name": "Patel"},
	]
	for spec in users:
		user = _get_or_create_user(spec, created)

	consultants = [
		{
			"consultant_name": "Rahul Kumar",
			"user": "rahul.kumar@example.com",
			"specialization": "Accounting",
			"experience_years": 6,
			"modules": [("Accounting", "Expert"), ("HR & Payroll", "Intermediate")],
			"skills": [("Ledger & Books", "Expert"), ("GST Compliance", "Expert"), ("Financial Reports", "Intermediate")],
		},
		{
			"consultant_name": "Priya Sharma",
			"user": "priya.sharma@example.com",
			"specialization": "Selling",
			"experience_years": 4,
			"modules": [("Selling", "Expert"), ("CRM", "Expert")],
			"skills": [("Sales Pipeline", "Expert"), ("Quotations", "Expert"), ("Customer Engagement", "Intermediate")],
		},
		{
			"consultant_name": "Arun Patel",
			"user": "arun.patel@example.com",
			"specialization": "Stock",
			"experience_years": 5,
			"modules": [("Stock", "Expert"), ("Manufacturing", "Intermediate")],
			"skills": [("Inventory", "Expert"), ("Warehouse Operations", "Intermediate"), ("BOM & Routing", "Intermediate")],
		},
	]
	consultant_by_name = {}
	for spec in consultants:
		consultant = _get_or_create_consultant(spec, created)
		consultant_by_name[consultant.consultant_name] = consultant

	# ---------------------------------------------------------------
	# 2. Customers / Lead + contacts
	# ---------------------------------------------------------------
	customers = [
		{"customer_name": "Acme Industries", "email": "finance@acme.test", "phone": "+91-98000-11111", "module": "Accounting"},
		{"customer_name": "Globex Ltd", "email": "sales@globex.test", "phone": "+91-98000-22222", "module": "Selling"},
		{"customer_name": "Initech Corp", "email": "ops@initech.test", "phone": "+91-98000-33333", "module": "Stock"},
		{"customer_name": "Umbrella Labs", "email": "accounts@umbrella.test", "phone": "+91-98000-44444", "module": "Accounting"},
		{"customer_name": "Stark Industries", "email": "crm@stark.test", "phone": "+91-98000-55555", "module": "CRM"},
		{"customer_name": "Wayne Enterprises", "email": "mfg@wayne.test", "phone": "+91-98000-66666", "module": "Manufacturing"},
		{"customer_name": "Aurora Foods", "email": "hr@aurora.test", "phone": "+91-98000-77777", "module": "HR & Payroll"},
	]
	customer_by_name = {}
	for spec in customers:
		customer = _get_or_create_customer(spec, created)
		customer_by_name[customer.customer_name] = customer

	lead = _get_or_create_lead("Fresh Farms Pvt Ltd", "Ramesh Iyer", "ramesh@freshfarms.test", "+91-98000-88888", created)

	# ---------------------------------------------------------------
	# 3. Demo templates per consultant
	# ---------------------------------------------------------------
	templates = [
		{
			"template_name": "Accounting Demo",
			"consultant": consultant_by_name["Rahul Kumar"],
			"module": "Accounting",
			"business_area": "General Ledger",
			"objective": "Show how the customer can run their complete accounting cycle in ERPNext.",
			"agenda": "1. Company setup & chart of accounts 2. Invoicing 3. Bank reconciliation 4. Financial reports",
			"steps": [
				(1, "Open Accounting dashboard and review the chart of accounts", "Chart of Accounts", 5),
				(2, "Create a Sales Invoice and post it", "Sales Invoice", 10),
				(3, "Reconcile a bank statement", "Bank Reconciliation", 10),
				(4, "Generate Profit & Loss and Balance Sheet", "Profit and Loss Statement", 5),
			],
			"features": ["Automated tax templates", "Multi-currency support", "Real-time financial statements"],
			"questions": [("How many transactions do you process per month?", "5000+")],
			"faqs": [("Does this support GST?", "Yes, GST is fully supported out of the box.")],
		},
		{
			"template_name": "GST Compliance Demo",
			"consultant": consultant_by_name["Rahul Kumar"],
			"module": "Accounting",
			"business_area": "GST",
			"objective": "Demonstrate end-to-end GST compliance: invoicing, returns and reports.",
			"agenda": "1. GST settings 2. Tax templates 3. GSTR-1 return 4. HSN summary",
			"steps": [
				(1, "Review GST Settings", "GST Settings", 5),
				(2, "Create an invoice with GST tax template", "Sales Invoice", 10),
				(3, "Open GSTR-1 report and verify entries", "GSTR-1 Report", 10),
			],
			"features": ["GSTR-1 / GSTR-3B ready reports", "HSN-wise summary", "E-invoice integration point"],
			"questions": [("Which GST registration types do you need to support?", "Regular + Composition")],
			"faqs": [],
		},
		{
			"template_name": "Sales Cycle Demo",
			"consultant": consultant_by_name["Priya Sharma"],
			"module": "Selling",
			"business_area": "Order to Payment",
			"objective": "Walk the customer through the complete sales cycle in ERPNext.",
			"agenda": "1. Lead to Quotation 2. Sales Order 3. Delivery 4. Billing & Payment",
			"steps": [
				(1, "Convert a Lead to Customer and create a Quotation", "Quotation", 10),
				(2, "Submit a Sales Order and reserve stock", "Sales Order", 5),
				(3, "Create a Delivery Note and Sales Invoice", "Delivery Note", 10),
			],
			"features": ["Pipeline view of opportunities", "Automatic stock reservation", "Party-wise credit limits"],
			"questions": [("How do you currently handle quotations?", "Email + spreadsheets")],
			"faqs": [("Can we set different price lists per customer?", "Yes, price lists are fully supported.")],
		},
		{
			"template_name": "CRM Lead-to-Quote Demo",
			"consultant": consultant_by_name["Priya Sharma"],
			"module": "CRM",
			"business_area": "Lead Management",
			"objective": "Show lead capture, qualification and conversion into opportunities.",
			"agenda": "1. Lead capture 2. Opportunity pipeline 3. Email integration 4. Reports",
			"steps": [
				(1, "Create a Lead from the CRM module", "Lead", 5),
				(2, "Convert Lead to Customer + Opportunity", "Opportunity", 10),
				(3, "Review the pipeline report", "Opportunity Report", 5),
			],
			"features": ["Lead scoring via custom fields", "Built-in email integration", "Sales pipeline reports"],
			"questions": [("How many leads do you receive every month?", "~200")],
			"faqs": [],
		},
		{
			"template_name": "Stock & Inventory Demo",
			"consultant": consultant_by_name["Arun Patel"],
			"module": "Stock",
			"business_area": "Inventory Control",
			"objective": "Demonstrate inventory management, stock levels and valuation.",
			"agenda": "1. Item master 2. Stock transactions 3. Stock levels & valuation 4. Reports",
			"steps": [
				(1, "Create an Item with multiple warehouses", "Item", 5),
				(2, "Receive stock and issue stock", "Stock Entry", 10),
				(3, "Check stock levels and valuation report", "Stock Balance", 10),
			],
			"features": ["Multi-warehouse support", "Automatic valuation", "Reorder level alerts"],
			"questions": [("How many warehouses do you operate?", "3")],
			"faqs": [("Does it support batch/serial tracking?", "Yes, both batch and serial numbers are supported.")],
		},
	]
	for spec in templates:
		template = _get_or_create_template(spec, created)
		spec["template"] = template

	# ---------------------------------------------------------------
	# 4. Demo Requests across the whole workflow
	# ---------------------------------------------------------------
	# Draft (pipeline start)
	req = _make_request(
		created,
		customer=customer_by_name["Aurora Foods"].name,
		module="Food & Beverage",
		priority="Medium",
		requirements="Evaluate payroll processing and leave management for ~120 employees.",
		preferred_days=12,
	)

	# Requested (no consultant yet) - from a Lead
	req = _make_request(
		created,
		lead=lead.name,
		module="Agriculture",
		priority="Medium",
		requirements="Interested in crop management and farm accounting features.",
		preferred_days=9,
	)
	change_status(req, "Requested", ignore_permissions=True)

	# Assigned (consultant chosen, not scheduled yet)
	req = _make_request(
		created,
		customer=customer_by_name["Acme Industries"].name,
		module="Banking & Finance",
		priority="High",
		consultant=consultant_by_name["Rahul Kumar"],
		requirements="Need a single system for invoicing, bank reconciliation and GST returns across 2 companies.",
		preferred_days=6,
	)
	change_status(req, "Requested", ignore_permissions=True)
	change_status(req, "Assigned", ignore_permissions=True)

	# Scheduled (session with template)
	req = _make_request(
		created,
		customer=customer_by_name["Globex Ltd"].name,
		module="Retail & Supermarket",
		priority="Medium",
		consultant=consultant_by_name["Priya Sharma"],
		requirements="Looking for a full sales cycle solution - quotations, orders, delivery and billing.",
		preferred_days=4,
	)
	change_status(req, "Requested", ignore_permissions=True)
	change_status(req, "Assigned", ignore_permissions=True)
	change_status(req, "Scheduled", ignore_permissions=True)
	session = _make_session(
		created,
		req,
		spec=next(s for s in templates if s["template_name"] == "Sales Cycle Demo"),
		days_ahead=2,
		meeting_link="https://meet.example.com/globex-sales-demo",
	)

	# Demo Completed (no follow-up)
	req = _make_request(
		created,
		customer=customer_by_name["Initech Corp"].name,
		module="Logistics & Transport",
		priority="High",
		consultant=consultant_by_name["Arun Patel"],
		requirements="Inventory control across 3 warehouses with barcode scanning.",
		preferred_days=0,
	)
	change_status(req, "Requested", ignore_permissions=True)
	change_status(req, "Assigned", ignore_permissions=True)
	change_status(req, "Scheduled", ignore_permissions=True)
	session = _make_session(
		created,
		req,
		spec=next(s for s in templates if s["template_name"] == "Stock & Inventory Demo"),
		days_ahead=-3,
		meeting_link="https://meet.example.com/initech-stock-demo",
	)
	_complete_session(
		session,
		feedback={
			"overall_feedback": "Team liked the multi-warehouse and valuation features.",
			"interested": "Interested",
			"requirements_met": "Partially Met",
			"additional_requirements": "Need barcode printing workflow.",
			"follow_up_required": 0,
		},
	)

	# Follow-up Required (completed demo + open follow-up + ToDo)
	req = _make_request(
		created,
		customer=customer_by_name["Umbrella Labs"].name,
		module="Banking & Finance",
		priority="Critical",
		consultant=consultant_by_name["Rahul Kumar"],
		requirements="Urgent: GST migration for the next quarter. Existing data in Tally needs to be migrated.",
		preferred_days=0,
	)
	change_status(req, "Requested", ignore_permissions=True)
	change_status(req, "Assigned", ignore_permissions=True)
	change_status(req, "Scheduled", ignore_permissions=True)
	session = _make_session(
		created,
		req,
		spec=next(s for s in templates if s["template_name"] == "GST Compliance Demo"),
		days_ahead=-1,
		meeting_link="https://meet.example.com/umbrella-gst-demo",
	)
	_complete_session(
		session,
		feedback={
			"overall_feedback": "Good fit for GST; concerned about data migration effort.",
			"interested": "Interested",
			"requirements_met": "Fully Met",
			"follow_up_required": 1,
			"follow_up_date": add_days(today(), 3),
			"next_action": "Share a data migration plan and a pilot migration timeline.",
		},
	)
	fu = _get_open_follow_up(req)
	if fu:
		created["follow_ups"].append(fu.name)

	# Converted (win -> auto-creates an Opportunity)
	req = _make_request(
		created,
		customer=customer_by_name["Stark Industries"].name,
		module="IT Services",
		priority="Medium",
		consultant=consultant_by_name["Priya Sharma"],
		requirements="Central CRM to consolidate leads from marketing and sales.",
		preferred_days=0,
	)
	change_status(req, "Requested", ignore_permissions=True)
	change_status(req, "Assigned", ignore_permissions=True)
	change_status(req, "Scheduled", ignore_permissions=True)
	session = _make_session(
		created,
		req,
		spec=next(s for s in templates if s["template_name"] == "CRM Lead-to-Quote Demo"),
		days_ahead=-5,
		meeting_link="https://meet.example.com/stark-crm-demo",
	)
	_complete_session(
		session,
		feedback={
			"overall_feedback": "Excellent fit, decision makers approved.",
			"interested": "Interested",
			"requirements_met": "Fully Met",
			"follow_up_required": 0,
		},
	)
	change_status(req, "Converted", ignore_permissions=True)
	created["requests"].append(req.name)
	opportunity = frappe.db.get_value(
		"Opportunity", {"custom_demo_request": req.name}, "name"
	)
	if opportunity:
		created["opportunities"].append(opportunity)

	# Not Interested
	req = _make_request(
		created,
		customer=customer_by_name["Wayne Enterprises"].name,
		module="Manufacturing",
		priority="Low",
		consultant=consultant_by_name["Arun Patel"],
		requirements="Evaluated manufacturing module but decided to defer this year.",
		preferred_days=0,
	)
	change_status(req, "Requested", ignore_permissions=True)
	change_status(req, "Assigned", ignore_permissions=True)
	change_status(req, "Scheduled", ignore_permissions=True)
	session = _make_session(
		created,
		req,
		spec=next(s for s in templates if s["template_name"] == "Stock & Inventory Demo"),
		days_ahead=-7,
		meeting_link="https://meet.example.com/wayne-mfg-demo",
	)
	_complete_session(
		session,
		feedback={
			"overall_feedback": "Budget constraints for this financial year.",
			"interested": "Not Interested",
			"requirements_met": "Not Met",
			"follow_up_required": 0,
		},
	)
	change_status(req, "Not Interested", ignore_permissions=True)
	created["requests"].append(req.name)

	frappe.db.commit()

	if verbose:
		print()
		print(_("Sample data created for functional_demo:"))
		for key, items in created.items():
			print("  {0}: {1}".format(key, len(items)))
		print()
		print(_("Consultant logins (demo users, no password set):"))
		for u in created["users"]:
			print("  {0}".format(u))
	return created


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _get_or_create_user(spec, created):
	email = spec["email"]
	if frappe.db.exists("User", email):
		return frappe.get_doc("User", email)
	user = frappe.new_doc("User")
	user.email = email
	user.first_name = spec["first_name"]
	user.last_name = spec.get("last_name")
	user.send_welcome_email = 0
	user.append("roles", {"role": "Functional Consultant"})
	user.insert(ignore_permissions=True)
	created["users"].append(user.name)
	return user


def _get_or_create_consultant(spec, created):
	if frappe.db.exists("Functional Consultant", {"consultant_name": spec["consultant_name"]}):
		return frappe.get_doc("Functional Consultant", {"consultant_name": spec["consultant_name"]})
	doc = frappe.new_doc("Functional Consultant")
	doc.consultant_name = spec["consultant_name"]
	doc.user = spec["user"]
	doc.specialization = spec["specialization"]
	doc.experience_years = spec["experience_years"]
	doc.availability = "Available"
	for module, level in spec["modules"]:
		doc.append("erpnext_modules", {"module": module, "experience_level": level})
	for skill, level in spec["skills"]:
		doc.append("skills", {"skill": skill, "level": level})
	doc.insert(ignore_permissions=True)
	created["consultants"].append(doc.name)
	return doc


def _get_or_create_customer(spec, created):
	if frappe.db.exists("Customer", {"customer_name": spec["customer_name"]}):
		customer = frappe.get_doc("Customer", {"customer_name": spec["customer_name"]})
	else:
		customer = frappe.new_doc("Customer")
		customer.customer_name = spec["customer_name"]
		customer.customer_group = "All Customer Groups"
		customer.territory = "All Territories"
		customer.insert(ignore_permissions=True)
		created["customers"].append(customer.name)

	# contact
	if not frappe.db.exists(
		"Contact",
		{"first_name": spec["customer_name"]},  # name placeholder; use Dynamic Link match below
	):
		contact = frappe.new_doc("Contact")
		contact.first_name = spec["customer_name"]
		contact.email_id = spec["email"]
		contact.mobile_no = spec["phone"]
		contact.is_primary_contact = 1
		contact.append(
			"links",
			{"link_doctype": "Customer", "link_name": customer.name, "link_title": customer.customer_name},
		)
		contact.insert(ignore_permissions=True)
		created["contacts"].append(contact.name)
	return customer


def _get_or_create_lead(company_name, lead_name, email, phone, created):
	if frappe.db.exists("Lead", {"company_name": company_name}):
		return frappe.get_doc("Lead", {"company_name": company_name})
	lead = frappe.new_doc("Lead")
	lead.lead_name = lead_name
	lead.company_name = company_name
	lead.email_id = email
	lead.mobile_no = phone
	lead.status = "Open"
	lead.insert(ignore_permissions=True)
	created["leads"].append(lead.name)
	return lead


def _get_or_create_template(spec, created):
	name = spec["template_name"]
	if frappe.db.exists("Functional Demo Template", {"template_name": name}):
		return frappe.get_doc("Functional Demo Template", {"template_name": name})
	doc = frappe.new_doc("Functional Demo Template")
	doc.template_name = name
	doc.functional_consultant = spec["consultant"].name
	doc.erpnext_module = spec["module"]
	doc.business_area = spec["business_area"]
	doc.demo_objective = spec["objective"]
	doc.demo_agenda = spec["agenda"]
	for step_no, description, screen, minutes in spec["steps"]:
		doc.append(
			"demo_steps",
			{"step_no": step_no, "description": description, "doctype_to_demo": screen, "duration_min": minutes},
		)
	for feature in spec["features"]:
		doc.append("key_features", {"item": feature})
	for question, answer in spec["questions"]:
		doc.append("questions_to_ask", {"question": question, "answer": answer})
	for question, answer in spec["faqs"]:
		doc.append("faqs", {"question": question, "answer": answer})
	doc.is_active = 1
	doc.insert(ignore_permissions=True)
	created["templates"].append(doc.name)
	return doc


def _make_request(created, customer=None, lead=None, module=None, priority="Medium",
				  consultant=None, requirements=None, preferred_days=0):
	doc = frappe.new_doc("Demo Request")
	if customer:
		doc.customer = customer
	if lead:
		doc.lead = lead
	doc.interested_module = module
	doc.priority = priority
	doc.customer_requirements = requirements
	doc.preferred_demo_date = add_days(today(), preferred_days)
	if consultant:
		doc.functional_consultant = consultant.name
	doc.insert(ignore_permissions=True)
	created["requests"].append(doc.name)
	return doc


def _make_session(created, request, spec=None, days_ahead=2, meeting_link=None):
	session = frappe.new_doc("Demo Session")
	session.demo_request = request.name
	session.scheduled_date = add_days(today(), days_ahead)
	session.start_time = "10:00:00"
	session.end_time = "11:00:00"
	session.meeting_link = meeting_link or "https://meet.example.com/demo"
	if spec and spec.get("template"):
		session.demo_template = spec["template"].name
	session.insert(ignore_permissions=True)
	created["sessions"].append(session.name)
	return session


def _complete_session(session, feedback):
	session.start_demo()
	session.complete_demo(feedback)


def _get_open_follow_up(request):
	return frappe.db.get_value(
		"Demo Follow Up",
		{"demo_request": request.name, "status": ["in", ["Open", "In Progress"]]},
		"name",
		as_dict=True,
	)


if __name__ == "__main__":
	setup_demo_data()
