# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import can_manage_consultants, consultant_of_user, portal_context


def get_context(context):
	portal_context(
		context,
		_("My Templates"),
		["Functional Consultant", "Functional Team Manager"],
		active="templates",
		subtitle=_("Your reusable demo templates"),
	)
	consultant = consultant_of_user()
	context.consultant = consultant
	context.can_manage_consultants = can_manage_consultants()
	context.consultant_name = None
	if consultant:
		context.consultant_name = frappe.db.get_value(
			"Functional Consultant", consultant, "consultant_name"
		)
	context.templates = frappe.get_all(
		"Functional Demo Template",
		filters={"functional_consultant": consultant},
		fields=[
			"name", "template_name", "erpnext_module", "business_area",
			"is_active", "modified", "demo_objective",
		],
		order_by="modified desc",
		limit_page_length=200,
	) or []
	for t in context.templates:
		t["modified_display"] = frappe.utils.format_datetime(t.get("modified"), "medium") if t.get("modified") else "-"
