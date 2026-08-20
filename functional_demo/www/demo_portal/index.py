# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import (
	functional_stats,
	is_developer,
	is_functional,
	is_mail_notifications_enabled,
	is_manager,
	is_sales,
	portal_context,
	sales_stats,
)

def get_context(context):
	# The feedback-only role (Developer / Feedback Viewer) never sees the home
	# dashboard, it is sent straight to the Feedback page.
	if is_developer():
		frappe.local.flags.redirect_location = "/feedback"
		raise frappe.Redirect
	portal_context(
		context,
		_("Demo Portal"),
		["Sales User", "Sales Manager", "Functional Consultant", "Functional Team Manager"],
		active="home",
		subtitle=_("One simple workspace for the complete demo workflow"),
	)
	context.show_sales = is_sales()
	context.show_functional = is_functional()
	context.show_manager = is_manager()
	# Per-user mail notification toggle
	context.mail_notifications_enabled = is_mail_notifications_enabled()
	if context.show_sales:
		context.sales = sales_stats()
	if context.show_functional:
		context.functional = functional_stats()
