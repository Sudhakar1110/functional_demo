# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

from frappe import _

from functional_demo.api import get_template_feedback_data
from functional_demo.portal import portal_context


def get_context(context):
	portal_context(
		context,
		_("Template Feedback"),
		["Sales User", "Sales Manager", "Functional Consultant", "Functional Team Manager"],
		active="feedback",
		subtitle=_("Demo templates and the feedback recorded against them"),
	)
	context.templates = get_template_feedback_data()
	context.total_templates = len(context.templates)
	context.total_feedback = sum(t.get("feedback_count") or 0 for t in context.templates)
