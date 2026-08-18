# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe.tests.utils import FrappeTestCase


def make_drive_file(title="Pricing Deck", **kwargs):
	doc = frappe.new_doc("Consultant Drive File")
	doc.title = title
	doc.file = "/private/files/test.txt"
	doc.update(kwargs)
	doc.insert(ignore_permissions=True)
	return doc


def _make_user(email, first_name, roles):
	user = frappe.new_doc("User")
	user.email = email
	user.first_name = first_name
	user.enabled = 1
	user.add_roles(*roles)
	user.insert(ignore_permissions=True)
	return user.name


class TestConsultantDriveFile(FrappeTestCase):
	def test_functional_consultant_can_access_drive(self):
		user = _make_user("fc.drive@example.com", "FC", ["Functional Consultant"])
		f = make_drive_file()
		frappe.set_user(user)
		try:
			self.assertTrue(frappe.has_permission("Consultant Drive File", doc=f, ptype="read"))
			self.assertEqual(
				[r.name for r in frappe.get_all("Consultant Drive File", filters={"name": f.name})],
				[f.name],
			)
		finally:
			frappe.set_user("Administrator")

	def test_functional_team_manager_can_access_drive(self):
		user = _make_user("ftm.drive@example.com", "FTM", ["Functional Team Manager"])
		f = make_drive_file()
		frappe.set_user(user)
		try:
			self.assertTrue(frappe.has_permission("Consultant Drive File", doc=f, ptype="read"))
		finally:
			frappe.set_user("Administrator")

	def test_sales_user_cannot_access_drive(self):
		user = _make_user("sales.drive@example.com", "Sales", ["Sales User"])
		f = make_drive_file()
		frappe.set_user(user)
		try:
			self.assertFalse(frappe.has_permission("Consultant Drive File", doc=f, ptype="read"))
			self.assertEqual(frappe.get_all("Consultant Drive File", filters={"name": f.name}), [])
		finally:
			frappe.set_user("Administrator")

	def test_sales_manager_cannot_access_drive(self):
		user = _make_user("sm.drive@example.com", "SM", ["Sales Manager"])
		f = make_drive_file()
		frappe.set_user(user)
		try:
			self.assertFalse(frappe.has_permission("Consultant Drive File", doc=f, ptype="read"))
			self.assertEqual(frappe.get_all("Consultant Drive File", filters={"name": f.name}), [])
		finally:
			frappe.set_user("Administrator")

	# --- delete is uploader-only ---------------------------------------

	def test_only_uploader_can_delete_own_file(self):
		uploader = _make_user("drive.uploader@example.com", "Uploader", ["Functional Consultant"])
		other = _make_user("drive.other@example.com", "Other", ["Functional Consultant"])
		f = make_drive_file(uploaded_by=uploader)

		frappe.set_user(uploader)
		try:
			self.assertTrue(frappe.has_permission("Consultant Drive File", doc=f, ptype="delete"))
		finally:
			frappe.set_user("Administrator")

		frappe.set_user(other)
		try:
			# another consultant can still view/download, but cannot delete
			self.assertTrue(frappe.has_permission("Consultant Drive File", doc=f, ptype="read"))
			self.assertFalse(frappe.has_permission("Consultant Drive File", doc=f, ptype="delete"))
		finally:
			frappe.set_user("Administrator")

	def test_functional_team_manager_cannot_delete_others_file(self):
		uploader = _make_user("drive.uploader2@example.com", "Uploader", ["Functional Consultant"])
		ftm = _make_user("drive.ftm2@example.com", "FTM", ["Functional Team Manager"])
		f = make_drive_file(uploaded_by=uploader)

		frappe.set_user(ftm)
		try:
			self.assertTrue(frappe.has_permission("Consultant Drive File", doc=f, ptype="read"))
			self.assertFalse(frappe.has_permission("Consultant Drive File", doc=f, ptype="delete"))
		finally:
			frappe.set_user("Administrator")
