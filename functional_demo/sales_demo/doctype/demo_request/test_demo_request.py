# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe.tests.utils import FrappeTestCase

from functional_demo.sales_demo.doctype.functional_consultant.test_functional_consultant import (
	make_consultant,
)
from functional_demo.sales_demo.doctype.demo_request.demo_request import change_status


def make_demo_request(customer=None, lead=None, consultant=None, **kwargs):
	"""Create a Demo Request; creates a Customer automatically if none is given.

	A Functional Consultant is mandatory for every new request (same rule as the
	portal), so tests pass one explicitly."""
	if not customer and not lead:
		customer = frappe.new_doc("Customer", customer_name="Test Customer").insert(ignore_permissions=True).name
	doc = frappe.new_doc("Demo Request")
	if customer:
		doc.customer = customer
	if lead:
		doc.lead = lead
	if consultant:
		doc.functional_consultant = consultant
	doc.interested_module = "Law Management"
	doc.priority = "High"
	doc.update(kwargs)
	doc.insert(ignore_permissions=True)
	return doc


class TestDemoRequest(FrappeTestCase):
	def setUp(self):
		self.consultant = make_consultant()

	def test_create_request_with_default_sales_person(self):
		doc = make_demo_request(consultant=self.consultant.name)
		self.assertEqual(doc.sales_person, frappe.session.user)
		self.assertEqual(doc.status, "Draft")

	def test_workflow_transition(self):
		doc = make_demo_request(consultant=self.consultant.name)
		doc = change_status(doc, "Requested", ignore_permissions=True)
		doc = change_status(doc, "Assigned", ignore_permissions=True)
		self.assertEqual(doc.status, "Assigned")

	def test_portal_create_jumps_draft_to_assigned(self):
		# the sales portal creates a request with a consultant and moves it
		# straight to Assigned in one call - the path walker must apply the
		# intermediate Requested state on the way (Draft -> Requested -> Assigned)
		doc = make_demo_request(consultant=self.consultant.name)
		self.assertEqual(doc.status, "Draft")
		doc = change_status(doc, "Assigned", ignore_permissions=True)
		self.assertEqual(doc.status, "Assigned")
		self.assertEqual(doc.workflow_state, "Assigned")

	def test_invalid_transition_is_blocked(self):
		doc = make_demo_request(consultant=self.consultant.name)
		with self.assertRaises(frappe.ValidationError):
			change_status(doc, "Converted", ignore_permissions=True)

	def test_consultant_required_at_creation(self):
		# the business rule matches the portal: a new Demo Request must have
		# a Functional Consultant from the very first save
		with self.assertRaises(frappe.ValidationError):
			make_demo_request()
