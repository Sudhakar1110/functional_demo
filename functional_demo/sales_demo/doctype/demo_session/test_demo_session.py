# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from functional_demo.sales_demo.doctype.demo_request.demo_request import change_status
from functional_demo.sales_demo.doctype.demo_request.test_demo_request import make_demo_request
from functional_demo.sales_demo.doctype.functional_consultant.test_functional_consultant import (
	make_consultant,
)
from functional_demo.sales_demo.doctype.functional_demo_template.test_functional_demo_template import (
	make_template,
)


def make_session(demo_request, scheduled_date=None, template=None):
	session = frappe.new_doc("Demo Session")
	session.demo_request = demo_request.name
	session.scheduled_date = scheduled_date or add_days(today(), 2)
	if template:
		session.demo_template = template.name
	session.insert(ignore_permissions=True)
	return session


class TestDemoSession(FrappeTestCase):
	def setUp(self):
		self.consultant = make_consultant()
		self.request = make_demo_request(consultant=self.consultant.name)
		change_status(self.request, "Requested", ignore_permissions=True)
		change_status(self.request, "Assigned", ignore_permissions=True)
		self.template = make_template(self.consultant, name="Session Test Template")

	def test_session_creation_snapshots_template(self):
		session = make_session(self.request, template=self.template)
		self.assertEqual(session.customer_requirements, self.request.customer_requirements)
		self.assertTrue(session.template_sections, "Template snapshot should be copied")
		self.assertEqual(session.template_sections[0].section, "Demo Objective")

	def test_master_template_changes_do_not_affect_session(self):
		session = make_session(self.request, template=self.template)
		content_before = [{"section": s.section, "content": s.content} for s in session.template_sections]

		# change the master template
		self.template.demo_objective = "Brand new objective after the session."
		self.template.save(ignore_permissions=True)

		session.reload()
		content_after = [{"section": s.section, "content": s.content} for s in session.template_sections]
		self.assertEqual(content_before, content_after)

	def test_full_demo_lifecycle(self):
		session = make_session(self.request, template=self.template)
		change_status(self.request, "Scheduled", ignore_permissions=True)

		session.start_demo()
		self.assertEqual(session.demo_status, "In Progress")
		self.request.reload()
		self.assertEqual(self.request.status, "Demo In Progress")

		session.complete_demo(
			{
				"overall_feedback": "Great response",
				"interested": "Interested",
				"requirements_met": "Partially Met",
				"follow_up_required": 1,
				"follow_up_date": add_days(today(), 5),
				"demo_feedback_items": [
					{"item_type": "Question", "description": "Can it handle multi-company?"}
				],
			}
		)
		session.reload()
		self.assertEqual(session.demo_status, "Completed")
		self.assertEqual(session.demo_feedback_items[0].description, "Can it handle multi-company?")
		self.request.reload()
		self.assertEqual(self.request.status, "Follow-up Required")
		self.assertTrue(frappe.db.exists("Demo Follow Up", {"demo_session": session.name}))
