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

	def test_completing_session_walks_request_from_scheduled(self):
		# completing a session without starting it first (e.g. bulk import or a
		# direct desk edit) must walk the request Scheduled -> Demo In Progress
		# -> Demo Completed even though no direct transition exists
		session = make_session(self.request, template=self.template)
		change_status(self.request, "Scheduled", ignore_permissions=True)
		session.demo_status = "Completed"
		session.save(ignore_permissions=True)
		self.request.reload()
		self.assertEqual(self.request.status, "Demo Completed")

	def test_reschedule_records_history(self):
		"""Rescheduling a session must create a history entry."""
		session = make_session(self.request, template=self.template)
		original_date = session.scheduled_date
		original_start = session.start_time
		change_status(self.request, "Scheduled", ignore_permissions=True)

		new_date = add_days(today(), 10)
		session.reschedule_demo(new_date, "11:00:00", "12:00:00")

		session.reload()
		self.assertEqual(session.demo_status, "Rescheduled")
		self.assertEqual(session.reschedule_count, 1)
		self.assertEqual(session.scheduled_date, new_date)
		self.assertEqual(session.start_time, "11:00:00")
		self.assertEqual(session.end_time, "12:00:00")

		# Verify history child table was populated
		self.assertEqual(len(session.reschedule_history), 1)
		history = session.reschedule_history[0]
		self.assertEqual(history.reschedule_number, 1)
		self.assertEqual(history.old_date, original_date)
		self.assertEqual(history.new_date, new_date)
		self.assertEqual(history.new_start_time, "11:00:00")
		self.assertEqual(history.new_end_time, "12:00:00")
		self.assertEqual(history.rescheduled_by, frappe.session.user)

		# Second reschedule
		newer_date = add_days(today(), 20)
		session.reschedule_demo(newer_date, "14:00:00", "15:00:00")
		session.reload()
		self.assertEqual(session.reschedule_count, 2)
		self.assertEqual(len(session.reschedule_history), 2)
		second = session.reschedule_history[1]
		self.assertEqual(second.reschedule_number, 2)
		self.assertEqual(second.old_date, new_date)
		self.assertEqual(second.new_date, newer_date)

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
