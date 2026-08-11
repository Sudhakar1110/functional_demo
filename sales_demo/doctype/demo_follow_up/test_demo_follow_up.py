# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from functional_demo.sales_demo.doctype.demo_request.test_demo_request import make_demo_request


def make_follow_up(demo_request, follow_up_date=None, **kwargs):
	doc = frappe.new_doc("Demo Follow Up")
	doc.demo_request = demo_request.name
	doc.customer = demo_request.customer
	doc.sales_person = demo_request.sales_person
	doc.follow_up_date = follow_up_date or add_days(today(), 3)
	doc.update(kwargs)
	doc.insert(ignore_permissions=True)
	return doc


class TestDemoFollowUp(FrappeTestCase):
	def test_follow_up_creation_with_todo(self):
		request = make_demo_request()
		fu = make_follow_up(request)
		self.assertEqual(fu.status, "Open")
		self.assertTrue(fu.assigned_to)
		self.assertTrue(frappe.db.exists("ToDo", {"reference_type": "Demo Follow Up", "reference_name": fu.name}))

	def test_mark_overdue(self):
		request = make_demo_request()
		fu = make_follow_up(request, follow_up_date=add_days(today(), -2))
		from functional_demo.install import mark_overdue_follow_ups

		mark_overdue_follow_ups()
		fu.reload()
		self.assertEqual(fu.status, "Overdue")

	def test_completion_closes_todo(self):
		request = make_demo_request()
		fu = make_follow_up(request)
		fu.status = "Completed"
		fu.save(ignore_permissions=True)
		todo_status = frappe.db.get_value(
			"ToDo", {"reference_type": "Demo Follow Up", "reference_name": fu.name}, "status"
		)
		self.assertEqual(todo_status, "Closed")
