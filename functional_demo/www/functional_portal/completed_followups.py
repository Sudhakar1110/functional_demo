# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import list_note, portal_context, is_sales_manager

STATUS_OPTIONS = ["Open", "In Progress", "Completed", "Overdue"]
OUTCOME_OPTIONS = [
	"Pending", "Additional Discussion", "Additional Demo Required",
	"Demo Done", "Trial", "Quotation Send",
	"Not Interested", "Closed",
]


def _sales_user_options():
	"""Active sales users (Sales User / Sales Manager) for the manager filter."""
	names = set()
	for role in ("Sales User", "Sales Manager"):
		for u in frappe.get_all(
			"Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent"
		) or []:
			if u not in ("Administrator", "Guest"):
				names.add(u)
	users = frappe.get_all(
		"User",
		filters={"name": ["in", list(names)], "enabled": 1},
		fields=["name", "full_name"],
		order_by="full_name asc",
	) or []
	return [{"name": u["name"], "label": u["full_name"] or u["name"]} for u in users]


def get_context(context):
	is_mgr = is_sales_manager()
	portal_context(
		context,
		_("Follow-ups Completed"),
		["Sales Manager", "Sales User"],
		active="completed_followups",
		subtitle=(
			_("All completed follow-ups across demo requests")
			if is_mgr
			else _("Your completed follow-ups")
		),
	)
	user = frappe.session.user
	filters = {"status": "Completed"}
	selected_person = (frappe.form_dict.get("sales_person") or "").strip()
	if not is_mgr:
		# A Sales User only sees their own assigned follow-ups.
		filters["sales_person"] = user
	elif selected_person:
		filters["sales_person"] = selected_person
	follow_ups = frappe.get_all(
		"Demo Follow Up",
		filters=filters,
		fields=[
			"name", "demo_request", "demo_session", "customer",
			"follow_up_date", "creation", "modified",
			"status", "outcome", "next_action", "remarks",
			"assigned_to", "sales_person", "description",
		],
		order_by="modified desc",
		limit_page_length=1000,
		ignore_permissions=True,
	) or []
	for fu in follow_ups:
		fu["due_display"] = (
			frappe.utils.format_date(fu.get("follow_up_date"), "medium")
			if fu.get("follow_up_date") else "-"
		)
		fu["created_display"] = (
			frappe.utils.format_datetime(fu.get("creation"), "dd MMM yyyy, hh:mm a")
			if fu.get("creation") else "-"
		)
		fu["completed_display"] = (
			frappe.utils.format_datetime(fu.get("modified"), "dd MMM yyyy, hh:mm a")
			if fu.get("modified") else "-"
		)
		if fu.get("assigned_to"):
			fu["assigned_display"] = (
				frappe.db.get_value("User", fu["assigned_to"], "full_name")
				or fu["assigned_to"]
			)
		else:
			fu["assigned_display"] = "-"
		if fu.get("sales_person"):
			fu["sales_person_display"] = (
				frappe.db.get_value("User", fu["sales_person"], "full_name")
				or fu["sales_person"]
			)
		else:
			fu["sales_person_display"] = "-"
	context.follow_ups = follow_ups
	context.status_options = STATUS_OPTIONS
	context.outcome_options = OUTCOME_OPTIONS
	context.is_sales_manager = is_mgr
	context.sales_person = selected_person if is_mgr else user
	context.sales_users = _sales_user_options() if is_mgr else []
	context.list_note = list_note(
		len(context.follow_ups),
		frappe.db.count("Demo Follow Up", {"status": "Completed"}),
		_("completed follow-ups"),
	)
