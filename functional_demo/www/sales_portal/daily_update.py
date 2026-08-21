# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate

from functional_demo.portal import portal_context


def _day_range(d):
	"""Return (start, end) datetime strings for a given date."""
	ds = str(d)
	return ds + " 00:00:00", ds + " 23:59:59"


def get_context(context):
    portal_context(
        context,
        _("End of Day Update"),
        ["Sales User", "Sales Manager"],
        active="daily_update",
        subtitle=_("Today's activity summary and tomorrow's outlook"),
    )

    today = getdate(frappe.utils.today())
    tomorrow = add_days(today, 1)
    day_start, day_end = _day_range(today)

    # ── Today's Activity ──────────────────────────────────────────────
    # New requests created today
    new_requests = frappe.get_all(
        "Demo Request",
        filters={"creation": ["between", [day_start, day_end]]},
        fields=["name", "customer", "sales_person", "priority", "status", "interested_module", "creation"],
        order_by="creation desc",
    ) or []

    # Status changes today — requests modified today with a different status
    modified_today = frappe.get_all(
        "Demo Request",
        filters={"modified": ["between", [day_start, day_end]]},
        fields=["name", "customer", "sales_person", "status", "priority", "interested_module", "modified"],
        order_by="modified desc",
    ) or []

    # Separate "truly new" from "status changed"
    new_names = {r.name for r in new_requests}
    status_changes = [r for r in modified_today if r.name not in new_names]

    # Demos completed today
    completed_today = frappe.get_all(
        "Demo Session",
        filters={
            "completed_on": ["between", [day_start, day_end]],
            "demo_status": "Completed",
        },
        fields=["name", "customer", "sales_person", "functional_consultant", "final_result", "overall_feedback", "completed_on", "demo_request"],
        order_by="completed_on desc",
    ) or []

    # Follow-ups closed/completed today
    followups_done = frappe.get_all(
        "Demo Follow Up",
        filters={
            "modified": ["between", [day_start, day_end]],
            "status": "Completed",
        },
        fields=["name", "customer", "sales_person", "demo_request", "follow_up_date", "modified"],
        order_by="modified desc",
    ) or []

    # ── Tomorrow's Outlook ────────────────────────────────────────────
    # Demos scheduled for tomorrow
    tomorrows_demos = frappe.get_all(
        "Demo Session",
        filters={
            "scheduled_date": tomorrow,
            "demo_status": ["in", ["Scheduled", "Rescheduled"]],
        },
        fields=["name", "customer", "sales_person", "functional_consultant", "scheduled_date", "start_time", "end_time", "interested_module", "meeting_link", "demo_type"],
        order_by="start_time asc",
    ) or []

    # Follow-ups due tomorrow
    tomorrows_followups = frappe.get_all(
        "Demo Follow Up",
        filters={
            "follow_up_date": tomorrow,
            "status": ["in", ["Open", "In Progress"]],
        },
        fields=["name", "customer", "sales_person", "demo_request", "follow_up_date", "status", "remarks", "subject"],
        order_by="follow_up_date asc",
    ) or []

    # ── Stale Pipeline (pending > 5 days) ─────────────────────────────
    stale_threshold = add_days(today, -5)
    stale_requests = frappe.get_all(
        "Demo Request",
        filters={
            "status": ["in", ["Draft", "Requested", "Manager Review", "Assigned"]],
            "creation": ["<=", stale_threshold],
        },
        fields=["name", "customer", "sales_person", "status", "priority", "interested_module", "creation", "preferred_demo_date"],
        order_by="creation asc",
        limit_page_length=50,
    ) or []

    # Calculate days pending for stale requests
    for r in stale_requests:
        try:
            r["days_pending"] = date_diff(today, str(r.get("creation", ""))[:10])
        except Exception:
            r["days_pending"] = 0

    # ── Pipeline Funnel ───────────────────────────────────────────────
    all_requests = frappe.get_all(
        "Demo Request",
        fields=["name", "status"],
        limit_page_length=5000,
    ) or []

    funnel = {}
    for r in all_requests:
        s = r.get("status") or "Draft"
        funnel[s] = funnel.get(s, 0) + 1

    pipeline_funnel = [
        {"label": "Draft", "count": funnel.get("Draft", 0), "color": "#9CA3AF"},
        {"label": "Requested", "count": funnel.get("Requested", 0), "color": "#114EFF"},
        {"label": "Manager Review", "count": funnel.get("Manager Review", 0), "color": "#D97706"},
        {"label": "Assigned", "count": funnel.get("Assigned", 0), "color": "#7C3AED"},
        {"label": "Scheduled", "count": funnel.get("Scheduled", 0), "color": "#114EFF"},
        {"label": "Demo In Progress", "count": funnel.get("Demo In Progress", 0), "color": "#D96C0A"},
        {"label": "Completed", "count": funnel.get("Demo Completed", 0), "color": "#009A52"},
        {"label": "Follow-up Required", "count": funnel.get("Follow-up Required", 0), "color": "#A16207"},
        {"label": "Demo Completed", "count": funnel.get("Converted", 0), "color": "#009A52"},
        {"label": "Not Interested", "count": funnel.get("Not Interested", 0), "color": "#E11D48"},
    ]

    # ── KPI Counts ────────────────────────────────────────────────────
    context.new_requests_count = len(new_requests)
    context.status_changes_count = len(status_changes)
    context.completed_today_count = len(completed_today)
    context.followups_done_count = len(followups_done)
    context.tomorrows_demos_count = len(tomorrows_demos)
    context.tomorrows_followups_count = len(tomorrows_followups)
    context.stale_count = len(stale_requests)

    # ── Pass to template ──────────────────────────────────────────────
    context.new_requests = new_requests
    context.status_changes = status_changes
    context.completed_today = completed_today
    context.followups_done = followups_done
    context.tomorrows_demos = tomorrows_demos
    context.tomorrows_followups = tomorrows_followups
    context.stale_requests = stale_requests
    context.pipeline_funnel = pipeline_funnel
    context.today_display = frappe.utils.format_date(today, "dd MMM yyyy")
    context.tomorrow_display = frappe.utils.format_date(tomorrow, "dd MMM yyyy")

    return context
