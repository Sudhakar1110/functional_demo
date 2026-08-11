# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe.tests.utils import FrappeTestCase


def make_consultant(user="Administrator", consultant_name=None, **kwargs):
	if frappe.db.exists("Functional Consultant", {"user": user}):
		return frappe.get_doc("Functional Consultant", {"user": user})

	doc = frappe.new_doc("Functional Consultant")
	doc.consultant_name = consultant_name or "Test Consultant"
	doc.user = user
	doc.specialization = "Accounting"
	doc.append("erpnext_modules", {"module": "Accounting", "experience_level": "Expert"})
	doc.update(kwargs)
	doc.insert(ignore_permissions=True)
	return doc


class TestFunctionalConsultant(FrappeTestCase):
	def test_consultant_creation(self):
		consultant = make_consultant()
		self.assertEqual(consultant.status, "Active")
		self.assertEqual(consultant.erpnext_modules[0].module, "Accounting")

	def test_inactive_consultant_flag(self):
		consultant = make_consultant(consultant_name="Test Consultant 2")
		consultant.status = "Inactive"
		consultant.save(ignore_permissions=True)
		self.assertEqual(consultant.status, "Inactive")
