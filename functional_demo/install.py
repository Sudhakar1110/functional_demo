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
	import_module_docs()
	create_developer_user()
	disable_legacy_notifications()
	fix_lead_naming()


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


def fix_lead_naming():
	"""Change the Lead doctype naming from CRM-LEAD to CRM-SALES.

	The portal calls leads 'Sales Persons' - the ID should match.
	"""
	if not frappe.db.exists("DocType", "Lead"):
		return
	current = frappe.db.get_value("DocType", "Lead", "autoname") or ""
	if "LEAD" in current:
		new_autoname = current.replace("LEAD", "SALES")
		frappe.db.set_value("DocType", "Lead", "autoname", new_autoname)
		frappe.db.commit()


def create_roles():
	"""Create the custom roles used by this app (idempotent).

	Note: 'Sales User' and 'Sales Manager' are standard ERPNext roles and are
	reused as-is. Only the functional team roles and Feedback Viewer are custom.
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
	"""Force re-import both app workspaces on every migrate.

	The standard workspace sync only applies when the JSON's `modified` is
	newer than the record in the database, which is not guaranteed on
	already-installed sites. A force import makes sure workspace changes
	(Lead shortcut/link, Demo Feedback, …) actually appear in the live desk.
	"""
	from frappe.modules.import_file import import_file_by_path

	workspaces = (
		("sales_demo_workspace", "sales_demo_workspace.json"),
		("functional_demo_workspace", "functional_demo_workspace.json"),
	)
	for folder, fname in workspaces:
		path = frappe.get_app_path(
			"functional_demo", "sales_demo", "workspace", folder, fname
		)
		try:
			import_file_by_path(path, force=True)
		except Exception:
			frappe.log_error(
				title=_("functional_demo: failed to re-import {0}").format(fname),
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


def disable_legacy_notifications():
	"""Disable the legacy standard Notification doctypes shipped before the
	custom notification path (create_notification + direct email) replaced
	them. Both systems used to fire on the same events - e.g. 'Demo Scheduled'
	would email AND bell the sales person and consultant twice. The JSON files
	are already synced with enabled=0; this is a belt-and-braces step that
	force-disables any record left enabled on an already-installed site."""
	legacy = [
		"Consultant Assigned",
		"Consultant Reassigned",
		"Demo Cancelled",
		"Demo Completed",
		"Demo Request Created",
		"Demo Rescheduled",
		"Demo Scheduled",
		"Demo Starting Soon",
		"Follow-up Due",
		"Follow-up Required",
	]
	for name in legacy:
		if frappe.db.exists("Notification", name):
			cur = frappe.db.get_value("Notification", name, "enabled")
			if cur:
				frappe.db.set_value("Notification", name, "enabled", 0)
	frappe.db.commit()


def create_developer_user():
	"""Idempotently create the 'developer' user with the feedback-only role.

	The feedback-only role sees ONLY the Demo Feedback page - the portal
	/feedback page and the desk /app/demo-feedback page. The standard Frappe
	'Developer' role is the feedback-only role for this app (a user carrying
	it is restricted to feedback); the legacy custom 'Feedback Viewer' role is
	kept as an equivalent alias wherever it was already assigned. The user is
	created on first migrate if missing; if the user already exists the
	feedback-only role is just ensured. The initial password is randomly
	generated and printed to the console (and stored on the user) so there is
	never a hardcoded default credential in the codebase - the operator sets
	a proper password afterwards if needed.
	"""
	if not frappe.db.exists("User", "developer"):
		try:
			doc = frappe.new_doc("User")
			doc.email = "developer@example.com"
			doc.first_name = "Developer"
			doc.username = "developer"
			doc.enabled = 1
			password = frappe.generate_hash(length=12)
			doc.new_password = password
			doc.send_welcome_email = 0
			doc.add_roles("Developer")
			doc.insert(ignore_permissions=True)
			print(
				f"Created User: developer (role: Developer, generated password: {password}) - "
				"change it after first login."
			)
		except Exception:
			frappe.log_error(
				title=_("functional_demo: failed to create the developer user"),
				message=frappe.get_traceback(),
			)
			return
	else:
		user = frappe.get_doc("User", "developer")
		roles = set(frappe.get_roles("developer"))
		if "Developer" not in roles:
			user.add_roles("Developer")
			user.save(ignore_permissions=True)


def mark_overdue_follow_ups():
	"""Daily job: mark Demo Follow Ups as Overdue once the date has passed,
	and notify the assignee + sales person so an overdue follow-up is never
	silently forgotten."""
	if not frappe.db.exists("DocType", "Demo Follow Up"):
		return
	overdue = frappe.get_all(
		"Demo Follow Up",
		filters=[
			["status", "in", ["Open", "In Progress"]],
			["follow_up_date", "<", frappe.utils.today()],
		],
		fields=[
			"name", "demo_request", "customer", "assigned_to", "sales_person",
			"follow_up_date",
		],
		limit_page_length=500,
	) or []
	if not overdue:
		return
	frappe.db.sql(
		"""update `tabDemo Follow Up`
		set status = 'Overdue'
		where status in ('Open', 'In Progress')
			and follow_up_date < %s""",
		frappe.utils.today(),
	)
	frappe.db.commit()
	for row in overdue:
		_notify_overdue_follow_up(row)
	frappe.db.commit()


def _notify_overdue_follow_up(row):
	"""In-app notification + email about one overdue follow-up."""
	from functional_demo.portal import create_notification, send_branded_email

	party = row.get("customer") or row.get("demo_request") or row.get("name")
	subject = _("Follow-up Overdue — {0} (due {1})").format(
		party, row.get("follow_up_date")
	)
	for user in {row.get("assigned_to"), row.get("sales_person")}:
		if not user or user == "Guest":
			continue
		create_notification(user, subject, "Demo Follow Up", row.get("name"))
		email = frappe.db.get_value("User", user, "email")
		if not email:
			continue
		try:
			send_branded_email(
				recipients=[email],
				subject=subject,
				heading=_("Follow-up Overdue"),
				intro=_("Follow-up {0} for {1} was due on {2} and is now overdue.").format(
					row.get("name"), party, row.get("follow_up_date")
				),
				rows=[
					(_("Follow-up"), row.get("name")),
					(_("Demo Request"), row.get("demo_request") or "-"),
				],
				cta_text=_("Open Follow-up"),
				cta_url=frappe.utils.get_url("/app/demo-follow-up/{0}".format(row.get("name"))),
				reference_doctype="Demo Follow Up",
				reference_name=row.get("name"),
			)
		except Exception:
			frappe.log_error(
				title=_("Overdue follow-up email to {0} failed for {1}").format(
					user, row.get("name")
				),
				message=frappe.get_traceback(),
			)


def send_trial_period_reminders():
	"""Daily job: when a converted lead's trial period ends tomorrow, email the
	sales person (and send an in-app notification) so they can follow up before
	the customer's access expires. Each trial period is reminded only once."""
	if not frappe.db.exists("DocType", "Demo Request"):
		return
	reminder_day = frappe.utils.add_days(frappe.utils.today(), 1)
	due = frappe.get_all(
		"Demo Request",
		filters=[
			["status", "=", "Converted"],
			["trial_end_date", "=", reminder_day],
			["trial_reminder_sent", "=", 0],
		],
		fields=["name", "customer", "lead", "sales_person", "owner", "trial_start_date", "trial_end_date"],
		limit_page_length=500,
	) or []
	if not due:
		return
	for row in due:
		_notify_trial_period_reminder(row)
	frappe.db.commit()


