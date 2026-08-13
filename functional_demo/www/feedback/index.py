# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

from frappe import _

from functional_demo.api import get_demo_feedback_data
from functional_demo.portal import portal_context


def get_context(context):
	portal_context(
		context,
		_("Demo Feedback"),
		["Sales User", "Sales Manager", "Functional Consultant", "Functional Team Manager"],
		active="feedback",
		subtitle=_("Feedback recorded against the demos"),
	)
	context.feedback = get_demo_feedback_data()
	context.total_feedback = len(context.feedback)
