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
	stage = "Demo Completed"
	portal_context(
		context,
		_("Demo Completed Leads"),
		["Sales Manager"],
		active="completed_leads",
		subtitle=_("Hand-maintained leads whose demo has been completed"),
	)
	context.stage = stage
	context.stage_options = MANUAL_LEAD_STAGES
	context.leads = manual_leads(stage)
	context.count = len(context.leads)