def _notify_trial_period_reminder(row, mark_sent=True):
	"""Email + in-app notification about one trial period ending tomorrow.

	mark_sent=False keeps the trial_reminder_sent flag untouched, so a manual
	"Send Reminder Now" (verification / early nudge) does not suppress the
	scheduled one-day-before reminder.
	"""
	from functional_demo.portal import create_notification, send_branded_email

	sales_person = row.get("sales_person") or row.get("owner")
	if not sales_person or sales_person == "Guest":
		return
	party = row.get("customer") or row.get("lead") or row.get("name")
	subject = _("Trial Period Ends Tomorrow — {0}").format(party)
	create_notification(sales_person, subject, "Demo Request", row.get("name"))
	email = frappe.db.get_value("User", sales_person, "email")
	if email:
		try:
			send_branded_email(
				recipients=[email],
				subject=subject,
				heading=_("Trial Period Ending Tomorrow"),
				intro=_(
					"The trial period for {0} ends tomorrow ({1}). Reach out to the customer "
					"about converting or extending before their access expires."
				).format(party, row.get("trial_end_date")),
				rows=[
					(_("Demo Request"), row.get("name")),
					(_("Trial Start Date"), row.get("trial_start_date") or "-"),
					(_("Trial End Date"), row.get("trial_end_date") or "-"),
					(_("Sales Person"), sales_person),
				],
				cta_text=_("Open Demo Request"),
				cta_url=frappe.utils.get_url("/app/demo-request/{0}".format(row.get("name"))),
				reference_doctype="Demo Request",
				reference_name=row.get("name"),
			)
		except Exception:
			frappe.log_error(
				title=_("Trial reminder email to {0} failed for {1}").format(
					sales_person, row.get("name")
				),
				message=frappe.get_traceback(),
			)
	# mark reminded (even if the mail failed - the job matches only the day
	# before the end date, so a retry would arrive a day late anyway)
	if mark_sent:
		frappe.db.set_value("Demo Request", row.get("name"), "trial_reminder_sent", 1)
