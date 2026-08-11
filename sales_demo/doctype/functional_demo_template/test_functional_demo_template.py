# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe.tests.utils import FrappeTestCase

from functional_demo.sales_demo.doctype.functional_consultant.test_functional_consultant import (
	make_consultant,
)
from functional_demo.sales_demo.doctype.functional_demo_template.functional_demo_template import (
	get_template_snapshot,
)


def make_template(consultant, name="Accounts Payable Demo"):
	doc = frappe.new_doc("Functional Demo Template")
	doc.template_name = name
	doc.functional_consultant = consultant.name
	doc.erpnext_module = "Accounting"
	doc.demo_objective = "Show how AP invoices are processed."
	doc.demo_agenda = "1. Intro 2. Live walkthrough"
	doc.append("demo_steps", {"step_no": 1, "description": "Open Purchase Invoice list", "doctype_to_demo": "Purchase Invoice"})
	doc.append("key_features", {"item": "Automated payment reminders"})
	doc.insert(ignore_permissions=True)
	return doc


class TestFunctionalDemoTemplate(FrappeTestCase):
	def setUp(self):
		self.consultant = make_consultant()

	def test_template_creation_and_snapshot(self):
		template = make_template(self.consultant)
		sections = get_template_snapshot(template.name)
		section_names = [s["section"] for s in sections]
		self.assertIn("Demo Objective", section_names)
		self.assertIn("Demo Steps", section_names)
		steps = next(s for s in sections if s["section"] == "Demo Steps")
		self.assertIn("Purchase Invoice", steps["content"])

	def test_template_questions_and_items(self):
		template = make_template(self.consultant, name="Q&A Template")
		template.append("questions_to_ask", {"question": "How many invoices do you process per month?"})
		template.append("faqs", {"question": "Does this support GST?", "answer": "Yes, fully."})
		template.save(ignore_permissions=True)
		sections = get_template_snapshot(template.name)
		qa = next(s for s in sections if s["section"] == "Important Questions to Ask")
		self.assertIn("How many invoices", qa["content"])
		faqs = next(s for s in sections if s["section"] == "FAQs")
		self.assertIn("Yes, fully", faqs["content"])
