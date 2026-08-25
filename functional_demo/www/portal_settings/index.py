# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import is_admin, is_mail_notifications_enabled, is_results_hidden, portal_context


def get_context(context):
	"""Portal settings page — all logged-in users can toggle their own
	mail notification preference. Admin-only: hide/show Results."""
	portal_context(
		context,
		_("Portal Settings"),
		["Sales User", "Sales Manager", "Functional Consultant", "Functional Team Manager", "Developer"],
		active="settings",
		subtitle=_("Manage your portal settings"),
	)
	context.mail_notifications_enabled = is_mail_notifications_enabled()
	context.is_admin = is_admin()
	context.results_hidden = is_results_hidden()
