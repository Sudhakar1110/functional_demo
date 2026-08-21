# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document


class SessionFeedback(Document):
    def validate(self):
        if not self.subject:
            self.subject = _("Feedback for {0}").format(self.demo_session or "")

    def on_update(self):
        # Notify the developer team when new feedback is submitted
        if self.has_value_changed("subject") and not self.developer_response:
            self._notify_developer_team()

    def _notify_developer_team(self):
        """Send notification to all Developer role users."""
        developers = frappe.get_all(
            "Has Role",
            filters={"role": "Developer", "parenttype": "User"},
            fields=["parent"],
        )
        for dev in developers:
            if dev.parent != frappe.session.user:
                frappe.get_doc(
                    {
                        "doctype": "Notification Log",
                        "for_user": dev.parent,
                        "type": "Alert",
                        "subject": _("New Session Feedback: {0}").format(self.subject),
                        "document_type": "Session Feedback",
                        "document_name": self.name,
                    }
                ).insert(ignore_permissions=True)
