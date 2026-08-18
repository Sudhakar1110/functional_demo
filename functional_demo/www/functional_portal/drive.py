# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import is_admin, portal_context


def _size_display(size):
	"""Human-readable file size (bytes -> KB/MB/GB)."""
	try:
		size = int(size or 0)
	except (TypeError, ValueError):
		return "-"
	if size >= 1024 * 1024 * 1024:
		return "{0:.1f} GB".format(size / (1024 * 1024 * 1024))
	if size >= 1024 * 1024:
		return "{0:.1f} MB".format(size / (1024 * 1024))
	if size >= 1024:
		return "{0:.0f} KB".format(size / 1024)
	return "{0} B".format(size)


def get_context(context):
	# The Drive is a shared consultant-only library - sales never sees it.
	portal_context(
		context,
		_("Consultant Drive"),
		["Functional Consultant", "Functional Team Manager"],
		active="drive",
		subtitle=_("Shared file library for the consultant team"),
	)
	context.files = frappe.get_all(
		"Consultant Drive File",
		fields=[
			"name", "title", "description", "file", "file_size",
			"uploaded_by", "uploaded_on",
		],
		order_by="uploaded_on desc, creation desc",
		limit_page_length=1000,
	) or []
	uploader_names = {}
	user_ids = {f.get("uploaded_by") for f in context.files if f.get("uploaded_by")}
	if user_ids:
		for row in frappe.get_all(
			"User", filters={"name": ["in", list(user_ids)]}, fields=["name", "full_name"]
		):
			uploader_names[row.name] = row.full_name
	for f in context.files:
		f["size_display"] = _size_display(f.get("file_size"))
		f["uploaded_by_display"] = uploader_names.get(f.get("uploaded_by")) or f.get("uploaded_by") or "-"
		f["uploaded_on_display"] = (
			frappe.utils.format_datetime(f.get("uploaded_on"), "medium")
			if f.get("uploaded_on")
			else "-"
		)
		# only the uploader (or an admin) may delete a file
		f["can_delete"] = (f.get("uploaded_by") == frappe.session.user) or is_admin()
	context.total_files = len(context.files)
	# The upload form posts multipart directly to the whitelisted API, so the
	# page hands the CSRF token to its own script (the shared portal_script
	# helper only covers JSON portalCall requests).
	context.csrf_token = frappe.sessions.get_csrf_token()
