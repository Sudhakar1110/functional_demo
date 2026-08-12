# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.api import SPECIALIZATIONS
from functional_demo.portal import can_manage_consultants, consultant_of_user, portal_context

MODULES = [
	"", "Accounting", "CRM", "Selling", "Buying", "Stock", "Manufacturing",
	"HR & Payroll", "Projects", "Healthcare", "Education", "Agriculture",
	"Custom Application",
]


def get_context(context):
	portal_context(
		context,
		_("Demo Template"),
		["Functional Consultant", "Functional Team Manager"],
		active="templates",
		subtitle=_("Create or edit your demo template"),
	)
	context.modules = MODULES
	context.specializations = SPECIALIZATIONS
	consultant = consultant_of_user()
	context.my_consultant = consultant
	context.can_manage_consultants = can_manage_consultants()
	context.consultant_name = None
	if consultant:
		context.consultant_name = frappe.db.get_value(
			"Functional Consultant", consultant, "consultant_name"
		)

	name = frappe.form_dict.get("name") or ""
	context.create_mode = bool(frappe.form_dict.get("new") == "1" or not name)
	if not context.create_mode:
		# get_doc applies document-level permissions (consultants own their templates)
		context.doc = frappe.get_doc("Functional Demo Template", name)
	return context
