# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Dev Feedback — developers view and respond to session feedback from managers."""

import frappe
from frappe import _

from functional_demo.portal import portal_context


def get_context(context):
    portal_context(
        context,
        _("Developer Feedback"),
        ["Developer", "System Manager"],
        active="dev_feedback",
        subtitle=_("View and respond to session feedback from managers"),
    )

    # All session feedback for developers to review
    feedback_list = frappe.get_all(
        "Session Feedback",
        fields=[
            "name", "demo_session", "demo_request", "customer",
            "functional_consultant", "sales_person",
            "feedback_type", "priority", "subject", "description",
            "developer_response", "responded_by", "responded_on",
            "status", "creation", "owner",
        ],
        order_by="creation desc",
        ignore_permissions=True,
        limit_page_length=1000,
    ) or []

    # Resolve display names in bulk
    customer_ids = {fb.get("customer") for fb in feedback_list if fb.get("customer")}
    customer_names = {}
    if customer_ids:
        for c in frappe.get_all("Customer", filters={"name": ["in", list(customer_ids)]},
                                fields=["name", "customer_name"], ignore_permissions=True):
            customer_names[c.name] = c.customer_name

    consultant_ids = {fb.get("functional_consultant") for fb in feedback_list if fb.get("functional_consultant")}
    consultant_names = {}
    if consultant_ids:
        for c in frappe.get_all("Functional Consultant",
                                filters={"name": ["in", list(consultant_ids)]},
                                fields=["name", "consultant_name"], ignore_permissions=True):
            consultant_names[c.name] = c.consultant_name

    user_ids = set()
    for fb in feedback_list:
        if fb.get("owner"):
            user_ids.add(fb.owner)
        if fb.get("responded_by"):
            user_ids.add(fb.responded_by)
    user_names = {}
    if user_ids:
        for u in frappe.get_all("User", filters={"name": ["in", list(user_ids)]},
                                fields=["name", "full_name", "email"], ignore_permissions=True):
            user_names[u.name] = u.full_name or u.email or u.name

    for fb in feedback_list:
        fb["customer_display"] = customer_names.get(fb.customer) or fb.customer or "-"
        fb["consultant_display"] = consultant_names.get(fb.functional_consultant) or fb.functional_consultant or "-"
        fb["submitted_by"] = user_names.get(fb.owner) or fb.owner or "-"
        fb["responded_by_display"] = user_names.get(fb.responded_by) or fb.responded_by or "-"
        fb["creation_display"] = frappe.utils.format_datetime(fb.creation, "dd MMM yyyy, hh:mm a") if fb.creation else "-"

    # Completed sessions for sending feedback
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

    # Resolve session display names in bulk
    session_customer_ids = {s.get("customer") for s in sessions if s.get("customer")}
    session_customer_names = {}
    if session_customer_ids:
        for c in frappe.get_all("Customer", filters={"name": ["in", list(session_customer_ids)]},
                                fields=["name", "customer_name"], ignore_permissions=True):
            session_customer_names[c.name] = c.customer_name

    session_consultant_ids = {s.get("functional_consultant") for s in sessions if s.get("functional_consultant")}
    session_consultant_names = {}
    if session_consultant_ids:
        for c in frappe.get_all("Functional Consultant",
                                filters={"name": ["in", list(session_consultant_ids)]},
                                fields=["name", "consultant_name"], ignore_permissions=True):
            session_consultant_names[c.name] = c.consultant_name

    # Check which sessions already have feedback
    session_names = [s.name for s in sessions]
    existing_feedback_map = {}
    if session_names:
        for fb in frappe.get_all(
            "Session Feedback",
            filters={"demo_session": ["in", session_names]},
            fields=["demo_session", "name", "subject", "status", "feedback_type", "priority"],
            ignore_permissions=True,
        ):
            existing_feedback_map.setdefault(fb.demo_session, []).append(fb)

    for s in sessions:
        s["customer_display"] = session_customer_names.get(s.customer) or s.customer or s.lead or "-"
        s["consultant_display"] = session_consultant_names.get(s.functional_consultant) or s.functional_consultant or "-"
        s["has_feedback"] = bool(existing_feedback_map.get(s.name))
        s["feedback_list"] = existing_feedback_map.get(s.name, [])

    # Stats
    total = len(feedback_list)
    open_count = len([fb for fb in feedback_list if fb.status == "Open"])
    in_progress = len([fb for fb in feedback_list if fb.status == "In Progress"])
    resolved = len([fb for fb in feedback_list if fb.status == "Resolved"])
    closed = len([fb for fb in feedback_list if fb.status == "Closed"])
    bugs = len([fb for fb in feedback_list if fb.feedback_type == "Bug"])
    features = len([fb for fb in feedback_list if fb.feedback_type == "Feature Request"])

    context.update({
        "feedback_list": feedback_list,
        "sessions": sessions,
        "total": total,
        "open_count": open_count,
        "in_progress": in_progress,
        "resolved": resolved,
        "closed": closed,
        "bugs": bugs,
        "features": features,
    })
