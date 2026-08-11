# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document


class FunctionalConsultant(Document):
	def validate(self):
		self.validate_user()
		self.validate_availability_times()

	def on_update(self):
		self.ensure_consultant_role()

	# ------------------------------------------------------------------
	# validations
	# ------------------------------------------------------------------

	def validate_user(self):
		if not frappe.db.exists("User", self.user):
			frappe.throw(_("User {0} does not exist. Please create the user first.").format(self.user))

	def validate_availability_times(self):
		if self.available_from and self.available_to and self.available_from >= self.available_to:
			frappe.throw(
				_("Available From must be earlier than Available To for consultant {0}.").format(
					self.consultant_name
				)
			)

	def ensure_consultant_role(self):
		"""Automatically grant the Functional Consultant role to the linked user."""
		if self.status != "Active":
			return
		assign_consultant_role(self.user)


def assign_consultant_role(user):
	"""Add the Functional Consultant role to a user (idempotent)."""
	if not user or user == "Administrator":
		return
	if "Functional Consultant" in frappe.get_roles(user):
		return
	try:
		user_doc = frappe.get_doc("User", user)
		user_doc.append("roles", {"role": "Functional Consultant"})
		user_doc.save(ignore_permissions=True)
	except Exception:
		frappe.log_error(title=_("Could not assign Functional Consultant role"), message=frappe.get_traceback())


# ------------------------------------------------------------------
# permission filters
# ------------------------------------------------------------------

def get_permission_query_conditions(user=None):
	"""Consultants only see their own consultant record; all others unrestricted."""
	user = user or frappe.session.user
	if not user or user == "Administrator":
		return ""
	roles = frappe.get_roles(user)
	if any(r in roles for r in ("System Manager", "Functional Team Manager", "Sales User", "Sales Manager")):
		return ""
	if "Functional Consultant" in roles:
		return "(`tabFunctional Consultant`.`user` = {0})".format(frappe.db.escape(user))
	return ""


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	if any(r in roles for r in ("System Manager", "Functional Team Manager", "Sales User", "Sales Manager")):
		return True
	if "Functional Consultant" in roles:
		return doc.get("user") == user
	return False
