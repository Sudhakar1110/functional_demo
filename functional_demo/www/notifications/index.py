# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import portal_context


def _doc_href(document_type, document_name):
	"""Where a notification should open - mirrors the bell's docHref() so the
	full notifications page and the dropdown link to the same portal page."""
	if not document_type or not document_name:
		return "/demo_portal"
	if document_type == "Demo Request":
		return "/sales_portal/demo_request?name={0}".format(document_name)
	if document_type == "Demo Session":
		return "/functional_portal/session?name={0}".format(document_name)
	if document_type == "Demo Follow Up":
		return "/functional_portal/follow_ups"
	return "/demo_portal"


def get_context(context):
	"""Full-page list of the current user's notifications.

	The bell's "View More" link opens this page, where every notification is
	visible (no cap). Each row links to the related portal record."""
	portal_context(
		context,
		_("Notifications"),
		["Sales User", "Sales Manager", "Functional Consultant", "Functional Team Manager", "Developer"],
		active="notifications",
	)
	user = frappe.session.user
	rows = frappe.get_all(
		"Notification Log",
		filters={"for_user": user},
		fields=["name", "subject", "type", "document_type", "document_name", "creation", "read"],
		order_by="creation desc",
		limit_page_length=1000000,
		ignore_permissions=True,
	) or []

	notifications = []
	for row in rows:
		notifications.append(
			{
				"name": row.name,
				"subject": row.subject or _("Notification"),
				"type": row.type or "",
				"document_type": row.document_type or "",
				"document_name": row.document_name or "",
				"when": frappe.utils.pretty_date(row.creation) if row.creation else "",
				"doc_href": _doc_href(row.document_type, row.document_name),
				"read": 1 if row.read else 0,
			}
		)

	context.notifications = notifications
	context.total_count = len(notifications)
	context.unread_count = sum(1 for n in notifications if not n["read"])
