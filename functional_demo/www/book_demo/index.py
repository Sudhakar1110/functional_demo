# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Public, login-free demo booking page (/book_demo).

Customers pick a module, an available consultant, a date and a free time slot
and submit their details. A Demo Request is created in the normal workflow
(Requested -> manager approval) so the sales team can confirm the slot.
"""

import frappe
from frappe import _

MODULES = [
	"Law Management", "Hospitality", "Medical Store", "Retail & Supermarket",
	"Manufacturing", "Education", "Healthcare", "Real Estate", "Logistics & Transport",
	"Agriculture", "IT Services", "Banking & Finance", "Food & Beverage",
	"Construction", "Energy & Utilities", "Other",
]
SLOTS = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]


def get_context(context):
	context.no_cache = 1
	context.title = _("Book a Demo")
	context.subtitle = _("Pick a module, consultant and time slot - our team confirms right back.")
	context.modules = MODULES
	context.slots = SLOTS
	# Filtered in Python: an unset status is stored as NULL and any SQL status
	# filter would silently hide those consultants. Only explicit 'Inactive'
	# records are excluded.
	_consultants = frappe.get_all(
		"Functional Consultant",
		fields=["name", "consultant_name", "specialization", "availability", "status"],
		order_by="consultant_name asc",
	) or []
	context.consultants = [c for c in _consultants if (c.get("status") or "") != "Inactive"]
	context.today = frappe.utils.today()
	return context
