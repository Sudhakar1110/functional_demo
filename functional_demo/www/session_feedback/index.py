# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Manager Session Feedback — managers select sessions and send feedback to developers."""

import frappe
from frappe import _

from functional_demo.portal import portal_context


def get_context(context):
    portal_context(
        context,
        _("Session Feedback"),
        ["Sales Manager", "Functional Team Manager"],
        active="session_feedback",
        subtitle=_("Send feedback about sessions to the development team"),
    )

    # Completed sessions for selection
    sessions = frappe.get_all(
        "Demo Session",
        filters={"demo_status": ["in", ["Completed", "Closed"]]},
        fields=[
            "name", "demo_request", "customer", "lead",
            "functional_consultant", "sales_person",
            "scheduled_date", "completed_on", "demo_status",
            "overall_feedback", "final_result", "interested_module",
        ],
        order_by="completed_on desc",
        ignore_permissions=True,
        limit_page_length=500,
    ) or []

    # Resolve display names in bulk
    customer_ids = {s.get("customer") for s in sessions if s.get("customer")}
    customer_names = {}
    if customer_ids:
        for c in frappe.get_all("Customer", filters={"name": ["in", list(customer_ids)]},
                                fields=["name", "customer_name"], ignore_permissions=True):
            customer_names[c.name] = c.customer_name

    consultant_ids = {s.get("functional_consultant") for s in sessions if s.get("functional_consultant")}
    consultant_names = {}
    if consultant_ids:
        for c in frappe.get_all("Functional Consultant",
                                filters={"name": ["in", list(consultant_ids)]},
                                fields=["name", "consultant_name"], ignore_permissions=True):
            consultant_names[c.name] = c.consultant_name

    # Check which sessions already have feedback and developer response status
    session_names = [s.name for s in sessions]
    existing_feedback = {}
    if session_names:
        for fb in frappe.get_all(
            "Session Feedback",
            filters={"demo_session": ["in", session_names]},
            fields=["demo_session", "name", "subject", "status", "feedback_type", "priority",
                    "developer_response", "responded_by", "responded_on"],
            ignore_permissions=True,
        ):
            existing_feedback.setdefault(fb.demo_session, []).append(fb)

    # Resolve responded_by display names
    responded_by_ids = set()
    for fb_list in existing_feedback.values():
        for fb in fb_list:
            if fb.get("responded_by"):
                responded_by_ids.add(fb["responded_by"])
    responded_by_names = {}
    if responded_by_ids:
        for u in frappe.get_all("User", filters={"name": ["in", list(responded_by_ids)]},
                                fields=["name", "full_name", "email"], ignore_permissions=True):
            responded_by_names[u.name] = u.full_name or u.email or u.name

    for s in sessions:
        s["customer_display"] = customer_names.get(s.customer) or s.customer or s.lead or "-"
        s["consultant_display"] = consultant_names.get(s.functional_consultant) or s.functional_consultant or "-"
        s["has_feedback"] = bool(existing_feedback.get(s.name))
        s["feedback_list"] = existing_feedback.get(s.name, [])
        # Check if any feedback for this session has a developer response
        s["has_response"] = any(
            fb.get("developer_response") for fb in s["feedback_list"]
        )
        # Find the first responded feedback for display
        responded_fb = next(
            (fb for fb in s["feedback_list"] if fb.get("developer_response")), None
        )
        if responded_fb:
            s["response_text"] = responded_fb.get("developer_response") or "-"
            s["response_by"] = responded_by_names.get(responded_fb.get("responded_by")) or responded_fb.get("responded_by") or "-"
            s["response_on"] = frappe.utils.format_datetime(responded_fb.get("responded_on"), "dd MMM yyyy, hh:mm a") if responded_fb.get("responded_on") else "-"
            s["response_subject"] = responded_fb.get("subject") or "-"
            s["response_type"] = responded_fb.get("feedback_type") or "-"
            s["response_priority"] = responded_fb.get("priority") or "-"
            s["response_status"] = responded_fb.get("status") or "-"

    # Stats
    total = len(sessions)
    with_feedback = len([s for s in sessions if s["has_feedback"]])
    without_feedback = total - with_feedback

    context.update({
        "sessions": sessions,
        "total_sessions": total,
        "with_feedback": with_feedback,
        "without_feedback": without_feedback,
    })
