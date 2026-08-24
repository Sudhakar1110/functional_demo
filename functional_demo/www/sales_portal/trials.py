# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import portal_context


def get_context(context):
	portal_context(
		context,
		_("Trial Dashboard"),
		["Sales User", "Sales Manager"],
		active="trials",
		subtitle=_("All trial periods - start, end, days remaining and the lead behind each one"),
	)

	today = frappe.utils.today()
	# Show ALL Converted demo requests - including those without trial dates
	# so the sales team can set trial periods for them
	trials = frappe.get_all(
		"Demo Request",
		filters=[
			["status", "=", "Converted"],
		],
		fields=[
			"name", "customer", "lead", "contact_person", "sales_person",
			"interested_module", "trial_start_date", "trial_end_date",
		],
		order_by="trial_end_date asc, creation desc",
		limit_page_length=1000,
	) or []

	# lead names for the table (the request stores the lead id, not its name)
	lead_names = {}
	lead_ids = [t["lead"] for t in trials if t.get("lead")]
	if lead_ids:
		for row in frappe.get_all("Lead", filters={"name": ["in", lead_ids]}, fields=["name", "lead_name"]):
			lead_names[row.name] = row.lead_name or row.name

	active = expired = ending_soon = 0
	for t in trials:
		t["lead_display"] = (
			t.get("customer")
			or (t.get("lead") and lead_names.get(t.get("lead")))
			or t.get("contact_person")
			or "-"
		)
		end = t.get("trial_end_date")
		# date may come back as a date object or string - normalize to a string
		end_str = str(end or "")[:10]
		days = None
		if end_str:
			days = (frappe.utils.date_diff(end_str, today))
		t["days_remaining"] = days
		if days is not None:
			if days < 0:
				expired += 1
			elif days == 0:
				ending_soon += 1  # ends today
			elif days <= 7:
				ending_soon += 1
			else:
				active += 1
		else:
			active += 1
		t["days_label"] = (
			_("Ended {0} days ago").format(-days) if days is not None and days < 0
			else _("Ends today") if days == 0
			else _("{0} days left").format(days) if days is not None
			else "-"
		)

	context.trials = trials
	context.total = len(trials)
	context.active = active
	context.ending_soon = ending_soon
	context.expired = expired
	context.today = today
	return context
