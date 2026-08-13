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
	create_workflow_states()


def after_migrate():
	"""Run after every `bench migrate` so already-installed sites pick up
	records introduced by later versions of the app. All steps are idempotent."""
	create_workflow_states()
	backfill_consultant_statuses()
	backfill_session_consultants()
	move_approved_requests_forward()
	sync_sales_workspace()


def backfill_consultant_statuses():
	"""One-time data fix: consultants created before the status field had a
	default (or via a path that never set it) end up with an EMPTY status,
	which hides them from every 'Active consultants' list in the portal (the
	dropdown filters status = Active). Set empty statuses to Active so existing
	consultants become selectable again."""
	if not frappe.db.exists("DocType", "Functional Consultant"):
		return
	frappe.db.sql(
		"""update `tabFunctional Consultant`
		set status = 'Active'
		where ifnull(status, '') = ''"""
	)
	frappe.db.commit()


def backfill_session_consultants():
	"""One-time data fix: sessions created before the consultant was always
	copied from the Demo Request can be empty, which shows 'No consultant
	selected' on the session form. Auto-select the request's consultant so
	every session carries the assigned consultant."""
	if not frappe.db.exists("DocType", "Demo Session"):
		return
	frappe.db.sql(
		"""update `tabDemo Session` ds
		join `tabDemo Request` dr on dr.name = ds.demo_request
		set ds.functional_consultant = dr.functional_consultant
		where ifnull(ds.functional_consultant, '') = ''
			and ifnull(dr.functional_consultant, '') != ''"""
	)
	frappe.db.commit()


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


def sync_sales_workspace():
	"""Force re-import the Sales Demo Workspace JSON on every migrate.

	The standard workspace sync only applies when the JSON's `modified` is
	newer than the record in the database, which is not guaranteed on
	already-installed sites. A force import makes sure the removed Lead
	shortcut/link (leads are managed from the sales portal only, not the
	desk) actually disappears from the live workspace.
	"""
	from frappe.modules.import_file import import_file_by_path

	path = frappe.get_app_path(
		"functional_demo",
		"sales_demo",
		"workspace",
		"sales_demo_workspace",
		"sales_demo_workspace.json",
	)
	try:
		import_file_by_path(path, force=True)
	except Exception:
		frappe.log_error(
			title=_("functional_demo: failed to re-import Sales Demo Workspace"),
			message=frappe.get_traceback(),
		)


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


def create_workflow_states():
	"""Create the Workflow State records used by the Demo Request workflow.

	Frappe v15 references Workflow State documents from workflow-enabled forms
	(e.g. the workflow state indicator/link). A workflow imported via fixture
	does not auto-create these records, so missing states surface as
	"Workflow State <name> not found" when opening or editing a Demo Request.
	"""
	workflow_states = [
		("Draft", "Inverse"),
		("Requested", "Info"),
		("Assigned", "Primary"),
		("Scheduled", "Primary"),
		("Demo In Progress", "Info"),
		("Demo Completed", "Success"),
		("Follow-up Required", "Warning"),
		("Converted", "Success"),
		("Not Interested", "Danger"),
		("Cancelled", "Danger"),
		("Closed", "Inverse"),
	]
	for state, style in workflow_states:
		if not frappe.db.exists("Workflow State", state):
			doc = frappe.new_doc("Workflow State")
			doc.workflow_state_name = state
			doc.style = style
			doc.insert(ignore_permissions=True)
	frappe.db.commit()


def move_approved_requests_forward():
	"""Data migration for the approval removal: any Demo Request still sitting
	in the removed 'Approved' workflow state is moved forward to Assigned (it
	has a consultant - every request is created with one) so it can be
	scheduled directly. Requests without a consultant go back to Requested."""
	if not frappe.db.exists("DocType", "Demo Request"):
		return
	frappe.db.sql(
		"""update `tabDemo Request`
		set workflow_state = 'Assigned', status = 'Assigned'
		where workflow_state = 'Approved' and ifnull(functional_consultant, '') != ''"""
	)
	frappe.db.sql(
		"""update `tabDemo Request`
		set workflow_state = 'Requested', status = 'Requested'
		where workflow_state = 'Approved'"""
	)
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
