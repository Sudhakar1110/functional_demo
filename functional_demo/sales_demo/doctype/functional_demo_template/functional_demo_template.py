# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document


class FunctionalDemoTemplate(Document):
	def validate(self):
		self.validate_consultant()

	def validate_consultant(self):
		if not self.functional_consultant and frappe.session.user == "Administrator":
			# same behaviour as the portal: Administrator gets a consultant
			# profile auto-created on first use, so desk template creation works
			# out of the box without manual ERPNext setup
			from functional_demo.portal import _ensure_admin_consultant

			self.functional_consultant = _ensure_admin_consultant()
		if not self.functional_consultant:
			frappe.throw(_("Please select the Functional Consultant who owns this template."))
		status = frappe.db.get_value(
			"Functional Consultant", self.functional_consultant, "status"
		)
		if status and status != "Active":
			frappe.throw(
				_("Templates can only be created for Active consultants. {0} is {1}.").format(
					self.functional_consultant, status
				)
			)


def get_template_snapshot(template_name):
	"""Build an immutable list of {section, content} pairs from a template.

	Demo Sessions copy this snapshot so that later edits to the master template
	never change historical sessions.
	"""
	template = frappe.get_doc("Functional Demo Template", template_name)
	sections = []

	def add(section, content):
		if content:
			sections.append({"section": section, "content": content})

	def steps_text(rows):
		lines = []
		for step in rows:
			line = "{0}. {1}".format(step.step_no or "-", step.description)
			if step.doctype_to_demo:
				line += "  [{0}]".format(step.doctype_to_demo)
			if step.duration_min:
				line += "  ({0} min)".format(step.duration_min)
			lines.append(line)
		return "\n".join(lines)

	def items_text(rows):
		lines = []
		for row in rows:
			line = "- {0}".format(row.item)
			if row.description:
				line += ": {0}".format(row.description)
			lines.append(line)
		return "\n".join(lines)

	def questions_text(rows):
		blocks = []
		for row in rows:
			block = "Q: {0}".format(row.question)
			if row.answer:
				block += "\nA: {0}".format(row.answer)
			blocks.append(block)
		return "\n\n".join(blocks)

	add("Demo Objective", template.demo_objective)
	add("Introduction", template.introduction)
	add("Customer Business Scenario", template.customer_business_scenario)
	add("Demo Agenda", template.demo_agenda)
	add("Demo Steps", steps_text(template.demo_steps))
	add("Key Features", items_text(template.key_features))
	add("Configuration Points", items_text(template.configuration_points))
	add("Business Benefits", items_text(template.business_benefits))
	add("Important Questions to Ask", questions_text(template.questions_to_ask))
	add("Common Customer Questions", questions_text(template.customer_questions))
	add("FAQs", questions_text(template.faqs))
	add("Demo Notes", template.demo_notes)
	add("Follow-up Points", items_text(template.follow_up_points))
	return sections


# ------------------------------------------------------------------
# permission filters
# ------------------------------------------------------------------

def get_permission_query_conditions(user=None):
	"""Consultants see the templates assigned to their consultant profile
	(matches the portal, which lists templates by functional_consultant);
	everyone else sees all."""
	user = user or frappe.session.user
	if not user or user == "Administrator":
		return ""
	roles = frappe.get_roles(user)
	if any(r in roles for r in ("System Manager", "Functional Team Manager", "Sales User", "Sales Manager")):
		return ""
	if "Functional Consultant" in roles:
		return (
			"(`tabFunctional Demo Template`.`functional_consultant` in "
			"(select `tabFunctional Consultant`.`name` from `tabFunctional Consultant` "
			"where `tabFunctional Consultant`.`user` = {0}))"
		).format(frappe.db.escape(user))
	return ""


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	if any(r in roles for r in ("System Manager", "Functional Team Manager", "Sales User", "Sales Manager")):
		return True
	if "Functional Consultant" in roles:
		consultant = frappe.db.get_value("Functional Consultant", {"user": user}, "name")
		return bool(consultant and doc.get("functional_consultant") == consultant)
	return False
