# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from functional_demo.portal import create_notification


class DemoFollowUp(Document):
	def validate(self):
		if not self.subject:
			self.subject = _("Follow-up for {0}").format(self.customer or self.demo_request)
		if not self.assigned_to:
			self.assigned_to = self.sales_person or frappe.session.user

	def after_insert(self):
		self.assign_todo()
		self.notify_sales_person()

	def on_update(self):
		# on_update runs AFTER the db write in v15, so the pre-save value
		# must come from get_doc_before_save() (db_get returns the new value)
		before = self.get_doc_before_save()
		old_status = before.get("status") if before else None
		if old_status and old_status != self.status:
			if self.status == "Completed":
				self.close_open_todos()

	# ------------------------------------------------------------------

	def assign_todo(self):
		if not self.assigned_to or self.assigned_to == "Administrator":
			return
		if frappe.db.exists(
			"ToDo",
			{"reference_type": "Demo Follow Up", "reference_name": self.name, "status": ["in", ["Open", "Overdue"]]},
		):
			return
		todo = frappe.new_doc("ToDo")
		todo.description = _(
			"Follow up on {0} for {1} (follow-up date: {2}). Next action: {3}"
		).format(self.demo_request, self.customer or "-", self.follow_up_date, self.next_action or "-")
		todo.reference_type = "Demo Follow Up"
		todo.reference_name = self.name
		todo.role = "Sales User"
		todo.owner = self.assigned_to
		todo.insert(ignore_permissions=True)

	def notify_sales_person(self):
		"""Email the sales person that a follow-up was created for their demo.

		Fires from after_insert, so it covers follow-ups created from the portal
		request page, from a completed demo session, and the auto-created
		follow-up when a demo completes with follow-up required. A mail failure
		is logged but never blocks the follow-up creation."""
		try:
			sales_person = self.sales_person or self.assigned_to
			if not sales_person:
				return
			# in-app notification (portal + desk bells) - created even when the
			# sales person has no email (e.g. Administrator)
			create_notification(
				sales_person,
				_("Follow-up created for {0} (Demo Request {1})").format(
					self.customer or "-", self.demo_request or "-"
				),
				"Demo Follow Up",
				self.name,
			)
			email = frappe.db.get_value("User", sales_person, "email")
			if not email:
				return
			subject = _("Follow-up created for {0}").format(self.customer or self.demo_request)
			message = _(
				"Hi,\n\n"
				"A follow-up has been created for {0} (Demo Request {1}).\n\n"
				"Follow-up date: {2}\n"
				"Next action: {3}\n"
				"Assigned to: {4}\n\n"
				"Open the follow-up: {5}\n"
			).format(
				self.customer or "-",
				self.demo_request or "-",
				self.follow_up_date or "-",
				self.next_action or "-",
				self.assigned_to or "-",
				frappe.utils.get_url("/app/demo-follow-up/{0}".format(self.name)),
			)
			frappe.sendmail(
				recipients=[email],
				subject=subject,
				message=message,
				reference_doctype="Demo Follow Up",
				reference_name=self.name,
				now=True,
			)
		except Exception:
			# never block follow-up creation because the email could not be sent
			frappe.log_error(
				title=_("Follow-up email to {0} failed for {1}").format(
					self.sales_person or "-", self.name
				),
				message=frappe.get_traceback(),
			)

	def close_open_todos(self):
		frappe.db.set_value(
			"ToDo",
			{"reference_type": "Demo Follow Up", "reference_name": self.name, "status": ["in", ["Open", "Overdue"]]},
			"status",
			"Closed",
		)

	def add_discussion_note(self, note):
		if not note:
			return
		self.append(
			"discussion_notes",
			{"note_date": now_datetime(), "note_by": frappe.session.user, "note": note},
		)
		self.save(ignore_permissions=True)


# ------------------------------------------------------------------
# permission filters
# ------------------------------------------------------------------

def get_permission_query_conditions(user=None):
	"""Sales users see follow-ups assigned to them or on their requests;
	consultants see follow-ups on their demos; managers see everything."""
	user = user or frappe.session.user
	if not user or user == "Administrator":
		return ""
	roles = frappe.get_roles(user)
	if any(r in roles for r in ("System Manager", "Sales Manager", "Functional Team Manager")):
		return ""
	if "Sales User" in roles:
		return (
			"(`tabDemo Follow Up`.`assigned_to` = {0} or `tabDemo Follow Up`.`owner` = {0} "
			"or `tabDemo Follow Up`.`demo_request` in "
			"(select `tabDemo Request`.`name` from `tabDemo Request` "
			"where `tabDemo Request`.`sales_person` = {0} or `tabDemo Request`.`owner` = {0}))"
		).format(frappe.db.escape(user))
	if "Functional Consultant" in roles:
		return (
			"(`tabDemo Follow Up`.`functional_consultant` in "
			"(select `tabFunctional Consultant`.`name` from `tabFunctional Consultant` "
			"where `tabFunctional Consultant`.`user` = {0}))"
		).format(frappe.db.escape(user))
	return ""


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	if any(r in roles for r in ("System Manager", "Sales Manager", "Functional Team Manager")):
		return True
	if "Sales User" in roles:
		if doc.get("assigned_to") == user or doc.get("owner") == user:
			return True
		if doc.get("demo_request"):
			request = frappe.db.get_value(
				"Demo Request", doc.get("demo_request"), ["sales_person", "owner"], as_dict=True
			)
			if request and (request.sales_person == user or request.owner == user):
				return True
		return False
	if "Functional Consultant" in roles and doc.get("functional_consultant"):
		consultant_user = frappe.db.get_value(
			"Functional Consultant", doc.get("functional_consultant"), "user"
		)
		return consultant_user == user
	return False
