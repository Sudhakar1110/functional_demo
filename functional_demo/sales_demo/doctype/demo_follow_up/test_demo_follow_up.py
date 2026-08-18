# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from functional_demo.sales_demo.doctype.demo_request.test_demo_request import make_demo_request
from functional_demo.sales_demo.doctype.functional_consultant.test_functional_consultant import (
	make_consultant,
)


def make_follow_up(demo_request, follow_up_date=None, **kwargs):
	doc = frappe.new_doc("Demo Follow Up")
	doc.demo_request = demo_request.name
	doc.customer = demo_request.customer
	doc.sales_person = demo_request.sales_person
	doc.follow_up_date = follow_up_date or add_days(today(), 3)
	doc.update(kwargs)
	doc.insert(ignore_permissions=True)
	return doc


def _make_user(email, first_name, roles):
	"""Create an enabled user carrying the given roles for permission tests."""
	user = frappe.new_doc("User")
	user.email = email
	user.first_name = first_name
	user.enabled = 1
	user.add_roles(*roles)
	user.insert(ignore_permissions=True)
	return user.name


class TestDemoFollowUp(FrappeTestCase):
	def setUp(self):
		self.consultant = make_consultant()

	def test_follow_up_creation_with_todo(self):
		request = make_demo_request(consultant=self.consultant.name)
		fu = make_follow_up(request)
		self.assertEqual(fu.status, "Open")
		self.assertTrue(fu.assigned_to)
		self.assertTrue(frappe.db.exists("ToDo", {"reference_type": "Demo Follow Up", "reference_name": fu.name}))

	def test_mark_overdue(self):
		request = make_demo_request(consultant=self.consultant.name)
		fu = make_follow_up(request, follow_up_date=add_days(today(), -2))
		from functional_demo.install import mark_overdue_follow_ups

		mark_overdue_follow_ups()
		fu.reload()
		self.assertEqual(fu.status, "Overdue")

	def test_completion_closes_todo(self):
		request = make_demo_request(consultant=self.consultant.name)
		fu = make_follow_up(request)
		fu.status = "Completed"
		fu.save(ignore_permissions=True)
		todo_status = frappe.db.get_value(
			"ToDo", {"reference_type": "Demo Follow Up", "reference_name": fu.name}, "status"
		)
		self.assertEqual(todo_status, "Closed")

	# --- follow-ups are sales-team-only --------------------------------

	def test_functional_consultant_cannot_access_follow_up(self):
		user = _make_user("fc.access@example.com", "FC", ["Functional Consultant"])
		request = make_demo_request(consultant=self.consultant.name)
		fu = make_follow_up(request)
		frappe.set_user(user)
		try:
			self.assertFalse(frappe.has_permission("Demo Follow Up", doc=fu, ptype="read"))
			self.assertEqual(frappe.get_all("Demo Follow Up", filters={"name": fu.name}), [])
			# the sales-only creation guard rejects functional users too
			from functional_demo.api import create_demo_follow_up

			with self.assertRaises(frappe.PermissionError):
				create_demo_follow_up(
					demo_request=request.name, follow_up_date=add_days(today(), 3)
				)
		finally:
			frappe.set_user("Administrator")

	def test_functional_team_manager_cannot_access_follow_up(self):
		user = _make_user("ftm.access@example.com", "FTM", ["Functional Team Manager"])
		request = make_demo_request(consultant=self.consultant.name)
		fu = make_follow_up(request)
		frappe.set_user(user)
		try:
			self.assertFalse(frappe.has_permission("Demo Follow Up", doc=fu, ptype="read"))
			self.assertEqual(frappe.get_all("Demo Follow Up", filters={"name": fu.name}), [])
		finally:
			frappe.set_user("Administrator")

	def test_sales_user_assigned_to_follow_up_can_access(self):
		user = _make_user("sales.access@example.com", "Sales", ["Sales User"])
		request = make_demo_request(consultant=self.consultant.name)
		fu = make_follow_up(request)
		frappe.db.set_value("Demo Follow Up", fu.name, "assigned_to", user)
		fu.reload()
		frappe.set_user(user)
		try:
			self.assertTrue(frappe.has_permission("Demo Follow Up", doc=fu, ptype="read"))
			self.assertEqual(
				[r.name for r in frappe.get_all("Demo Follow Up", filters={"name": fu.name})],
				[fu.name],
			)
		finally:
			frappe.set_user("Administrator")

	def test_sales_user_unrelated_to_follow_up_cannot_access(self):
		user = _make_user("sales.other@example.com", "Sales", ["Sales User"])
		request = make_demo_request(consultant=self.consultant.name)
		fu = make_follow_up(request)
		frappe.set_user(user)
		try:
			self.assertFalse(frappe.has_permission("Demo Follow Up", doc=fu, ptype="read"))
			self.assertEqual(frappe.get_all("Demo Follow Up", filters={"name": fu.name}), [])
		finally:
			frappe.set_user("Administrator")
