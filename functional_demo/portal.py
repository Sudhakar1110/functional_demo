# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Helpers shared by the Sales / Functional / Manager portal pages (www/)."""

import frappe
from frappe import _

SALES_ROLES = ("Sales User", "Sales Manager")
FUNCTIONAL_ROLES = ("Functional Consultant", "Functional Team Manager")
MANAGER_ROLES = ("Sales Manager", "Functional Team Manager")


# ---------------------------------------------------------------------------
# role helpers
# ---------------------------------------------------------------------------

def user_roles(user=None):
	user = user or frappe.session.user
	return set(frappe.get_roles(user))


def is_sales(user=None):
	return bool(user_roles(user) & set(SALES_ROLES))


def is_functional(user=None):
	return bool(user_roles(user) & set(FUNCTIONAL_ROLES))


def is_manager(user=None):
	return bool(user_roles(user) & set(MANAGER_ROLES))


def consultant_of_user(user=None):
	"""Functional Consultant record linked to the current user."""
	user = user or frappe.session.user
	return frappe.db.get_value("Functional Consultant", {"user": user}, "name")


def guard(required_roles):
	"""Raise a permission error unless the user has one of the given roles
	(or is a System Manager)."""
	if "System Manager" in user_roles():
		return
	for role in required_roles:
		if role in user_roles():
			return
	frappe.throw(
		_("You do not have permission to view this page."),
		frappe.PermissionError,
	)


# ---------------------------------------------------------------------------
# sidebar navigation (left-hand menu, role aware)
# ---------------------------------------------------------------------------

def sidebar_items(active):
	"""Sidebar menu for the current user. Managers see all sections."""
	items = [{"label": _("Home"), "route": "/demo_portal", "icon": "🏠", "active": active == "home"}]

	if is_sales() or is_manager():
		items += [
			{"label": _("Sales Home"), "route": "/sales_portal", "icon": "📊", "active": active == "sales"},
			{"label": _("My Leads"), "route": "/sales_portal/my_leads", "icon": "🧲", "active": active == "leads"},
			{"label": _("Demo Requests"), "route": "/sales_portal/demo_requests", "icon": "🗂️", "active": active == "requests"},
			{"label": _("Results"), "route": "/sales_portal/results", "icon": "📈", "active": active == "results"},
		]

	if is_functional() or is_manager():
		items += [
			{"label": _("Functional Home"), "route": "/functional_portal", "icon": "🎯", "active": active == "functional"},
			{"label": _("My Sessions"), "route": "/functional_portal/my_sessions", "icon": "📅", "active": active == "sessions"},
			{"label": _("My Templates"), "route": "/functional_portal/my_templates", "icon": "📋", "active": active == "templates"},
			{"label": _("Follow-ups"), "route": "/functional_portal/follow_ups", "icon": "🔔", "active": active == "follow_ups"},
		]

	if is_manager():
		items += [{"label": _("Manager Dashboard"), "route": "/manager_portal", "icon": "📉", "active": active == "manager"}]

	return items


def portal_context(context, title, required_roles, active, subtitle=""):
	"""Standard context setup for login-required, role-guarded portal pages."""
	context.login_required = True
	context.no_cache = 1
	if frappe.session.user == "Guest":
		# redirect to the login page (the framework's own login redirect runs
		# after get_context, so we must handle guests here before guard() throws)
		frappe.local.flags.redirect_location = "/login?redirect-to={0}".format(
			frappe.utils.get_url()
		)
		raise frappe.Redirect
	context.title = title
	context.subtitle = subtitle
	context.is_sales = is_sales()
	context.is_functional = is_functional()
	context.is_manager = is_manager()
	context.full_name = frappe.utils.get_fullname(frappe.session.user)
	context.sidebar_items = sidebar_items(active)
	guard(required_roles)
	return context


# ---------------------------------------------------------------------------
# stats (lists go through frappe.get_all, so row-level permission filters and
# ERPNext user permissions are respected automatically)
# ---------------------------------------------------------------------------

def _count(doctype, filters=None):
	return len(frappe.get_all(doctype, filters=filters or {}, fields=["name"]) or [])


def sales_stats(user=None):
	user = user or frappe.session.user
	today = frappe.utils.today()
	requests = frappe.get_all(
		"Demo Request", fields=["name", "status"], limit_page_length=1000, order_by="creation desc"
	) or []
	by_status = {}
	for r in requests:
		by_status[r.get("status")] = by_status.get(r.get("status"), 0) + 1

	total = len(requests)
	pending = sum(by_status.get(s, 0) for s in ("Draft", "Requested", "Assigned"))
	scheduled = sum(by_status.get(s, 0) for s in ("Scheduled", "Demo In Progress"))
	completed = sum(by_status.get(s, 0) for s in ("Demo Completed", "Follow-up Required"))
	converted = by_status.get("Converted", 0)

	return {
		"total_requests": total,
		"pending": pending,
		"scheduled": scheduled,
		"completed": completed,
		"converted": converted,
		"todays_demos": _count(
			"Demo Session",
			{"scheduled_date": today, "demo_status": ["in", ["Scheduled", "In Progress"]]},
		),
		"follow_ups_due": _count(
			"Demo Follow Up",
			{"status": ["in", ["Open", "In Progress"]], "follow_up_date": ["<=", today]},
		),
		"conversion_rate": round((converted / total * 100), 1) if total else 0,
		"recent_requests": frappe.get_all(
			"Demo Request",
			fields=["name", "customer", "lead", "status", "priority", "interested_module", "preferred_demo_date", "functional_consultant", "creation"],
			order_by="creation desc",
			limit_page_length=8,
		) or [],
	}


