# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Install-time helpers and scheduled jobs for functional_demo."""

import os

import frappe
from frappe import _


def before_install():
	"""Ensure the app is only installed on Frappe v15+."""
	try:
		major = int(frappe.__version__.split(".")[0])
	except Exception:
		major = 0
	if major < 15:
		frappe.throw(
			_("functional_demo requires Frappe Framework v15 or later. Found version {0}.").format(
				frappe.__version__
			)
		)


def after_install():
	"""Idempotent post-install setup."""
	create_roles()
	import_module_docs()


def create_roles():
	"""Create the custom roles used by this app (idempotent).

	Note: 'Sales User' and 'Sales Manager' are standard ERPNext roles and are
	reused as-is. Only the functional team roles are custom.
	"""
	from functional_demo.roles import ROLES

	for role in ROLES:
		if not frappe.db.exists("Role", role):
			doc = frappe.new_doc("Role")
			doc.role_name = role
			doc.desk_access = 1
			doc.is_custom = 0
			doc.insert(ignore_permissions=True)
			print(f"Created Role: {role}")


def import_module_docs():
	"""Import Dashboard Charts and Number Cards shipped in the module folders.

	The standard folder-sync mechanisms cover Doctypes, Reports, Notifications and
	Workspaces automatically. Charts/Cards are imported here as well to make the
	install fully deterministic.
	"""
	from frappe.modules.import_file import import_file_by_path

	if not frappe.db.exists("Module Def", "Sales Demo"):
		return

	module_path = frappe.get_module_path("Sales Demo")
	for folder in ("dashboard_chart", "number_card"):
		folder_path = os.path.join(module_path, folder)
		if not os.path.isdir(folder_path):
			continue
		for fname in sorted(os.listdir(folder_path)):
			doc_path = os.path.join(folder_path, fname, f"{fname}.json")
			if os.path.isfile(doc_path):
				try:
					import_file_by_path(doc_path, force=True)
				except Exception:
					frappe.log_error(
						title=_("functional_demo: failed to import {0}").format(fname),
						message=frappe.get_traceback(),
					)

	fix_dashboard_charts()


def fix_dashboard_charts():
	"""Directly set group_by_based_on on the Group By charts (belt & braces).

	Frappe v15 requires `group_by_based_on` for 'Group By' charts. This sets it
directly so an already-installed site is fixed without waiting for a JSON
re-import.
	"""
	chart_fields = {
		"Demo Requests by Module": "interested_module",
		"Demo Requests by Priority": "priority",
		"Demo Requests by Status": "status",
		"Demo Sessions by Consultant": "functional_consultant",
	}
	for chart_name, field in chart_fields.items():
		if frappe.db.exists("Dashboard Chart", chart_name):
			cur = frappe.db.get_value("Dashboard Chart", chart_name, "group_by_based_on")
			if cur != field:
				frappe.db.set_value("Dashboard Chart", chart_name, "group_by_based_on", field)
	frappe.db.commit()


def fix_workspace_parents():
	"""Put both app workspaces under the Home workspace in the sidebar.

	Frappe v15 places a workspace according to its `parent_page`; an empty value
	leaves placement to module defaults (workspaces can end up under unrelated
	modules). This makes the placement explicit: both under Home.
	"""
	for ws in ("Sales Demo Workspace", "Functional Demo Workspace"):
		if frappe.db.exists("Workspace", ws):
			frappe.db.set_value("Workspace", ws, "parent_page", "Home")
	frappe.db.commit()


def mark_overdue_follow_ups():
	"""Daily job: mark Demo Follow Ups as Overdue once the date has passed."""
	if not frappe.db.exists("DocType", "Demo Follow Up"):
		return
	frappe.db.sql(
		"""update `tabDemo Follow Up`
		set status = 'Overdue'
		where status in ('Open', 'In Progress')
			and follow_up_date < %s""",
		frappe.utils.today(),
	)
	frappe.db.commit()
