# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import portal_context
from functional_demo.sales_demo.doctype.manual_lead_tracker.manual_lead_tracker import (
	MANUAL_LEAD_STAGES,
	manual_leads,
)


def get_context(context):
	stage = "Paid"
	portal_context(
		context,
		_("Paid Leads"),
		["Sales Manager"],
		active="paid_leads",
		subtitle=_("Hand-maintained leads that have paid"),
	)
	context.stage = stage
	context.stage_options = MANUAL_LEAD_STAGES
	context.leads = manual_leads(stage)
	context.count = len(context.leads)
	context.form_show_demo_date = False
	context.form_show_plan = True
	context.form_show_quotation = False
	context.form_show_payment = True
	context.form_show_expiry = True