def functional_stats(user=None):
	user = user or frappe.session.user
	consultant = consultant_of_user(user)
	today = frappe.utils.today()
	empty = {
		"consultant": consultant,
		"todays_demos": 0, "in_progress": 0, "upcoming": 0,
		"completed": 0, "templates": 0, "follow_ups": 0,
	}
	if not consultant:
		return empty

	sessions = frappe.get_all(
		"Demo Session",
		filters={"functional_consultant": consultant},
		fields=["name", "demo_status", "scheduled_date"],
		limit_page_length=1000,
	) or []

	todays = sum(
		1
		for s in sessions
		if s.get("demo_status") in ("Scheduled", "In Progress") and s.get("scheduled_date") == today
	)
	in_progress = sum(1 for s in sessions if s.get("demo_status") == "In Progress")
	upcoming = sum(
		1
		for s in sessions
		if s.get("demo_status") == "Scheduled" and (s.get("scheduled_date") or "") >= today
	)
	completed = sum(1 for s in sessions if s.get("demo_status") == "Completed")

	return {
		"consultant": consultant,
		"todays_demos": todays,
		"in_progress": in_progress,
		"upcoming": upcoming,
		"completed": completed,
		"templates": _count("Functional Demo Template", {"functional_consultant": consultant}),
		"follow_ups": _count(
			"Demo Follow Up",
			{"functional_consultant": consultant, "status": ["in", ["Open", "In Progress"]]},
		),
		"recent_sessions": frappe.get_all(
			"Demo Session",
			filters={"functional_consultant": consultant},
			fields=["name", "customer", "scheduled_date", "start_time", "demo_status", "final_result"],
			order_by="scheduled_date desc",
			limit_page_length=8,
		) or [],
	}


def manager_stats():
	today = frappe.utils.today()

	by_status = dict(
		frappe.db.sql(
			"select status, count(*) from `tabDemo Request` group by status"
		)
	)
	total = sum(by_status.values()) or 0
	converted = by_status.get("Converted", 0) or 0

	consultant_workload = frappe.db.sql(
		"""
		select fc.name, fc.consultant_name, fc.specialization, fc.availability,
			count(ds.name) as active_demos
		from `tabFunctional Consultant` fc
		left join `tabDemo Session` ds
			on ds.functional_consultant = fc.name and ds.demo_status in ('Scheduled', 'In Progress')
		where fc.status = 'Active'
		group by fc.name
		order by active_demos desc
		"""
	)

	sales_performance = frappe.db.sql(
		"""
		select sales_person,
			count(*) as total_requests,
			sum(case when status = 'Converted' then 1 else 0 end) as converted,
			sum(case when status in ('Scheduled', 'Demo In Progress') then 1 else 0 end) as scheduled
		from `tabDemo Request`
		group by sales_person
		order by total_requests desc
		"""
	)

	module_wise = frappe.db.sql(
		"select interested_module, count(*) from `tabDemo Request` group by interested_module order by count(*) desc"
	) or []

	recent_activity = frappe.get_all(
		"Demo Request Activity",
		fields=["activity_type", "activity_date", "user", "status", "remarks", "parent"],
		order_by="activity_date desc",
		limit_page_length=12,
	) or []
	for a in recent_activity:
		a["activity_display"] = (
			frappe.utils.format_datetime(a.get("activity_date"), "medium") if a.get("activity_date") else "-"
		)

	return {
		"total": total,
		"by_status": by_status,
		"pending": sum(by_status.get(s, 0) for s in ("Draft", "Requested", "Assigned")),
		"scheduled": sum(by_status.get(s, 0) for s in ("Scheduled", "Demo In Progress")),
		"completed": sum(by_status.get(s, 0) for s in ("Demo Completed", "Follow-up Required")),
		"converted": converted,
		"cancelled": by_status.get("Cancelled", 0) or 0,
		"conversion_rate": round(converted / total * 100, 1) if total else 0,
		"todays_demos": _count(
			"Demo Session",
			{"scheduled_date": today, "demo_status": ["in", ["Scheduled", "In Progress"]]},
		),
		"open_follow_ups": _count(
			"Demo Follow Up", {"status": ["in", ["Open", "In Progress"]]}
		),
		"consultant_workload": consultant_workload,
		"sales_performance": sales_performance,
		"module_wise": module_wise,
		"recent_activity": recent_activity,
	}


# ---------------------------------------------------------------------------
# portal menu (Frappe shows these in the website menu by role)
# ---------------------------------------------------------------------------

def get_standard_portal_menu_items():
	return [
		{"title": _("Demo Portal"), "route": "/demo_portal", "role": "Sales User"},
		{"title": _("Demo Portal"), "route": "/demo_portal", "role": "Sales Manager"},
		{"title": _("Demo Portal"), "route": "/demo_portal", "role": "Functional Consultant"},
		{"title": _("Demo Portal"), "route": "/demo_portal", "role": "Functional Team Manager"},
	]
