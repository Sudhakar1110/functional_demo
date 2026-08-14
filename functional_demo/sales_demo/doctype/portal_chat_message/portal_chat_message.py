# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe


def get_permission_query_conditions(user=None):
	"""Users can only see messages they sent or received (Administrator sees all)."""
	user = user or frappe.session.user
	if not user or user == "Administrator":
		return ""
	return (
		"(`tabPortal Chat Message`.`from_user` = {0} or `tabPortal Chat Message`.`to_user` = {0})"
	).format(frappe.db.escape(user))


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return doc.get("from_user") == user or doc.get("to_user") == user
