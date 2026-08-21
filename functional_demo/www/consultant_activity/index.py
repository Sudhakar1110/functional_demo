# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import guard, is_admin, is_manager, portal_context


def get_context(context):
    """Consultant Activity page — visible only to Functional Team Manager
    (and System Manager / Administrator for convenience)."""
    portal_context(
        context,
        _("Consultant Activity"),
        ["Functional Team Manager"],
        active="consultant_activity",
        subtitle=_("Overview of all consultants and their demo activity"),
    )

    # Filter parameters from query string
    filter_spec = frappe.form_dict.get("specialization") or ""
    filter_avail = frappe.form_dict.get("availability") or ""
    filter_status = frappe.form_dict.get("status") or ""
    sort_by = frappe.form_dict.get("sort") or "name"

    # Consultants with full profile details
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

    # Specializations for filter dropdown
    specializations = sorted(set(
        c.get("specialization") or "Generalist" for c in consultants if (c.get("status") or "") != "Inactive"
    ))

    consultant_details = []
    for c in consultants:
        if (c.get("status") or "") == "Inactive":
            continue

        # Apply filters
        if filter_spec and (c.get("specialization") or "Generalist") != filter_spec:
            continue
        if filter_avail and (c.get("availability") or "Available") != filter_avail:
            continue

        # Current active session (In Progress)
        active_session = frappe.get_all(
            "Demo Session",
            filters={
                "functional_consultant": c.name,
                "demo_status": "In Progress",
            },
            fields=["name", "customer", "scheduled_date", "start_time", "interested_module", "demo_request", "meeting_link", "demo_type"],
            limit=1,
        ) or []

        # Upcoming scheduled sessions
        upcoming = frappe.get_all(
            "Demo Session",
            filters={
                "functional_consultant": c.name,
                "demo_status": ["in", ["Scheduled", "Rescheduled"]],
            },
            fields=["name", "customer", "scheduled_date", "start_time", "interested_module", "demo_request", "meeting_link", "demo_type"],
            order_by="scheduled_date asc",
            limit_page_length=10,
        ) or []

        # Today's demos
        todays = frappe.get_all(
            "Demo Session",
            filters={
                "functional_consultant": c.name,
                "demo_status": ["in", ["Scheduled", "In Progress"]],
                "scheduled_date": frappe.utils.today(),
            },
            fields=["name", "customer", "scheduled_date", "start_time", "demo_status", "interested_module", "demo_request", "meeting_link", "demo_type"],
            order_by="start_time asc",
        ) or []

        # Total completed
        completed_count = frappe.db.count(
            "Demo Session",
            {"functional_consultant": c.name, "demo_status": "Completed"},
        ) or 0

        # Pending assigned requests (no session yet) — with priority & SLA info
        pending_requests = frappe.get_all(
            "Demo Request",
            filters={"functional_consultant": c.name, "status": "Assigned"},
            fields=["name", "customer", "interested_module", "preferred_demo_date", "sales_person", "priority", "sla_due_date", "sla_breached", "creation"],
            order_by="preferred_demo_date asc",
        ) or []
        pending_count = len(pending_requests)

        # Recent completed demos (last 5) — with overall_feedback
        recent_completed = frappe.get_all(
            "Demo Session",
            filters={"functional_consultant": c.name, "demo_status": "Completed"},
            fields=["name", "customer", "scheduled_date", "completed_on", "overall_feedback", "final_result", "demo_type", "interested_module"],
            order_by="completed_on desc",
            limit_page_length=5,
        ) or []

        # Rescheduled count
        rescheduled_count = frappe.db.count(
            "Demo Session",
            {"functional_consultant": c.name, "demo_status": "Rescheduled"},
        ) or 0

        # SLA breached count
        sla_breached_count = frappe.db.count(
            "Demo Request",
            {"functional_consultant": c.name, "sla_breached": 1, "status": ["in", ["Assigned", "Manager Review"]]},
        ) or 0

        in_progress_count = len(active_session)
        upcoming_count = len(upcoming)

        # Enrich sessions
        all_sessions = active_session + upcoming + todays
        for sess in all_sessions:
            sess["date_display"] = (
                frappe.utils.format_date(sess.get("scheduled_date"), "medium")
                if sess.get("scheduled_date")
                else "-"
            )
            if not sess.get("interested_module") and sess.get("demo_request"):
                mod = frappe.db.get_value("Demo Request", sess["demo_request"], "interested_module")
                if mod:
                    sess["interested_module"] = mod

        # Enrich pending requests
        for pr in pending_requests:
            pr["date_display"] = (
                frappe.utils.format_date(pr.get("preferred_demo_date"), "medium")
                if pr.get("preferred_demo_date")
                else "-"
            )
            # Days pending since creation
            if pr.get("creation"):
                from frappe.utils import date_diff
                try:
                    pr["days_pending"] = date_diff(frappe.utils.today(), str(pr["creation"])[:10])
                except Exception:
                    pr["days_pending"] = 0

        # Enrich recent completed
        for rc in recent_completed:
            rc["completed_display"] = (
                frappe.utils.format_datetime(rc.get("completed_on"), "dd MMM yyyy")
                if rc.get("completed_on")
                else "-"
            )

        # Determine status badge
        if active_session:
            status_label = "In Progress"
            status_class = "b-demo-in-progress"
        elif upcoming:
            status_label = "Scheduled ({0})".format(upcoming_count)
            status_class = "b-scheduled"
        elif pending_count:
            status_label = "Pending ({0})".format(pending_count)
            status_class = "b-manager-review"
        else:
            status_label = "Free"
            status_class = "b-draft"

        # Apply status filter
        if filter_status:
            filter_status_lower = filter_status.lower()
            if filter_status_lower == "in_progress" and status_label != "In Progress":
                continue
            elif filter_status_lower == "scheduled" and "Scheduled" not in status_label:
                continue
            elif filter_status_lower == "pending" and "Pending" not in status_label:
                continue
            elif filter_status_lower == "free" and status_label != "Free":
                continue

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
            "in_progress_count": in_progress_count,
            "upcoming_count": upcoming_count,
            "rescheduled_count": rescheduled_count,
            "sla_breached_count": sla_breached_count,
        })

    # Sorting
    if sort_by == "completed":
        consultant_details.sort(key=lambda x: x["completed_count"], reverse=True)
    elif sort_by == "pending":
        consultant_details.sort(key=lambda x: x["pending_count"], reverse=True)
    elif sort_by == "status":
        status_order = {"In Progress": 0, "Scheduled": 1, "Pending": 2, "Free": 3}
        consultant_details.sort(key=lambda x: status_order.get(x["status_label"].split(" ")[0], 9))
    else:
        consultant_details.sort(key=lambda x: x["consultant_name"])

    context.consultant_details = consultant_details

    # Summary counts
    total_consultants = len(consultant_details)
    total_active = sum(1 for c in consultant_details if c["active_session"])
    total_scheduled = sum(1 for c in consultant_details if c["upcoming_sessions"] and not c["active_session"])
    total_free = sum(1 for c in consultant_details if not c["active_session"] and not c["upcoming_sessions"] and not c["pending_count"])
    total_completed = sum(c["completed_count"] for c in consultant_details)
    total_pending = sum(c["pending_count"] for c in consultant_details)
    total_sla_breached = sum(c["sla_breached_count"] for c in consultant_details)
    total_rescheduled = sum(c["rescheduled_count"] for c in consultant_details)
    avg_demos = round(total_completed / total_consultants, 1) if total_consultants else 0

    context.total_consultants = total_consultants
    context.total_active = total_active
    context.total_scheduled = total_scheduled
    context.total_free = total_free
    context.total_completed = total_completed
    context.total_pending = total_pending
    context.total_sla_breached = total_sla_breached
    context.total_rescheduled = total_rescheduled
    context.avg_demos = avg_demos

    # Filter context
    context.filter_spec = filter_spec
    context.filter_avail = filter_avail
    context.filter_status = filter_status
    context.sort_by = sort_by
    context.specializations = specializations
    context.availabilities = ["Available", "Busy", "On Leave", "Unavailable"]

    # ── Demo Schedule Pipeline Funnel ────────────────────────────────
    all_sessions = frappe.get_all(
        "Demo Session",
        fields=["name", "demo_status"],
        limit_page_length=5000,
        ignore_permissions=True,
    ) or []
    session_funnel = {}
    for s in all_sessions:
        st = s.get("demo_status") or "Scheduled"
        session_funnel[st] = session_funnel.get(st, 0) + 1
    context.pipeline_funnel = [
        {"label": "Scheduled", "count": session_funnel.get("Scheduled", 0), "color": "#114EFF"},
        {"label": "Rescheduled", "count": session_funnel.get("Rescheduled", 0), "color": "#7C3AED"},
        {"label": "In Progress", "count": session_funnel.get("In Progress", 0), "color": "#D96C0A"},
        {"label": "Completed", "count": session_funnel.get("Completed", 0), "color": "#009A52"},
        {"label": "Cancelled", "count": session_funnel.get("Cancelled", 0), "color": "#E11D48"},
        {"label": "Closed", "count": session_funnel.get("Closed", 0), "color": "#9CA3AF"},
    ]

    return context
