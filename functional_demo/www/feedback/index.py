# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.api import get_demo_feedback_data
from functional_demo.portal import list_note, portal_context


def get_context(context):
	portal_context(
		context,
		_("Demo Feedback"),
		["Sales User", "Sales Manager", "Functional Consultant", "Functional Team Manager", "Feedback Viewer", "Developer"],
		active="feedback",
		subtitle=_("Feedback recorded against the demos"),
	)

	# Template filter (?template=Law) - the page groups feedback by the Demo
	# Template it was recorded against, so each template (Law, Hospitality, ...)
	# can be reviewed on its own.
	all_feedback = get_demo_feedback_data()
	selected = (frappe.form_dict.get("template") or "").strip()

	# ordered template list with counts (No Template always last)
	counts = {}
	for f in all_feedback:
		name = f.get("template") or "No Template"
		counts[name] = counts.get(name, 0) + 1
	templates = sorted(
		counts.items(),
		key=lambda kv: (kv[0] == "No Template", kv[0].lower()),
	)
	context.templates = [{"name": name, "count": count} for name, count in templates]
	context.selected_template = selected if selected in counts else ""
	context.total_all = len(all_feedback)

	context.feedback = [
		f
		for f in all_feedback
		if not context.selected_template or (f.get("template") or "No Template") == context.selected_template
	]
	context.total_feedback = len(context.feedback)
	context.list_note = (
		""
		if context.selected_template
		else list_note(
			len(context.feedback),
			frappe.db.count(
				"Demo Session",
				{"demo_status": ["in", ["Completed", "Follow-up Required", "Closed"]]},
			),
			_("feedback entries"),
		)
	)
