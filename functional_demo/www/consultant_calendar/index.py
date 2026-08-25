# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Consultant Calendar — month-view of all consultant demo sessions for managers."""

import calendar
import frappe
from frappe import _

from functional_demo.portal import portal_context


def get_context(context):
    portal_context(
        context,
        _("Consultant Calendar"),
        ["Sales Manager", "Functional Team Manager"],
        active="consultant_calendar",
        subtitle=_("All consultant sessions at a glance"),
    )

    # Only functional team managers and sales managers can access
    user_roles = frappe.get_roles()
    if not any(r in user_roles for r in ("Sales Manager", "Functional Team Manager")):
        frappe.throw(_("You do not have permission to access this page."))

    # Get month/year from query params or default to current
    today = frappe.utils.today()
    month = frappe.form_dict.get("month") or frappe.utils.getdate(today).month
    year = frappe.form_dict.get("year") or frappe.utils.getdate(today).year
    try:
        month = int(month)
        year = int(year)
    except (ValueError, TypeError):
        month = frappe.utils.getdate(today).month
        year = frappe.utils.getdate(today).year

    # Clamp values
    month = max(1, min(12, month))
    year = max(2020, min(2099, year))

    context.month = month
    context.year = year
    context.month_name = calendar.month_name[month]

    # Previous / next month for navigation
    if month == 1:
        context.prev_month = 12
        context.prev_year = year - 1
    else:
        context.prev_month = month - 1
        context.prev_year = year
    if month == 12:
        context.next_month = 1
        context.next_year = year + 1
    else:
        context.next_month = month + 1
        context.next_year = year

    # Get all active consultants
    consultants = frappe.get_all(
        "Functional Consultant",
        fields=["name", "consultant_name", "specialization", "availability", "user"],
        filters={"status": ["!=", "Inactive"]},
        order_by="consultant_name asc",
        ignore_permissions=True,
    ) or []
    context.consultants = consultants
    context.consultant_map = {c.name: c.consultant_name for c in consultants}

    # Get all demo sessions for this month
    import datetime
    month_start = datetime.date(year, month, 1)
    if month == 12:
        month_end = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        month_end = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

    sessions = frappe.get_all(
        "Demo Session",
        filters={
            "scheduled_date": ["between", [str(month_start), str(month_end)]],
            "demo_status": ["not in", ["Cancelled"]],
        },
        fields=[
            "name", "customer", "functional_consultant", "sales_person",
            "scheduled_date", "start_time", "end_time", "demo_status",
            "meeting_link", "demo_type", "final_result",
        ],
        order_by="scheduled_date asc, start_time asc",
    ) or []

    # Enrich sessions with consultant names
    for s in sessions:
        s["consultant_name"] = context.consultant_map.get(
            s.get("functional_consultant"), s.get("functional_consultant") or "-"
        )
        s["date_str"] = str(s.get("scheduled_date") or "")
        # Color coding based on status
        status = s.get("demo_status") or "Scheduled"
        s["color"] = {
            "Scheduled": "#3B82F6",
            "Rescheduled": "#8B5CF6",
            "In Progress": "#F59E0B",
            "Completed": "#10B981",
            "Closed": "#6B7280",
        }.get(status, "#3B82F6")

    context.sessions = sessions

    # Build calendar grid data
    cal = calendar.Calendar(firstweekday=0)  # Monday first
    month_days = cal.monthdayscalendar(year, month)

    # Group sessions by date string
    sessions_by_date = {}
    for s in sessions:
        ds = s.get("date_str", "")
        if ds:
            sessions_by_date.setdefault(ds, []).append(s)

    context.calendar_weeks = []
    for week in month_days:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({"day": 0, "sessions": []})
            else:
                date_str = "{0}-{1:02d}-{2:02d}".format(year, month, day)
                is_today = date_str == today
                week_data.append({
                    "day": day,
                    "date_str": date_str,
                    "is_today": is_today,
                    "sessions": sessions_by_date.get(date_str, []),
                })
        context.calendar_weeks.append(week_data)

    # Stats for the month
    context.total_sessions = len(sessions)
    context.scheduled_count = sum(1 for s in sessions if s.get("demo_status") in ("Scheduled", "Rescheduled"))
    context.completed_count = sum(1 for s in sessions if s.get("demo_status") == "Completed")
    context.in_progress_count = sum(1 for s in sessions if s.get("demo_status") == "In Progress")

    return context
