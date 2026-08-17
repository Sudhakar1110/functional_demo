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
	context.feedback = get_demo_feedback_data()
	context.total_feedback = len(context.feedback)
	context.list_note = list_note(
		len(context.feedback),
		frappe.db.count(
			"Demo Session",
			{"demo_status": ["in", ["Completed", "Follow-up Required", "Closed"]]},
		),
		_("feedback entries"),
	)
