# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import portal_context

CHAT_ROLES = [
	"Sales User",
	"Sales Manager",
	"Functional Consultant",
	"Functional Team Manager",
	"Developer",
]


def get_context(context):
	portal_context(
		context,
		_("Chat"),
		CHAT_ROLES,
		active="chat",
		subtitle=_("Message any team member"),
	)
	context.me = frappe.session.user
	context.me_name = frappe.utils.get_fullname(frappe.session.user) or frappe.session.user
