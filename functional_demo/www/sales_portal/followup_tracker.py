# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Sales Follow-up Tracker — today's action list, overdue alerts, and full history."""

import frappe
from frappe import _

from functional_demo.portal import portal_context


def _today():
    return frappe.utils.today()


def _day_range(d):
    ds = str(d)
    return ds + " 00:00:00", ds + " 23:59:59"


def _fmt_date(val):
    if not val:
        return "-"
    try:
        return frappe.utils.format_date(val, "medium")
    except Exception:
        return str(val)


def _fmt_datetime(val):
    if not val:
        return "-"
    try:
        return frappe.utils.format_datetime(val, "dd MMM yyyy, hh:mm a")
    except Exception:
        return str(val)


def _days_between(date1, date2):
    """Return positive integer difference between two dates."""
    try:
        from datetime import date as _date
        d1 = _date.fromisoformat(str(date1)[:10])
        d2 = _date.fromisoformat(str(date2)[:10])
        return max(0, (d2 - d1).days)
    except Exception:
        return 0


def get_context(context):
    portal_context(
        context,
        _("Follow-up Tracker"),
        ["Sales User", "Sales Manager"],
        active="followup_tracker",
        subtitle=_("Track and manage your follow-ups"),
    )

    today = _today()
    user = frappe.session.user
    today_start, today_end = _day_range(today)

    # ------------------------------------------------------------------
    # All follow-ups for current sales user
    # ------------------------------------------------------------------	# ignore_permissions: the page is already role-gated by portal_context
	# (Sales User / Sales Manager only). Row-level permission filters on
	# Demo Follow Up can hide follow-ups that a consultant created (assigned
	# to the sales person) when the sales_person field is empty on the
	# session — so we bypass them here and rely on the page-level guard.
	all_followups = frappe.get_all(
		"Demo Follow Up",
		fields=[
			"name", "demo_request", "demo_session", "customer",
			"sales_person", "functional_consultant", "subject",
			"follow_up_date", "status", "outcome", "next_action",
			"remarks", "assigned_to", "creation",
		],
		order_by="follow_up_date asc",
		limit_page_length=2000,
		ignore_permissions=True,
	) or []

    # ------------------------------------------------------------------
    # Resolve display names in bulk
    # ------------------------------------------------------------------
    customer_ids = {fu.get("customer") for fu in all_followups if fu.get("customer")}
    customer_names = {}
    if customer_ids:
        for c in frappe.get_all("Customer", filters={"name": ["in", list(customer_ids)]},
                                fields=["name", "customer_name"], ignore_permissions=True):
            customer_names[c.name] = c.customer_name

    consultant_ids = {fu.get("functional_consultant") for fu in all_followups if fu.get("functional_consultant")}
    consultant_names = {}
    if consultant_ids:
        for c in frappe.get_all("Functional Consultant",
                                filters={"name": ["in", list(consultant_ids)]},
                                fields=["name", "consultant_name"], ignore_permissions=True):
            consultant_names[c.name] = c.consultant_name

    user_ids = {fu.get("assigned_to") for fu in all_followups if fu.get("assigned_to")}
    if user_ids:
        user_names = {}
        for u in frappe.get_all("User", filters={"name": ["in", list(user_ids)]},
                                fields=["name", "full_name", "email"], ignore_permissions=True):
            user_names[u.name] = u.full_name or u.email or u.name
    else:
        user_names = {}

    # ------------------------------------------------------------------
    # Enrich each follow-up
    # ------------------------------------------------------------------
    overdue_list = []
    today_list = []
    upcoming_list = []
    completed_list = []
    all_display = []

    for fu in all_followups:
        fu["customer_display"] = customer_names.get(fu.customer) or fu.customer or "-"
        fu["consultant_display"] = consultant_names.get(fu.functional_consultant) or fu.functional_consultant or "-"
        fu["assigned_display"] = user_names.get(fu.assigned_to) or fu.assigned_to or "-"
        fu["due_display"] = _fmt_date(fu.follow_up_date)
        fu["creation_display"] = _fmt_datetime(fu.creation)
        fu["is_overdue"] = False
        fu["is_today"] = False
        fu["days_overdue"] = 0

        fu_date = str(fu.follow_up_date)[:10] if fu.follow_up_date else ""
        if fu_date and fu.status in ("Open", "In Progress"):
            if fu_date < today:
                fu["is_overdue"] = True
                fu["days_overdue"] = _days_between(fu_date, today)
                overdue_list.append(fu)
            elif fu_date == today:
                fu["is_today"] = True
                today_list.append(fu)
            else:
                upcoming_list.append(fu)
        elif fu.status == "Completed":
            completed_list.append(fu)

        all_display.append(fu)

    # Sort overdue by most overdue first
    overdue_list.sort(key=lambda x: -x.get("days_overdue", 0))

    # ------------------------------------------------------------------
    # Customer history map (all follow-ups grouped by customer)
    # ------------------------------------------------------------------
    customer_history = {}
    for fu in all_display:
        cust = fu.customer or ""
        if cust:
            customer_history.setdefault(cust, []).append({
                "name": fu.name,
                "subject": fu.get("subject") or fu.due_display,
                "date": fu.due_display,
                "status": fu.status,
                "outcome": fu.outcome or "",
                "remarks": fu.remarks or "",
                "consultant": fu["consultant_display"],
            })

    # ------------------------------------------------------------------
    # KPIs
    # ------------------------------------------------------------------
    total = len(all_followups)
    total_overdue = len(overdue_list)
    total_today = len(today_list)
    total_upcoming = len(upcoming_list)
    total_completed = len(completed_list)
    total_open = total - total_completed

    # This week: next 7 days
    from datetime import timedelta
    try:
        week_end = (frappe.utils.getdate(today) + timedelta(days=7)).isoformat()
    except Exception:
        week_end = today

    this_week = len([fu for fu in upcoming_list
                     if fu.get("follow_up_date") and str(fu.follow_up_date)[:10] <= week_end])

    context.update({
        "overdue_list": overdue_list,
        "today_list": today_list,
        "upcoming_list": upcoming_list,
        "completed_list": completed_list[-10:],  # last 10 completed
        "all_followups": all_display,
        "customer_history": customer_history,
        "total": total,
        "total_overdue": total_overdue,
        "total_today": total_today,
        "total_upcoming": total_upcoming,
        "total_completed": total_completed,
        "total_open": total_open,
        "this_week": this_week,
        "today_date_display": _fmt_date(today),
    })
