# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

"""Hand-maintained lead pipeline - fully manual records kept by the Sales
Manager, completely separate from the Demo Request / Lead records."""

import frappe
from frappe.model.document import Document


MANUAL_LEAD_STAGES = ["Demo Completed", "Quotation Send", "Paid"]


class ManualLeadTracker(Document):
	pass


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
				"quotation_no",
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
	return rows