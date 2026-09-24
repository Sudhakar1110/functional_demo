# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

"""Hand-maintained lead pipeline - fully manual records kept by the Sales
Manager, completely separate from the Demo Request / Lead records."""

import frappe
from frappe.model.document import Document
from frappe.utils import format_date


MANUAL_LEAD_STAGES = ["Demo Completed", "Quotation Send", "Paid"]


class ManualLeadTracker(Document):
	pass


def _money(value):
	"""Indian-style grouped amount, e.g. 500000 -> 5,00,000."""
	if value in (None, ""):
		return "-"
	try:
		amount = float(value)
	except (TypeError, ValueError):
		return "-"
	whole = int(amount)
	frac = round(abs(amount - whole) * 100)
	negative = "-" if whole < 0 or amount < 0 else ""
	digits = str(abs(whole))
	if len(digits) > 3:
		head = digits[:-3]
		tail = digits[-3:]
		parts = []
		while len(head) > 2:
			parts.insert(0, head[-2:])
			head = head[:-2]
		if head:
			parts.insert(0, head)
		digits = ",".join(parts) + "," + tail
	result = negative + digits
	if frac:
		result += "." + str(frac).zfill(2)
	return result


def _date(value, fmt="dd MMM yyyy"):
	if not value:
		return "-"
	return format_date(value, fmt)


def manual_leads(stage):
	"""Return the manually maintained leads for a pipeline stage."""
	rows = (
		frappe.get_all(
			"Manual Lead Tracker",
			filters={"stage": stage},
			fields=[
				"name",
				"lead_name",
				"contact_person",
				"contact_number",
				"email",
				"stage",
				"demo_completed_date",
				"interested_module",
				"annual_plan",
				"monthly_plan",
				"quotation_value",
				"quotation_date",
				"paid_amount",
				"paid_date",
				"remarks",
				"creation",
				"modified",
			],
			order_by="modified desc",
			limit_page_length=2000,
			ignore_permissions=True,
		)
		or []
	)
	for row in rows:
		row["modified_display"] = (
			frappe.utils.format_datetime(row.get("modified"), "dd MMM yyyy, hh:mm a")
			if row.get("modified")
			else "-"
		)
		row["demo_date_display"] = _date(row.get("demo_completed_date"))
		row["quotation_date_display"] = _date(row.get("quotation_date"))
		row["paid_date_display"] = _date(row.get("paid_date"))
		row["quotation_value_display"] = _money(row.get("quotation_value"))
		row["paid_amount_display"] = _money(row.get("paid_amount"))
		row["plan_badges"] = []
		if row.get("annual_plan"):
			row["plan_badges"].append("Annual")
		if row.get("monthly_plan"):
			row["plan_badges"].append("Monthly")
	return rows