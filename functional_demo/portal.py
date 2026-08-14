# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Helpers shared by the Sales / Functional / Manager portal pages (www/)."""

import frappe
from frappe import _

SALES_ROLES = ("Sales User", "Sales Manager")
FUNCTIONAL_ROLES = ("Functional Consultant", "Functional Team Manager")
MANAGER_ROLES = ("Sales Manager", "Functional Team Manager")
DEVELOPER_ROLES = ("Developer",)


# ---------------------------------------------------------------------------
# role helpers
# ---------------------------------------------------------------------------

def user_roles(user=None):
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	# Site admins (Administrator / System Manager) see every portal section -
	# the same treatment the app already gives them in guard(). This keeps the
	# admin account from falling through to the bare 'Home + Feedback' sidebar.
	if user == "Administrator" or "System Manager" in roles:
		roles |= set(SALES_ROLES + FUNCTIONAL_ROLES + MANAGER_ROLES)
	return roles


def is_sales(user=None):
	return bool(user_roles(user) & set(SALES_ROLES))


def is_functional(user=None):
	return bool(user_roles(user) & set(FUNCTIONAL_ROLES))


def is_manager(user=None):
	return bool(user_roles(user) & set(MANAGER_ROLES))


def is_developer(user=None):
	"""The Developer role is feedback-only: it may view the portal Feedback
	page and nothing else."""
	return bool(user_roles(user) & set(DEVELOPER_ROLES))


def can_manage_consultants(user=None):
	"""Functional Team Managers and System Managers can create/link
	consultant profiles (the desk-side Functional Consultant doctype is
	restricted to exactly these two roles)."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(user_roles(user) & {"Functional Team Manager", "System Manager"})


def consultant_of_user(user=None):
	"""Functional Consultant record linked to the current user.		Administrator gets a consultant profile auto-created on first access so the
		whole portal (My Sessions, Follow-ups, …) works right away for the site
		admin — no manual ERPNext setup needed to test."""
	user = user or frappe.session.user
	name = frappe.db.get_value("Functional Consultant", {"user": user}, "name")
	if name:
		return name
	if user == "Administrator":
		return _ensure_admin_consultant()
	return None


def _ensure_admin_consultant():
	"""Idempotently create a Functional Consultant record for Administrator."""
	existing = frappe.db.get_value("Functional Consultant", {"user": "Administrator"}, "name")
	if existing:
		return existing
	try:
		doc = frappe.new_doc("Functional Consultant")
		doc.consultant_name = "Administrator"
		doc.user = "Administrator"
		doc.specialization = "Custom Application"
		doc.status = "Active"
		doc.availability = "Available"
		doc.insert(ignore_permissions=True)
		return doc.name
	except Exception:
		# never break the portal if auto-creation fails - fall back to the
		# normal guard screen (with the one-click 'Link my user' button)
		frappe.log_error(
			title=_("Could not auto-create Administrator consultant profile"),
			message=frappe.get_traceback(),
		)
		return None


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

def _icon(paths):
	"""Wrap SVG paths into a small line-style icon (inherits currentColor)."""
	return (
		'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
		'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
		+ paths
		+ "</svg>"
	)


ICON_HOME = _icon('<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>')
ICON_SALES = _icon('<line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/>')
ICON_LEADS = _icon('<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>')
ICON_REQUESTS = _icon('<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>')
ICON_RESULTS = _icon('<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>')
ICON_FUNCTIONAL = _icon('<circle cx="12" cy="12" r="10"/><line x1="22" x2="18" y1="12" y2="12"/><line x1="6" x2="2" y1="12" y2="12"/><line x1="12" x2="12" y1="6" y2="2"/><line x1="12" x2="12" y1="22" y2="18"/>')
ICON_SESSIONS = _icon('<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>')
ICON_FOLLOWUPS = _icon('<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>')
ICON_MANAGER = _icon('<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>')
ICON_FEEDBACK = _icon('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>')


def sidebar_items(active):
	"""Sidebar menu for the current user. The sales team sees all content
	(sales + functional); functional team members see only functional-related
	sections (never the sales ones); the Developer role sees only Feedback."""
	if is_developer():
		return [{"label": _("Feedback"), "route": "/feedback", "icon": ICON_FEEDBACK, "active": active == "feedback"}]

	items = [{"label": _("Home"), "route": "/demo_portal", "icon": ICON_HOME, "active": active == "home"}]

	if is_sales():
		items += [
			{"label": _("Sales Home"), "route": "/sales_portal", "icon": ICON_SALES, "active": active == "sales"},
			{"label": _("My Leads"), "route": "/sales_portal/my_leads", "icon": ICON_LEADS, "active": active == "leads"},
			{"label": _("Demo Requests"), "route": "/sales_portal/demo_requests", "icon": ICON_REQUESTS, "active": active == "requests"},
			{"label": _("Results"), "route": "/sales_portal/results", "icon": ICON_RESULTS, "active": active == "results"},
		]

	# Functional sections are shared - the sales team sees them too
	if is_sales() or is_functional() or is_manager():
		items += [
			{"label": _("Functional Home"), "route": "/functional_portal", "icon": ICON_FUNCTIONAL, "active": active == "functional"},
			{"label": _("My Sessions"), "route": "/functional_portal/my_sessions", "icon": ICON_SESSIONS, "active": active == "sessions"},
			{"label": _("Follow-ups"), "route": "/functional_portal/follow_ups", "icon": ICON_FOLLOWUPS, "active": active == "follow_ups"},
		]

	if is_manager():
		items += [{"label": _("Manager Dashboard"), "route": "/manager_portal", "icon": ICON_MANAGER, "active": active == "manager"}]

	# Shared section: template feedback is visible to every portal role
	items.append({"label": _("Feedback"), "route": "/feedback", "icon": ICON_FEEDBACK, "active": active == "feedback"})

	return items


def greeting():
	"""Time-of-day greeting, e.g. 'Good morning'."""
	hour = frappe.utils.now_datetime().hour
	if hour < 12:
		return _("Good morning")
	if hour < 17:
		return _("Good afternoon")
	return _("Good evening")


def portal_context(context, title, required_roles, active, subtitle=""):
	"""Standard context setup for login-required, role-guarded portal pages."""
	context.login_required = True
	context.no_cache = 1
	# Belt & braces: force a fresh render with no-store headers for every portal
	# page so a stale cached copy (which once caused the 'User Required' popup
	# on the Link profile button) can never be served to the browser again.
	frappe.local.no_cache = True
	frappe.local.flags.disable_website_cache = True
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
	context.is_developer = is_developer()
	# Show the user's actual roles in the topbar (diagnostic aid for the
	# role-based sidebar: e.g. an account with the Developer role correctly
	# sees only Feedback).
	context.user_roles_display = ", ".join(
		sorted(r for r in user_roles() if r not in {"All", "Guest", "Full Name"})
	) or "-"
	context.full_name = frappe.utils.get_fullname(frappe.session.user)
	context.greeting = greeting()
	context.today_pretty = frappe.utils.now_datetime().strftime("%A, %d %B %Y")
	context.sidebar_items = sidebar_items(active)
	# Full-bleed dashboard layout: skip the standard website container
	# (web.html renders <main class="container my-4"> unless full_width is set)
	context.full_width = True
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
		where ifnull(fc.status, '') != 'Inactive'
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
		{"title": _("Demo Feedback"), "route": "/feedback", "role": "Developer"},
	]
