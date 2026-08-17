# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

from frappe.model.document import Document


class WebPushSubscription(Document):
	"""A browser's Web Push subscription for one user.

	Created through the whitelisted subscribe_push API (always scoped to the
	logged-in user) and used by create_notification to send OS-level popups
	with sound even when the user is on another page entirely.
	"""
	pass
