# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

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
		# straight to Assigned in one call - the direct Draft -> Assigned
		# transition means the intermediate Requested state is never recorded
		doc = make_demo_request(consultant=self.consultant.name)
		self.assertEqual(doc.status, "Draft")
		doc = change_status(doc, "Assigned", ignore_permissions=True)
		self.assertEqual(doc.status, "Assigned")
		self.assertEqual(doc.workflow_state, "Assigned")
		status_changes = [
			row.remarks
			for row in (doc.get("demo_request_activity") or [])
			if row.activity_type == "Status Changed"
		]
		self.assertIn("Draft -> Assigned", status_changes)
		self.assertNotIn("Draft -> Requested", status_changes)
		self.assertNotIn("Requested -> Assigned", status_changes)

	def test_invalid_transition_is_blocked(self):
		doc = make_demo_request(consultant=self.consultant.name)
		with self.assertRaises(frappe.ValidationError):
			change_status(doc, "Converted", ignore_permissions=True)

	def test_consultant_required_at_creation(self):
		# the business rule matches the portal: a new Demo Request must have
		# a Functional Consultant from the very first save
		with self.assertRaises(frappe.ValidationError):
			make_demo_request()

	# --- trial period (converted leads) -------------------------------

	def test_trial_end_before_start_is_rejected(self):
		doc = make_demo_request(consultant=self.consultant.name)
		doc.trial_start_date = add_days(today(), 2)
		doc.trial_end_date = add_days(today(), 1)
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	def test_valid_trial_period_is_saved(self):
		doc = make_demo_request(consultant=self.consultant.name)
		doc.trial_start_date = add_days(today(), -14)
		doc.trial_end_date = add_days(today(), 14)
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.trial_end_date, add_days(today(), 14))

	def test_set_trial_period_api_rejects_functional_user(self):
		user = frappe.new_doc("User")
		user.email = "fc.trial@example.com"
		user.first_name = "FC Trial"
		user.enabled = 1
		user.add_roles("Functional Consultant")
		user.insert(ignore_permissions=True)

		doc = make_demo_request(consultant=self.consultant.name)
		frappe.set_user(user.name)
		try:
			from functional_demo.api import set_trial_period

			with self.assertRaises(frappe.PermissionError):
				set_trial_period(
					demo_request=doc.name,
					trial_start_date=add_days(today(), -7),
					trial_end_date=add_days(today(), 7),
				)
		finally:
			frappe.set_user("Administrator")

	def test_set_trial_period_api_allows_sales_user(self):
		user = frappe.new_doc("User")
		user.email = "sales.trial@example.com"
		user.first_name = "Sales Trial"
		user.enabled = 1
		user.add_roles("Sales User")
		user.insert(ignore_permissions=True)

		doc = make_demo_request(consultant=self.consultant.name, sales_person=user.name)
		frappe.set_user(user.name)
		try:
			from functional_demo.api import set_trial_period

			res = set_trial_period(
				demo_request=doc.name,
				trial_start_date=add_days(today(), -7),
				trial_end_date=add_days(today(), 7),
			)
			self.assertEqual(res["trial_end_date"], add_days(today(), 7))
		finally:
			frappe.set_user("Administrator")

	def test_trial_reminder_job_reminds_sales_person_once(self):
		# walk the workflow to Converted (the cap is 3 transitions per call)
		doc = make_demo_request(consultant=self.consultant.name)
		doc = change_status(doc, "Assigned", ignore_permissions=True)
		doc = change_status(doc, "Scheduled", ignore_permissions=True)
		doc = change_status(doc, "Demo In Progress", ignore_permissions=True)
		doc = change_status(doc, "Demo Completed", ignore_permissions=True)
		doc = change_status(doc, "Converted", ignore_permissions=True)
		self.assertEqual(doc.status, "Converted")

		doc.trial_start_date = add_days(today(), -14)
		doc.trial_end_date = add_days(today(), 1)  # ends tomorrow -> reminder due
		doc.save(ignore_permissions=True)

		from functional_demo.install import send_trial_period_reminders

		send_trial_period_reminders()
		doc.reload()
		self.assertEqual(doc.trial_reminder_sent, 1)
		# the sales person got an in-app notification about the trial ending
		self.assertTrue(
			frappe.db.exists(
				"Notification Log",
				{
					"for_user": doc.sales_person,
					"document_type": "Demo Request",
					"document_name": doc.name,
				},
			)
		)

		# running again does not double-notify (flag already set)
		send_trial_period_reminders()
		doc.reload()
		self.assertEqual(doc.trial_reminder_sent, 1)
