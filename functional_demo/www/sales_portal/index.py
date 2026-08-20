# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import is_mail_notifications_enabled, portal_context, sales_stats


def get_context(context):
	# Hide sales portal entirely when mail notifications are disabled by admin
	if not is_mail_notifications_enabled():
		frappe.local.flags.redirect_location = "/demo_portal"
		raise frappe.Redirect
	portal_context(
		context,
		_("Sales Home"),
		["Sales User", "Sales Manager"],
		active="sales",
		subtitle=_("Sales, demo requests, scheduling and results"),
	)
	context.stats = sales_stats()
