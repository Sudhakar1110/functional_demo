# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

from frappe.model.document import Document


class PortalChatMessage(Document):
	"""Group chat messages between all portal users (sales / functional / developers).

	The controller class is REQUIRED: Frappe's migrate deletes any doctype
	whose controller module has no matching class (get_controller raises
	ImportError -> treated as an orphaned doctype).

	This is a shared group chat, so every portal role reads every message
	(doctype permissions) and no row-level filter applies."""
	pass
