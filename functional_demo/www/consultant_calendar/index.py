# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Consultant Activity — calendar view + full consultant dashboard for managers."""

import calendar
import datetime
import frappe
from frappe import _

from functional_demo.portal import portal_context


def get_context(context):
    portal_context(
        context,
        _("Consultant Activity"),
        ["Sales Manager", "Functional Team Manager"],
        active="consultant_activity",
        subtitle=_("Overview of all consultants and their demo activity"),
    )

    user_roles = frappe.get_roles()
    if not any(r in user_roles for r in ("Sales Manager", "Functional Team Manager")):
        frappe.throw(_("You do not have permission to access this page."))

    today = frappe.utils.today()

    # ── Calendar month/year ──
    month = frappe.form_dict.get("month") or frappe.utils.getdate(today).month
    year = frappe.form_dict.get("year") or frappe.utils.getdate(today).year
    try:
        month = int(month)
        year = int(year)
    except (ValueError, TypeError):
        month = frappe.utils.getdate(today).month
        year = frappe.utils.getdate(today).year
    month = max(1, min(12, month))
    year = max(2020, min(2099, year))

    context.month = month
    context.year = year
    context.month_name = calendar.month_name[month]

    if month == 1:
        context.prev_month, context.prev_year = 12, year - 1
    else:
        context.prev_month, context.prev_year = month - 1, year
    if month == 12:
        context.next_month, context.next_year = 1, year + 1
    else:
        context.next_month, context.next_year = month + 1, year

    # ── Consultants ──
    consultants = frappe.get_all(
        "Functional Consultant",
        fields=[
            "name", "consultant_name", "specialization", "availability", "status",
            "user", "experience_years", "department", "available_from", "available_to",
            "phone", "email",
        ],
        order_by="consultant_name asc",
        ignore_permissions=True,
    ) or []
    context.consultants = [c for c in consultants if (c.get("status") or "") != "Inactive"]
    context.consultant_map = {c.name: c.consultant_name for c in consultants}

    # ── Calendar sessions ──
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

    for s in sessions:
        s["consultant_name"] = context.consultant_map.get(
            s.get("functional_consultant"), s.get("functional_consultant") or "-"
        )
        s["date_str"] = str(s.get("scheduled_date") or "")
        status = s.get("demo_status") or "Scheduled"
        s["color"] = {
            "Scheduled": "#3B82F6", "Rescheduled": "#8B5CF6",
            "In Progress": "#F59E0B", "Completed": "#10B981", "Closed": "#6B7280",
        }.get(status, "#3B82F6")

    context.sessions = sessions

    # Build calendar grid
    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)
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
                week_data.append({
                    "day": day, "date_str": date_str,
                    "is_today": date_str == today,
                    "sessions": sessions_by_date.get(date_str, []),
                })
        context.calendar_weeks.append(week_data)

    context.total_sessions = len(sessions)
    context.scheduled_count = sum(1 for s in sessions if s.get("demo_status") in ("Scheduled", "Rescheduled"))
    context.completed_count = sum(1 for s in sessions if s.get("demo_status") == "Completed")
    context.in_progress_count = sum(1 for s in sessions if s.get("demo_status") == "In Progress")

    # ── Consultant detail cards (old consultant_activity data) ──
    consultant_details = []
    for c in consultants:
        if (c.get("status") or "") == "Inactive":
            continue

        active_session = frappe.get_all(
            "Demo Session",
            filters={"functional_consultant": c.name, "demo_status": "In Progress"},
            fields=["name", "customer", "scheduled_date", "start_time", "interested_module",
                     "demo_request", "meeting_link", "demo_type"],
            limit=1,
        ) or []

        upcoming = frappe.get_all(
            "Demo Session",
            filters={"functional_consultant": c.name, "demo_status": ["in", ["Scheduled", "Rescheduled"]]},
            fields=["name", "customer", "scheduled_date", "start_time", "interested_module",
                     "demo_request", "meeting_link", "demo_type"],
            order_by="scheduled_date asc", limit_page_length=10,
        ) or []

        todays = frappe.get_all(
            "Demo Session",
            filters={"functional_consultant": c.name, "demo_status": ["in", ["Scheduled", "In Progress"]],
                     "scheduled_date": today},
            fields=["name", "customer", "scheduled_date", "start_time", "demo_status",
                     "interested_module", "demo_request", "meeting_link", "demo_type"],
            order_by="start_time asc",
        ) or []

        completed_count = frappe.db.count(
            "Demo Session", {"functional_consultant": c.name, "demo_status": "Completed"},
        ) or 0

        pending_requests = frappe.get_all(
            "Demo Request",
            filters={"functional_consultant": c.name, "status": "Assigned"},
            fields=["name", "customer", "interested_module", "preferred_demo_date",
                     "sales_person", "priority", "sla_due_date", "sla_breached", "creation"],
            order_by="preferred_demo_date asc",
        ) or []
        pending_count = len(pending_requests)

        recent_completed = frappe.get_all(
            "Demo Session",
            filters={"functional_consultant": c.name, "demo_status": "Completed"},
            fields=["name", "customer", "scheduled_date", "completed_on", "overall_feedback",
                     "final_result", "demo_type", "interested_module"],
            order_by="completed_on desc", limit_page_length=5,
        ) or []

        rescheduled_count = frappe.db.count(
            "Demo Session", {"functional_consultant": c.name, "demo_status": "Rescheduled"},
        ) or 0

        sla_breached_count = frappe.db.count(
            "Demo Request",
            {"functional_consultant": c.name, "sla_breached": 1, "status": ["in", ["Assigned", "Manager Review"]]},
        ) or 0

        # Enrich sessions
        for sess in active_session + upcoming + todays:
            sess["date_display"] = (
                frappe.utils.format_date(sess.get("scheduled_date"), "medium")
                if sess.get("scheduled_date") else "-"
            )
            if not sess.get("interested_module") and sess.get("demo_request"):
                mod = frappe.db.get_value("Demo Request", sess["demo_request"], "interested_module")
                if mod:
                    sess["interested_module"] = mod

        for pr in pending_requests:
            pr["date_display"] = (
                frappe.utils.format_date(pr.get("preferred_demo_date"), "medium")
                if pr.get("preferred_demo_date") else "-"
            )
            if pr.get("creation"):
                from frappe.utils import date_diff
                try:
                    pr["days_pending"] = date_diff(today, str(pr["creation"])[:10])
                except Exception:
                    pr["days_pending"] = 0

        for rc in recent_completed:
            rc["completed_display"] = (
                frappe.utils.format_datetime(rc.get("completed_on"), "dd MMM yyyy")
                if rc.get("completed_on") else "-"
            )

        # Status badge
        if active_session:
            status_label, status_class = "In Progress", "b-demo-in-progress"
        elif upcoming:
            status_label, status_class = "Scheduled ({0})".format(len(upcoming)), "b-scheduled"
        elif pending_count:
            status_label, status_class = "Pending ({0})".format(pending_count), "b-manager-review"
        else:
            status_label, status_class = "Free", "b-draft"

        next_session = upcoming[0] if upcoming else None
        next_pending = pending_requests[0] if pending_requests else None

        consultant_details.append({
            "name": c.name,
            "consultant_name": c.consultant_name,
            "specialization": c.specialization or "Generalist",
            "availability": c.availability or "Available",
            "user": c.user or "",
            "experience_years": c.experience_years or 0,
            "department": c.department or "",
            "available_from": str(c.available_from or "")[:5],
            "available_to": str(c.available_to or "")[:5],
            "phone": c.phone or "",
            "email": c.email or "",
            "status_label": status_label,
            "status_class": status_class,
            "active_session": active_session[0] if active_session else None,
            "next_session": next_session,
            "next_pending": next_pending,
            "upcoming_sessions": upcoming,
            "todays_sessions": todays,
            "pending_requests": pending_requests,
            "recent_completed": recent_completed,
            "completed_count": completed_count,
            "pending_count": pending_count,
            "in_progress_count": len(active_session),
            "upcoming_count": len(upcoming),
            "rescheduled_count": rescheduled_count,
            "sla_breached_count": sla_breached_count,
        })

    consultant_details.sort(key=lambda x: x["consultant_name"])
    context.consultant_details = consultant_details

    # Summary KPIs
    total_consultants = len(consultant_details)
    context.total_consultants = total_consultants
    context.total_active = sum(1 for c in consultant_details if c["active_session"])
    context.total_scheduled = sum(1 for c in consultant_details if c["upcoming_sessions"] and not c["active_session"])
    context.total_free = sum(1 for c in consultant_details if not c["active_session"] and not c["upcoming_sessions"] and not c["pending_count"])
    context.total_completed = sum(c["completed_count"] for c in consultant_details)
    context.total_pending = sum(c["pending_count"] for c in consultant_details)
    context.total_sla_breached = sum(c["sla_breached_count"] for c in consultant_details)
    context.total_rescheduled = sum(c["rescheduled_count"] for c in consultant_details)
    context.avg_demos = round(context.total_completed / total_consultants, 1) if total_consultants else 0

    # Pipeline data
    pipeline_statuses = ["Scheduled", "Rescheduled", "In Progress", "Completed", "Cancelled", "Closed"]
    pipeline_colors = {
        "Scheduled": "#114EFF", "Rescheduled": "#7C3AED", "In Progress": "#D96C0A",
        "Completed": "#009A52", "Cancelled": "#E11D48", "Closed": "#9CA3AF",
    }
    consultant_sessions = frappe.get_all(
        "Demo Session", fields=["functional_consultant", "demo_status"],
        limit_page_length=5000, ignore_permissions=True,
    ) or []
    counts_by_consultant = {}
    for s in consultant_sessions:
        cid = s.get("functional_consultant") or "Unassigned"
        st = s.get("demo_status") or "Scheduled"
        counts_by_consultant.setdefault(cid, {})
        counts_by_consultant[cid][st] = counts_by_consultant[cid].get(st, 0) + 1

    pipeline_data = []
    for c in consultant_details:
        sc = counts_by_consultant.get(c["name"], {})
        stages = []
        for st in pipeline_statuses:
            cnt = sc.get(st, 0)
            stages.append({"label": st, "count": cnt, "color": pipeline_colors.get(st, "#9CA3AF")})
        pipeline_data.append({
            "consultant_name": c["consultant_name"],
            "consultant_initial": c["consultant_name"][:1],
            "stages": stages,
            "total": sum(stg["count"] for stg in stages),
        })
    context.pipeline_data = pipeline_data

    # Filter context
    context.filter_spec = frappe.form_dict.get("specialization") or ""
    context.filter_avail = frappe.form_dict.get("availability") or ""
    context.filter_status = frappe.form_dict.get("status") or ""
    context.sort_by = frappe.form_dict.get("sort") or "name"
    context.specializations = sorted(set(
        c.get("specialization") or "Generalist" for c in consultants if (c.get("status") or "") != "Inactive"
    ))
    context.availabilities = ["Available", "Busy", "On Leave", "Unavailable"]

    return context
