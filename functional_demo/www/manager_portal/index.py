# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import manager_stats, portal_context


def get_context(context):
	portal_context(
		context,
		_("Manager Dashboard"),
		["Sales Manager", "Functional Team Manager"],
		active="manager",
		subtitle=_("Monitor the whole demo pipeline"),
	)
	context.stats = manager_stats()
	return context
