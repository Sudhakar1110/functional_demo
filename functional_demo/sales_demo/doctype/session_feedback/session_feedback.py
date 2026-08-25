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

        # Notify the manager when a developer responds
        if self.has_value_changed("developer_response") and self.developer_response:
            self._notify_manager_of_response()

    def _notify_developer_team(self):
        """Send notification to all Developer role users."""
        developers = frappe.get_all(
            "Has Role",
            filters={"role": "Developer", "parenttype": "User"},
            fields=["parent"],
        )
        for dev in developers:
            if dev.parent != frappe.session.user:
                self._send_notification(
                    dev.parent,
                    _("New Session Feedback: {0}").format(self.subject),
                )

    def _notify_manager_of_response(self):
        """Notify the person who submitted the feedback when a developer responds."""
        # Notify the owner (person who created the feedback)
        if self.owner and self.owner != frappe.session.user:
            self._send_notification(
                self.owner,
                _("Developer responded to your feedback: {0}").format(self.subject),
            )

        # Also notify Sales Manager and Functional Team Manager roles
        managers = frappe.get_all(
            "Has Role",
            filters={"role": ["in", ["Sales Manager", "Functional Team Manager"]], "parenttype": "User"},
            fields=["parent"],
            distinct=True,
        )
        for mgr in managers:
            if mgr.parent != frappe.session.user and mgr.parent != self.owner:
                self._send_notification(
                    mgr.parent,
                    _("Developer responded to feedback: {0}").format(self.subject),
                )

    def _send_notification(self, user, subject):
        """Create an in-app notification and send email for the given user."""
        # In-app notification (Notification Log)
        try:
            frappe.get_doc(
                {
                    "doctype": "Notification Log",
                    "for_user": user,
                    "type": "Alert",
                    "subject": subject,
                    "document_type": "Session Feedback",
                    "document_name": self.name,
                }
            ).insert(ignore_permissions=True)
        except Exception:
            frappe.log_error(
                title=_("Notification Log creation failed for {0}").format(user),
                message=frappe.get_traceback(),
            )

        # Realtime push (portal bell refresh)
        try:
            frappe.publish_realtime(
                "demo_portal_notification",
                {
                    "subject": subject,
                    "document_type": "Session Feedback",
                    "document_name": self.name,
                },
                user=user,
                after_commit=True,
            )
        except Exception:
            pass

        # Email notification
        try:
            from functional_demo.portal import is_mail_notifications_enabled, send_branded_email

            if not is_mail_notifications_enabled(user):
                return
            user_doc = frappe.get_doc("User", user)
            email = user_doc.email
            if not email:
                return
            session_link = frappe.utils.get_url(
                "/session_feedback"
            )
            send_branded_email(
                recipients=[email],
                subject=subject,
                heading=subject,
                intro=_("A developer has responded to the session feedback submitted for <strong>{0}</strong>."),
                rows=[
                    (_("Session"), self.demo_session or "-"),
                    (_("Customer"), self.customer or "-"),
                    (_("Feedback Type"), self.feedback_type or "-"),
                    (_("Priority"), self.priority or "-"),
                    (_("Subject"), self.subject or "-"),
                    (_("Developer Response"), self.developer_response or "-"),
                    (_("Status"), self.status or "-"),
                ],
                cta_text="View Feedback",
                cta_url=session_link,
                reference_doctype="Session Feedback",
                reference_name=self.name,
            )
        except Exception:
            frappe.log_error(
                title=_("Email notification failed for {0}").format(user),
                message=frappe.get_traceback(),
            )
