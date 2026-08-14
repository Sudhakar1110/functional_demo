# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import portal_context, sales_stats


def get_context(context):
	portal_context(
		context,
		_("Sales Home"),
		["Sales User", "Sales Manager"],
		active="sales",
		subtitle=_("Sales, demo requests, scheduling and results"),
	)
	context.stats = sales_stats()
