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

    for s in sessions:
        s["customer_display"] = customer_names.get(s.customer) or s.customer or s.lead or "-"
        s["consultant_display"] = consultant_names.get(s.functional_consultant) or s.functional_consultant or "-"
        s["has_feedback"] = bool(existing_feedback.get(s.name))
        s["feedback_list"] = existing_feedback.get(s.name, [])
        # Check if any feedback for this session has a developer response
        s["has_response"] = any(
            fb.get("developer_response") for fb in s["feedback_list"]
        )

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
