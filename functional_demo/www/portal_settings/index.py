# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import is_admin, is_mail_notifications_enabled, portal_context


def get_context(context):
	"""Admin-only portal settings page for toggling mail notifications."""
	portal_context(
		context,
		_("Portal Settings"),
		["Sales User", "Sales Manager", "Functional Consultant", "Functional Team Manager"],
		active="settings",
		subtitle=_("Manage portal settings"),
	)
	# Only admins can see this page
	if not is_admin():
		frappe.throw(
			_("Only administrators can access portal settings."),
			frappe.PermissionError,
		)
	context.mail_notifications_enabled = is_mail_notifications_enabled()
