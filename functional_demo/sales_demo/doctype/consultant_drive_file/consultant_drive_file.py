# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class ConsultantDriveFile(Document):
	"""A file in the shared consultant Drive.

	The Drive is a team library: every Functional Consultant / Functional Team
	Manager sees and manages the same files (there is deliberately no
	per-owner row filter). The actual bytes live in a private `File` record
	pointed at by `file`; `on_trash` removes it together with this entry so
	the Drive never leaves orphaned files behind.
	"""

	def validate(self):
		if not self.uploaded_by:
			self.uploaded_by = frappe.session.user
		if not self.uploaded_on:
			self.uploaded_on = now_datetime()

	def on_trash(self):
		# remove the backing File record together with the Drive entry
		file_doc = frappe.db.get_value("File", {"file_url": self.file}, "name")
		if file_doc:
			frappe.get_doc("File", file_doc).delete(ignore_permissions=True)
