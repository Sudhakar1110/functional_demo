# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe.model.document import Document


class PortalChatMessage(Document):
	"""Chat messages between portal users (one-to-one).

	The controller class is REQUIRED: Frappe's migrate deletes any doctype
	whose controller module has no matching class (get_controller raises
	ImportError -> treated as an orphaned doctype)."""
	pass


def get_permission_query_conditions(user=None):
	"""Users can only see messages they sent or received. Only the site admin
	(Administrator / System Manager) sees everything."""
	user = user or frappe.session.user
	if not user or user == "Administrator":
		return ""
	if "System Manager" in frappe.get_roles(user):
		return ""
	return (
		"(`tabPortal Chat Message`.`from_user` = {0} or `tabPortal Chat Message`.`to_user` = {0})"
	).format(frappe.db.escape(user))


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	if "System Manager" in frappe.get_roles(user):
		return True
	return doc.get("from_user") == user or doc.get("to_user") == user
