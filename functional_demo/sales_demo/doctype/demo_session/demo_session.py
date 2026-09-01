# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, now_datetime, today

from functional_demo.portal import create_notification, send_branded_email
from functional_demo.sales_demo.doctype.functional_demo_template.functional_demo_template import (
	get_template_snapshot,
)


class DemoSession(Document):
	def validate(self):
		self.fetch_request_details()
		self.validate_consultant()
		self.validate_template_ownership()
		self.validate_schedule()
		self.snapshot_template()
		self.set_timestamps()

	def after_insert(self):
		self.log_request_activity("Demo Scheduled")
		# Every scheduled demo gets a calendar Event - including sessions that
		# were created manually from the desk form (not just via Schedule Demo).
		create_calendar_event(self)
		self.notify_sales_scheduled()

	def on_update(self):
		self.log_session_status_activity()
		self.sync_request_status()

	# ------------------------------------------------------------------
	# validation / auto-fetch
	# ------------------------------------------------------------------

	def fetch_request_details(self):
		"""Server-side fallback for the read-only fields fetched from the Demo Request."""
		if not self.demo_request:
			return
		request = frappe.get_cached_doc("Demo Request", self.demo_request)
		self.lead = self.lead or request.lead
		self.customer = self.customer or request.customer
		self.company = self.company or request.company
		self.contact_person = self.contact_person or request.contact_person
		self.contact_number = self.contact_number or request.contact_number
		self.email = self.email or request.email
		self.sales_person = self.sales_person or request.sales_person
		self.functional_consultant = self.functional_consultant or request.functional_consultant
		self.interested_module = self.interested_module or request.interested_module
		self.demo_type = self.demo_type or request.demo_type
		self.customer_requirements = self.customer_requirements or request.customer_requirements

	def validate_consultant(self):
		if not self.functional_consultant:
			return
		status = frappe.db.get_value("Functional Consultant", self.functional_consultant, "status")
		if status and status != "Active":
			frappe.throw(
				_("Functional Consultant {0} is not active.").format(self.functional_consultant),
				title=_("Consultant Not Active"),
			)

	def validate_template_ownership(self):
		if not self.demo_template:
			return
		owner = frappe.db.get_value(
			"Functional Demo Template", self.demo_template, "functional_consultant"
		)
		if owner and self.functional_consultant and owner != self.functional_consultant:
			frappe.throw(
				_("Demo Template {0} belongs to {1}, not to the assigned consultant {2}.").format(
					self.demo_template, owner, self.functional_consultant
				),
				title=_("Wrong Template"),
			)

	def validate_schedule(self):
		"""Prevent overlapping demos for the same consultant on the same date."""
		if not (self.functional_consultant and self.scheduled_date):
			return
		if self.demo_status not in ("Scheduled", "Rescheduled", "In Progress"):
			return
		conflicts = frappe.db.sql(
			"""
			select name, start_time, end_time
			from `tabDemo Session`
			where functional_consultant = %(consultant)s
				and scheduled_date = %(date)s
				and demo_status not in ('Cancelled', 'Completed', 'Closed')
				and name != %(self)s
			""",
			{
				"consultant": self.functional_consultant,
				"date": self.scheduled_date,
				"self": self.name or "",
			},
			as_dict=True,
		)
		for row in conflicts:
			if times_overlap(self.start_time, self.end_time, row.start_time, row.end_time):
				frappe.throw(
					_("Functional Consultant {0} already has a demo on {1} (Session {2}) at an overlapping time.").format(
						self.functional_consultant, self.scheduled_date, row.name
					),
					title=_("Schedule Conflict"),
				)

	def snapshot_template(self):
		"""Copy the selected template into the session (immutable snapshot).

		The master template may change later - historical sessions keep this copy.
		"""
		old_template = self.db_get("demo_template")
		if not self.demo_template:
			return
		# Auto-fill the agenda from the template so the session form and the
		# execution screen always show it without the consultant retyping it.
		if not self.agenda:
			self.agenda = frappe.db.get_value(
				"Functional Demo Template", self.demo_template, "demo_agenda"
			)
		if old_template != self.demo_template or not self.template_sections:
			self.template_sections = []
			for section in get_template_snapshot(self.demo_template):
				self.append("template_sections", section)
			self.template_snapshot_date = now_datetime()
			self.template_source_modified = frappe.db.get_value(
				"Functional Demo Template", self.demo_template, "modified"
			)

	def set_timestamps(self):
		if self.demo_status == "In Progress" and not self.started_on:
			self.started_on = now_datetime()
		if self.demo_status == "Completed" and not self.completed_on:
			self.completed_on = now_datetime()

	# ------------------------------------------------------------------
	# activity / request sync
	# ------------------------------------------------------------------

	def log_session_status_activity(self):
		# on_update runs AFTER the db write in v15, so the pre-save value
		# must come from get_doc_before_save() (db_get returns the new value)
		before = self.get_doc_before_save()
		old_status = before.get("demo_status") if before else None
		if old_status and old_status != self.demo_status:
			self.log_request_activity(
				"Note",
				remarks="Session {0}: status changed from {1} to {2}".format(
					self.name, old_status, self.demo_status
				),
			)

	def log_request_activity(self, activity_type, remarks=None):
		if not self.demo_request:
			return
		request = frappe.get_cached_doc("Demo Request", self.demo_request)
		request.log_activity(
			activity_type, status=request.status, remarks=remarks or "{0} {1}".format(activity_type, self.name)
		)

	def sync_request_status(self):
		"""Keep the Demo Request workflow in sync with the session status."""
		if self.flags.get("skip_request_sync"):
			return
		# on_update runs AFTER the db write in v15, so the pre-save value
		# must come from get_doc_before_save() (db_get returns the new value)
		before = self.get_doc_before_save()
		old_status = before.get("demo_status") if before else None
		if old_status == self.demo_status or not self.demo_request:
			return

		from functional_demo.sales_demo.doctype.demo_request.demo_request import change_status

		request = frappe.get_doc("Demo Request", self.demo_request)
		try:
			if self.demo_status == "In Progress":
				change_status(request, "Demo In Progress", ignore_permissions=True)
			elif self.demo_status == "Completed":
				target = "Follow-up Required" if self.follow_up_required else "Demo Completed"
				change_status(request, target, ignore_permissions=True)
			elif self.demo_status == "Cancelled":
				other_active = frappe.db.count(
					"Demo Session",
					{
						"demo_request": self.demo_request,
						"demo_status": ["not in", ["Cancelled", "Completed", "Closed"]],
					},
				)
				if other_active == 0:
					try:
						change_status(request, "Cancelled", ignore_permissions=True)
					except Exception:
						# the current user is not allowed to cancel the request (e.g. a
						# consultant cancelling their own session) - keep the request
						# active and notify the sales team
						frappe.log_error(
							title=_("Demo Session -> Demo Request cancel sync failed"),
							message=frappe.get_traceback(),
						)
						self.notify_sales_session_cancelled(request)
		except Exception:
			# never block the session update because the request could not be moved
			frappe.log_error(title=_("Demo Session -> Demo Request status sync failed"), message=frappe.get_traceback())

	def notify_sales_session_cancelled(self, request):
		"""Create a ToDo + timeline note so the sales team reviews a request whose
		session was cancelled by someone without the right to cancel the request
		(typically the consultant). The request itself stays open."""
		if not request or request.sales_person == "Administrator":
			return
		assignee = request.sales_person or frappe.session.user
		subject = _("Demo Session {0} cancelled - Demo Request {1} is still open").format(
			self.name, request.name
		)
		description = _(
			"Demo Session {0} was cancelled by {1}. Demo Request {2} ({3}) is still {4}. "
			"Please review it and reschedule or close it."
		).format(
			self.name,
			frappe.session.user,
			request.name,
			request.customer or request.lead,
			request.status,
		)

		# ToDo for the sales person (standard assignment; skip if one is already open)
		if not frappe.db.exists(
			"ToDo",
			{
				"reference_type": "Demo Request",
				"reference_name": request.name,
				"owner": assignee,
				"status": ["in", ["Open", "Overdue"]],
				"description": ["like", "%{0} cancelled%".format(self.name)],
			},
		):
			todo = frappe.new_doc("ToDo")
			todo.description = description
			todo.reference_type = "Demo Request"
			todo.reference_name = request.name
			todo.role = "Sales User"
			todo.owner = assignee
			todo.insert(ignore_permissions=True)

		# timeline note on the Demo Request
		try:
			communication = frappe.new_doc("Communication")
			communication.communication_type = "Comment"
			communication.communication_medium = "System Generated"
			communication.subject = subject
			communication.content = description
			communication.reference_doctype = "Demo Request"
			communication.reference_name = request.name
			communication.sender = frappe.session.user
			communication.sent_or_received = "Sent"
			communication.insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(title=_("Communication creation failed"), message=frappe.get_traceback())

	def notify_sales_scheduled(self):
		"""Notify both the sales person and the assigned consultant when a demo
		is scheduled (new session or reschedule): an in-app Notification Log
		(everything shows in the portal bell AND the desk bell) plus an email
		with the date / time / meeting link. Fires from after_insert and
		reschedule_demo, so it covers the portal Schedule Demo / reschedule
		actions and sessions created from the desk form. A failure is logged
		but never blocks the scheduling."""
		try:
			if self.demo_status not in ("Scheduled", "Rescheduled"):
				return
			consultant_name = (
				frappe.db.get_value("Functional Consultant", self.functional_consultant, "consultant_name")
				if self.functional_consultant
				else None
			)
			consultant_user = (
				frappe.db.get_value("Functional Consultant", self.functional_consultant, "user")
				if self.functional_consultant
				else None
			)
			party = self.customer or self.lead or self.demo_request
			date_label = (
				frappe.utils.format_date(self.scheduled_date, "medium")
				if self.scheduled_date
				else "-"
			)
			subject = _("Demo Scheduled — {0} on {1}").format(party, date_label)
			session_url = frappe.utils.get_url("/app/demo-session/{0}".format(self.name))
			rows = [
				(_("Date"), date_label),
				(_("Time"), "{0} - {1}".format(self.start_time or "-", self.end_time or "-")),
				(_("Consultant"), consultant_name or "-"),
				(_("Meeting Link"), self.meeting_link or "-"),
				(_("Demo Session"), self.name),
			]

			# sales person: in-app notification + email
			if self.sales_person:
				# in-app notification (portal + desk bells) - created even when the
				# sales person has no email (e.g. Administrator)
				create_notification(
					self.sales_person,
					_("Demo Scheduled — {0} on {1} (Session {2})").format(
						party, date_label, self.name
					),
					"Demo Session",
					self.name,
				)
				email = frappe.db.get_value("User", self.sales_person, "email")
				if email:
					send_branded_email(
						recipients=[email],
						subject=subject,
						heading=_("Demo Scheduled"),
						intro=_("A demo for {0} has been scheduled.").format(party),
						rows=rows,
						cta_text=_("Open Demo Session"),
						cta_url=session_url,
						reference_doctype="Demo Session",
						reference_name=self.name,
					)

			# consultant: in-app notification + email with the same schedule details
			if consultant_user:
				create_notification(
					consultant_user,
					_("Demo Scheduled for You — {0} on {1} (Session {2})").format(
						party, date_label, self.name
					),
					"Demo Session",
					self.name,
				)
				# the linked User's email wins (that is where assignments are
				# delivered); fall back to the consultant profile's email field
				email = (
					frappe.db.get_value("User", consultant_user, "email")
					or (
						frappe.db.get_value("Functional Consultant", self.functional_consultant, "email")
						if self.functional_consultant
						else ""
					)
					or ""
				)
				if email:
					send_branded_email(
						recipients=[email],
						subject=_("Demo Scheduled for You — {0} on {1}").format(party, date_label),
						heading=_("Demo Scheduled"),
						intro=_("A demo for {0} has been scheduled for you.").format(party),
						rows=rows,
						cta_text=_("Open Demo Session"),
						cta_url=session_url,
						reference_doctype="Demo Session",
						reference_name=self.name,
					)
				else:
					# log so a missing address is never silently lost
					frappe.log_error(
						title=_("Consultant email missing - no mail sent for Session {0}").format(self.name),
						message=_(
							"The consultant {0} (user {1}) has no email on their User or consultant profile."
						).format(self.functional_consultant, consultant_user),
					)
		except Exception:
			frappe.log_error(
				title=_("Scheduled email/notification failed for {0}").format(self.name),
				message=frappe.get_traceback(),
			)

	def notify_sales_completed(self):
		"""Email the sales person the demo outcome after the session is completed."""
		try:
			sales_person = self.sales_person
			if not sales_person:
				return
			# in-app notification (portal + desk bells) - created even when the
			# sales person has no email (e.g. Administrator)
			party = self.customer or self.lead or self.demo_request
			create_notification(
				sales_person,
				_("Demo Completed — {0} (Session {1})").format(party, self.name),
				"Demo Session",
				self.name,
			)
			email = frappe.db.get_value("User", sales_person, "email")
			if not email:
				return
			send_branded_email(
				recipients=[email],
				subject=_("Demo Completed — {0}").format(party),
				heading=_("Demo Completed"),
				intro=_("Demo Session {0} for {1} has been completed.").format(self.name, party),
				rows=[
					(_("Interested"), self.interested or "-"),
					(_("Requirements Met"), self.requirements_met or "-"),
					(_("Overall Feedback"), self.overall_feedback or "-"),
					(_("Follow-up Required"), "Yes" if self.follow_up_required else "No"),
					(_("Demo Session"), self.name),
				],
				cta_text=_("Open Demo Session"),
				cta_url=frappe.utils.get_url("/app/demo-session/{0}".format(self.name)),
				reference_doctype="Demo Session",
				reference_name=self.name,
			)
		except Exception:
			frappe.log_error(
				title=_("Completed email to {0} failed for {1}").format(
					self.sales_person or "-", self.name
				),
				message=frappe.get_traceback(),
			)

	def notify_sales_started(self):
		"""In-app notification + email to the sales person when the demo starts."""
		try:
			sales_person = self.sales_person
			if not sales_person:
				return
			party = self.customer or self.lead or self.demo_request
			create_notification(
				sales_person,
				_("Demo Started — {0} (Session {1})").format(party, self.name),
				"Demo Session",
				self.name,
			)
			email = frappe.db.get_value("User", sales_person, "email")
			if not email:
				return
			send_branded_email(
				recipients=[email],
				subject=_("Demo Started — {0}").format(party),
				heading=_("Demo Started"),
				intro=_("Demo Session {0} for {1} has just started.").format(self.name, party),
				rows=[
					(_("Demo Session"), self.name),
					(_("Meeting Link"), self.meeting_link or "-"),
				],
				cta_text=_("Open Demo Session"),
				cta_url=frappe.utils.get_url("/app/demo-session/{0}".format(self.name)),
				reference_doctype="Demo Session",
				reference_name=self.name,
			)
		except Exception:
			frappe.log_error(
				title=_("Started email to {0} failed for {1}").format(
					self.sales_person or "-", self.name
				),
				message=frappe.get_traceback(),
			)

	def notify_sales_cancelled(self, reason=None):
		"""In-app notification + email to the sales person when the demo is cancelled.

		Skips self-notification when the sales person themselves cancelled it."""
		try:
			sales_person = self.sales_person
			if not sales_person or frappe.session.user == sales_person:
				return
			party = self.customer or self.lead or self.demo_request
			create_notification(
				sales_person,
				_("Demo Cancelled — {0} (Session {1})").format(party, self.name),
				"Demo Session",
				self.name,
			)
			email = frappe.db.get_value("User", sales_person, "email")
			if not email:
				return
			send_branded_email(
				recipients=[email],
				subject=_("Demo Cancelled — {0}").format(party),
				heading=_("Demo Cancelled"),
				intro=_("Demo Session {0} for {1} has been cancelled by {2}.").format(
					self.name, party, frappe.utils.get_fullname(frappe.session.user)
				),
				rows=[
					(_("Reason"), reason or "Not provided"),
					(_("Demo Session"), self.name),
				],
				cta_text=_("Open Demo Session"),
				cta_url=frappe.utils.get_url("/app/demo-session/{0}".format(self.name)),
				reference_doctype="Demo Session",
				reference_name=self.name,
			)
		except Exception:
			frappe.log_error(
				title=_("Cancelled email to {0} failed for {1}").format(
					self.sales_person or "-", self.name
				),
				message=frappe.get_traceback(),
			)

	def notify_sales_final_result(self, result):
		"""In-app notification + email to the sales person when the demo is closed
		with a final result (Converted / Not Interested / Closed / Pending)."""
		try:
			sales_person = self.sales_person
			if not sales_person:
				return
			party = self.customer or self.lead or self.demo_request
			create_notification(
				sales_person,
				_("Demo Closed — {0} · Result: {1} (Session {2})").format(party, result, self.name),
				"Demo Session",
				self.name,
			)
			email = frappe.db.get_value("User", sales_person, "email")
			if not email:
				return
			send_branded_email(
				recipients=[email],
				subject=_("Demo Closed — {0} · Result: {1}").format(party, result),
				heading=_("Demo Closed"),
				intro=_("Demo Session {0} for {1} has been closed with the final result '{2}'.").format(
					self.name, party, result
				),
				rows=[
					(_("Final Result"), result),
					(_("Demo Session"), self.name),
				],
				cta_text=_("Open Demo Session"),
				cta_url=frappe.utils.get_url("/app/demo-session/{0}".format(self.name)),
				reference_doctype="Demo Session",
				reference_name=self.name,
			)
		except Exception:
			frappe.log_error(
				title=_("Result email to {0} failed for {1}").format(
					self.sales_person or "-", self.name
				),
				message=frappe.get_traceback(),
			)


# ------------------------------------------------------------------
# demo actions
# ------------------------------------------------------------------

	def _guard_consultant_action(self, allow_cancel=False):
		"""Demo execution actions (start / complete / cancel / final result) are
		functional-team actions. Sales users may only cancel a session that is
		still Scheduled (matching the request workflow, where Sales User can
		cancel before the demo starts); Sales Managers may also cancel an
		in-progress demo. Everyone else must be a functional role."""
		if allow_cancel:
			if can_cancel_session(self):
				return
			frappe.throw(
				_("You do not have permission to cancel this demo."),
				frappe.PermissionError,
			)
		if can_execute_session_action(self):
			return
		frappe.throw(
			_("Only Functional Consultants can perform this action."),
			frappe.PermissionError,
		)

	def start_demo(self):
		self._guard_consultant_action()
		if self.demo_status in ("Completed", "Cancelled", "Closed"):
			frappe.throw(
				_("A {0} demo cannot be started. Please create a new session.").format(
					self.demo_status.lower()
				),
				title=_("Cannot Start"),
			)
		self.demo_status = "In Progress"
		self.save(ignore_permissions=True)
		self.notify_sales_started()

	def complete_demo(self, feedback=None):
		self._guard_consultant_action()
		if self.demo_status != "In Progress":
			frappe.throw(
				_("Please start the demo first (use 'Start Demo'), then complete it."),
				title=_("Demo Not Started"),
			)
		feedback = feedback or {}
		# The consultant must record feedback before the demo can be completed -
		# this is the whole point of the completion step, so an empty submission
		# is rejected even if a stale client skips the UI validation.
		if not str(feedback.get("overall_feedback") or "").strip():
			frappe.throw(
				_("Please enter the overall feedback before completing the demo."),
				title=_("Feedback Required"),
			)

		def _set(fieldname, key=None):
			value = feedback.get(key or fieldname)
			if value not in (None, ""):
				setattr(self, fieldname, value)

		_set("overall_feedback")
		_set("interested")
		_set("requirements_met")
		_set("additional_requirements")
		_set("requested_changes")
		_set("next_action")
		_set("consultant_remarks")
		_set("follow_up_date")
		# Allow the final result to be set directly during completion
		_set("final_result")
		for flag in ("follow_up_required", "additional_demo_required"):
			if flag in feedback and feedback[flag] not in (None, ""):
				setattr(self, flag, 1 if feedback[flag] else 0)

		for item in feedback.get("demo_feedback_items") or []:
			if item.get("description"):
				self.append(
					"demo_feedback_items",
					{
						"item_type": item.get("item_type") or "Question",
						"description": item.get("description"),
					},
				)

		self.demo_status = "Completed"
		self.save(ignore_permissions=True)
		self.add_comment_to_timeline()

		# Create a follow-up only when the consultant checked the Follow-up
		# Required box. The sales team tracks these in the Follow-up Tracker.
		if self.follow_up_required:
			self.create_follow_up(
				self.follow_up_date or add_days(today(), 7),
				self.next_action or "Follow up after demo completion",
				self.sales_person,
			)
		# Apply the final result to the Demo Request when set during completion
		if self.final_result and self.final_result in ("Converted", "Not Interested", "Closed"):
			self._apply_request_final_result(self.final_result)
		self.notify_sales_completed()

	def cancel_demo(self, reason=None):
		self._guard_consultant_action(allow_cancel=True)
		if self.demo_status == "Completed":
			frappe.throw(_("A completed demo cannot be cancelled."), title=_("Cannot Cancel"))
		self.demo_status = "Cancelled"
		if reason:
			self.consultant_remarks = reason
		self.save(ignore_permissions=True)
		self.notify_sales_cancelled(reason)

	def reschedule_demo(self, scheduled_date, start_time=None, end_time=None, meeting_link=None):
		if not scheduled_date:
			frappe.throw(_("Please select a new date."))
		# capture the current schedule before overwriting
		old_date = self.scheduled_date
		old_start = self.start_time
		old_end = self.end_time
		self.scheduled_date = scheduled_date
		self.start_time = start_time
		self.end_time = end_time
		self.meeting_link = meeting_link or self.meeting_link
		self.reschedule_count = int(self.reschedule_count or 0) + 1
		# record the reschedule in the child table
		self.append("reschedule_history", {
			"reschedule_number": self.reschedule_count,
			"old_date": old_date,
			"old_start_time": old_start,
			"old_end_time": old_end,
			"new_date": scheduled_date,
			"new_start_time": start_time,
			"new_end_time": end_time,
			"rescheduled_by": frappe.session.user,
			"rescheduled_on": frappe.utils.now_datetime(),
		})
		# mark the session as Rescheduled so it is clearly distinguishable from
		# a first-time schedule (it is still an active, startable session)
		self.demo_status = "Rescheduled"
		self.save(ignore_permissions=True)
		self.log_request_activity(
			"Demo Rescheduled", remarks="Session {0} rescheduled to {1}".format(self.name, scheduled_date)
		)
		create_calendar_event(self)
		self.notify_sales_scheduled()
		self.notify_managers_rescheduled()
		# Auto-create a follow-up so the session appears on the Follow-ups
		# page for the sales team to track.
		fu = self.create_follow_up(
			scheduled_date,
			_("Follow up after demo reschedule to {0}").format(scheduled_date),
			self.sales_person,
		)
		self.notify_sales_reschedule_follow_up(fu, scheduled_date)

	def notify_sales_reschedule_follow_up(self, fu, new_date):
		"""Notify the sales person that a follow-up was created because the
		demo was rescheduled — distinct from the generic follow-up notification
		so the sales team immediately understands why a follow-up appeared."""
		try:
			sales_person = self.sales_person or self.assigned_to
			if not sales_person:
				return
			party = self.customer or self.lead or self.demo_request or self.name
			date_label = (
				frappe.utils.format_date(new_date, "medium")
				if new_date
				else "-"
			)
			subject = _("Follow-up Created — Demo Rescheduled to {0} ({1})").format(
				date_label, party
			)
			# in-app notification (portal + desk bells)
			create_notification(
				sales_person,
				subject,
				"Demo Follow Up",
				fu.name if fu else self.name,
			)
			# email
			email = frappe.db.get_value("User", sales_person, "email")
			if not email:
				return
			consultant_name = (
				frappe.db.get_value(
					"Functional Consultant", self.functional_consultant, "consultant_name"
				)
				if self.functional_consultant
				else "-"
			)
			send_branded_email(
				recipients=[email],
				subject=subject,
				heading=_("Follow-up Created — Reschedule"),
				intro=_(
					"Demo Session {0} for {1} was rescheduled to {2}. "
					"A follow-up has been created so you can track the next steps."
				).format(self.name, party, date_label),
				rows=[
					(_("New Date"), date_label),
					(_("Time"), "{0} \u2013 {1}".format(self.start_time or "-", self.end_time or "-")),
					(_("Consultant"), consultant_name),
					(_("Follow-up"), fu.name if fu else "-"),
					(_("Demo Session"), self.name),
				],
				cta_text=_("Open Follow-up"),
				cta_url=frappe.utils.get_url("/app/demo-follow-up/{0}".format(fu.name)) if fu else "",
				reference_doctype="Demo Follow Up",
				reference_name=fu.name if fu else self.name,
			)
		except Exception:
			frappe.log_error(
				title=_("Reschedule follow-up notification to {0} failed for {1}").format(
					self.sales_person or "-", self.name
				),
				message=frappe.get_traceback(),
			)

	def notify_managers_rescheduled(self):
		"""Notify Functional Team Managers, Sales Managers, and the assigned
		Sales Person (in-app + email) when a demo is rescheduled."""
		try:
			party = self.customer or self.lead or self.demo_request
			date_label = (
				frappe.utils.format_date(self.scheduled_date, "medium")
				if self.scheduled_date
				else "-"
			)
			consultant_name = (
				frappe.db.get_value("Functional Consultant", self.functional_consultant, "consultant_name")
				if self.functional_consultant
				else "-"
			)
			session_url = frappe.utils.get_url("/app/demo-session/{0}".format(self.name))
			rows = [
				(_("Customer"), party or "-"),
				(_("New Date"), date_label),
				(_("Time"), "{0} - {1}".format(self.start_time or "-", self.end_time or "-")),
				(_("Consultant"), consultant_name),
				(_("Meeting Link"), self.meeting_link or "-"),
				(_("Reschedule #"), str(self.reschedule_count or 1)),
				(_("Demo Session"), self.name),
			]

			# Collect unique recipients: managers + sales person
			recipients = set()

			# Functional Team Managers
			ft_managers = frappe.get_all(
				"User",
				filters=[
					["Has Role", "role", "=", "Functional Team Manager"],
					["User", "enabled", "=", 1],
				],
				fields=["name"],
			)
			for m in ft_managers:
				recipients.add(m.name)

			# Sales Managers
			sales_managers = frappe.get_all(
				"User",
				filters=[
					["Has Role", "role", "=", "Sales Manager"],
					["User", "enabled", "=", 1],
				],
				fields=["name"],
			)
			for m in sales_managers:
				recipients.add(m.name)

			# Assigned Sales Person (also notified by notify_sales_scheduled,
			# but include here so managers see the same recipient list)
			if self.sales_person:
				recipients.add(self.sales_person)

			for user in recipients:
				# in-app notification
				create_notification(
					user,
					_("Demo Rescheduled — {0} to {1} (Session {2})").format(
						party, date_label, self.name
					),
					"Demo Session",
					self.name,
				)
				# email
				try:
					email = frappe.db.get_value("User", user, "email")
					if not email:
						continue
					send_branded_email(
						recipients=[email],
						subject=_("Demo Rescheduled: {0} to {1}").format(party, date_label),
						heading=_("Demo Rescheduled"),
						intro=_(
							"Demo Session {0} for {1} has been rescheduled to {2}."
						).format(self.name, party, date_label),
						rows=rows,
						cta_text=_("Open Demo Session"),
						cta_url=session_url,
						reference_doctype="Demo Session",
						reference_name=self.name,
					)
				except Exception:
					frappe.log_error(
						title=_("Reschedule notification email failed for {0}").format(user),
						message=frappe.get_traceback(),
					)
		except Exception:
			frappe.log_error(
				title=_("Reschedule notification failed for {0}").format(self.name),
				message=frappe.get_traceback(),
			)

	def create_follow_up(self, follow_up_date, next_action=None, assigned_to=None):
		"""Create a Demo Follow Up + ToDo, and move the Demo Request to Follow-up Required."""
		if not follow_up_date:
			follow_up_date = add_days(today(), 7)

		# Idempotency: don't create a duplicate if one already exists for this session
		existing = frappe.db.get_value("Demo Follow Up", {"demo_session": self.name}, "name")
		if existing:
			return frappe.get_doc("Demo Follow Up", existing)

		fu = frappe.new_doc("Demo Follow Up")
		fu.demo_session = self.name
		fu.demo_request = self.demo_request
		fu.customer = self.customer
		fu.sales_person = self.sales_person
		fu.functional_consultant = self.functional_consultant
		fu.follow_up_date = follow_up_date
		fu.next_action = next_action
		fu.assigned_to = assigned_to or self.sales_person or frappe.session.user
		# DemoFollowUp.after_insert -> assign_todo creates the ToDo for the assignee
		fu.insert(ignore_permissions=True)

		# keep the Demo Request in sync
		request = frappe.get_doc("Demo Request", self.demo_request)
		request.follow_up_date = follow_up_date
		request.next_action = next_action
		request.save(ignore_permissions=True)
		from functional_demo.sales_demo.doctype.demo_request.demo_request import change_status

		try:
			change_status(request, "Follow-up Required", ignore_permissions=True)
		except Exception:
			# The request transition to "Follow-up Required" is role-gated in the
			# workflow (like Converted / Not Interested / Closed), so a consultant
			# or manager creating the follow-up may be blocked even though the
			# follow-up itself was created. Apply the state directly (status +
			# workflow_state, exactly what the workflow would write) and log -
			# never fail the action or roll back the follow-up.
			frappe.log_error(
				title=_("Demo Request {0} could not be moved to 'Follow-up Required' from session {1}").format(
					request.name, self.name
				),
				message=frappe.get_traceback(),
			)
			frappe.db.set_value(
				"Demo Request",
				request.name,
				{"status": "Follow-up Required", "workflow_state": "Follow-up Required"},
			)
		return fu

	def set_final_result(self, result):
		self._guard_consultant_action()
		allowed = ("Pending", "Converted", "Not Interested", "Closed")
		if result not in allowed:
			frappe.throw(_("Invalid result. Choose from {0}.").format(", ".join(allowed)))
		self.final_result = result
		self.demo_status = "Closed"
		self.save(ignore_permissions=True)
		self.notify_sales_final_result(result)
		if result in ("Converted", "Not Interested", "Closed"):
			self._apply_request_final_result(result)

	def _apply_request_final_result(self, result):
		"""Move the Demo Request to the matching final state without letting the
		caller's role block the session's result.

		The session's final result is the source of truth, but the request
		transitions (Converted / Not Interested / Closed) are gated to Sales
		roles in the workflow while this action runs from the consultant's
		Conduct Demo page - so try the normal workflow first and fall back to
		applying the state directly (status + workflow_state, exactly what the
		workflow would write) when the save is blocked. The failure is logged
		and the sales team is notified so nothing is silently lost."""
		from functional_demo.sales_demo.doctype.demo_request.demo_request import change_status

		request = frappe.get_doc("Demo Request", self.demo_request)
		try:
			change_status(request, result, ignore_permissions=True)
			return
		except Exception:
			# never fail the result - the session is already Closed and the
			# request transition may simply not be allowed for this role
			frappe.log_error(
				title=_("Demo Request {0} could not be moved to '{1}' from session {2}").format(
					request.name, result, self.name
				),
				message=frappe.get_traceback(),
			)

		# Direct fallback: the request transition is role-gated to Sales, so
		# apply the final state the same way the workflow itself would.
		frappe.db.set_value(
			"Demo Request", request.name, {"status": result, "workflow_state": result}
		)

		if result == "Converted":
			try:
				# on_update (create_opportunity_on_conversion) is skipped when the
				# state is applied directly - run it explicitly; it is idempotent.
				frappe.get_doc("Demo Request", request.name).create_opportunity_on_conversion()
			except Exception:
				frappe.log_error(
					title=_("Opportunity creation failed for converted demo {0}").format(request.name),
					message=frappe.get_traceback(),
				)

		# Let the sales team know the request was updated directly (no workflow
		# audit trail) so they can review it.
		sales_person = request.sales_person
		if sales_person and sales_person != "Administrator":
			create_notification(
				sales_person,
				_("Demo Closed — Result: {0} · Demo Request {1} Updated (Session {2})").format(
					result, request.name, self.name
				),
				"Demo Session",
				self.name,
			)

	def add_comment_to_timeline(self):
		"""Add a Communication entry so the demo completion shows on the timeline."""
		try:
			communication = frappe.new_doc("Communication")
			communication.communication_type = "Comment"
			communication.communication_medium = "System Generated"
			communication.subject = _("Demo Completed: {0}").format(self.name)
			communication.content = _(
				"Demo {0} completed for {1}. Interested: {2}, Requirements met: {3}, Follow-up required: {4}"
			).format(
				self.name,
				self.customer or self.demo_request,
				self.interested or "-",
				self.requirements_met or "-",
				"Yes" if self.follow_up_required else "No",
			)
			communication.reference_doctype = "Demo Session"
			communication.reference_name = self.name
			communication.sender = frappe.session.user
			communication.sent_or_received = "Sent"
			communication.insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(title=_("Communication creation failed"), message=frappe.get_traceback())


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def can_execute_session_action(session, user=None):
	"""True when the user may run consultant actions (start / complete / final
	result) on a Demo Session. Only the assigned functional consultant and
	site admins may execute - managers and other consultants see it read-only."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	# Only the assigned consultant may execute demo actions
	if session.functional_consultant:
		consultant_user = frappe.db.get_value(
			"Functional Consultant", session.functional_consultant, "user"
		)
		if consultant_user and user == consultant_user:
			return True
	return False


def can_cancel_session(session, user=None):
	"""True when the user may cancel a Demo Session: only the assigned
	consultant, Sales Managers, and site admins. A plain Sales User may
	only cancel while the session is still Scheduled."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	if "Sales Manager" in roles:
		return True
	# Only the assigned consultant may cancel
	if session.functional_consultant:
		consultant_user = frappe.db.get_value(
			"Functional Consultant", session.functional_consultant, "user"
		)
		if consultant_user and user == consultant_user:
			return True
	return "Sales User" in roles and session.demo_status == "Scheduled"


def times_overlap(start1, end1, start2, end2):
	"""Return True if two HH:MM:SS time ranges overlap (missing end = same time)."""
	s1 = _to_seconds(start1)
	s2 = _to_seconds(start2)
	if s1 is None or s2 is None:
		return False
	e1 = _to_seconds(end1) if end1 else s1
	e2 = _to_seconds(end2) if end2 else s2
	return s1 < e2 and s2 < e1


def _to_seconds(value):
	if value in (None, ""):
		return None
	try:
		parts = str(value).split(":")
		secs = int(float(parts[0])) * 3600 + int(float(parts[1])) * 60 + int(float(parts[2] or 0))
		return secs
	except Exception:
		return None


def create_calendar_event(session):
	"""Create (or update) the ERPNext Event (calendar) for a scheduled demo.

	Upserts on the existing Event for the session so re-scheduling and the
	after_insert hook can never create duplicate calendar entries."""
	if not session or not session.scheduled_date:
		return
	try:
		start = frappe.utils.get_datetime(
			"{0} {1}".format(session.scheduled_date, session.start_time or "10:00:00")
		)
		subject = _("Demo: {0} ({1})").format(session.customer or session.demo_request, session.name)

		existing = frappe.db.get_value(
			"Event",
			{"reference_type": "Demo Session", "reference_name": session.name},
			"name",
		)
		if existing:
			event = frappe.get_doc("Event", existing)
			event.subject = subject
			event.starts_on = start
			event.ends_on = (
				frappe.utils.get_datetime("{0} {1}".format(session.scheduled_date, session.end_time))
				if session.end_time
				else None
			)
			event.save(ignore_permissions=True)
			return

		event = frappe.new_doc("Event")
		event.subject = subject
		event.starts_on = start
		if session.end_time:
			event.ends_on = frappe.utils.get_datetime(
				"{0} {1}".format(session.scheduled_date, session.end_time)
			)
		event.event_type = "Private"
		event.status = "Open"
		event.reference_type = "Demo Session"
		event.reference_name = session.name
		event.insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title=_("Demo calendar event creation failed"), message=frappe.get_traceback())


# ------------------------------------------------------------------
# reminders (daily scheduled job)
# ------------------------------------------------------------------

def send_demo_reminders():
	"""Daily job: remind the consultant and the sales person (in-app
	notification + email) about every demo scheduled for tomorrow.

	Idempotent: a session is only reminded once per target date, tracked in
	Demo Session.last_reminder_date - rescheduling to a different day triggers
	a fresh reminder for the new date, and re-runs of the same job never
	double-send. (The previous subject-text match was brittle: it could
	suppress a reminder when a 'demo scheduled' email happened to mention the
	same date.)"""
	if not frappe.db.exists("DocType", "Demo Session"):
		return
	tomorrow = frappe.utils.add_days(frappe.utils.today(), 1)
	sessions = frappe.get_all(
		"Demo Session",
		filters={
			"demo_status": ["in", ["Scheduled", "Rescheduled"]],
			"scheduled_date": tomorrow,
		},
		fields=[
			"name", "customer", "lead", "demo_request", "sales_person",
			"functional_consultant", "start_time", "end_time", "meeting_link",
			"last_reminder_date",
		],
		limit_page_length=500,
	) or []
	sent = 0
	for row in sessions:
		# date fields come back as date objects on some drivers and as strings
		# on others - normalize before comparing
		if str(row.get("last_reminder_date") or "")[:10] == str(tomorrow)[:10]:
			continue
		sent += _send_session_reminder(row, tomorrow)
	if sent:
		frappe.db.commit()


def _send_session_reminder(row, tomorrow):
	"""Send the day-before reminder for one session to both the sales person
	and the consultant; returns how many notifications were created."""
	party = row.customer or row.lead or row.demo_request or row.name
	subject = _("Reminder: Demo Tomorrow — {0} ({1}) (Session {2})").format(
		party, tomorrow, row.name
	)
	recipients = [row.sales_person]
	consultant_user = (
		frappe.db.get_value("Functional Consultant", row.functional_consultant, "user")
		if row.functional_consultant
		else None
	)
	if consultant_user:
		recipients.append(consultant_user)

	sent = 0
	for user in {r for r in recipients if r and r != "Guest"}:
		create_notification(user, subject, "Demo Session", row.name)
		sent += 1
		email = frappe.db.get_value("User", user, "email")
		if not email:
			continue
		try:
			send_branded_email(
				recipients=[email],
				subject=subject,
				heading=_("Demo Reminder"),
				intro=_("This is a reminder that Demo Session {0} for {1} is scheduled for tomorrow ({2}).").format(
					row.name, party, tomorrow
				),
				rows=[
					(_("Time"), "{0} - {1}".format(row.start_time or "-", row.end_time or "-")),
					(_("Meeting Link"), row.meeting_link or "-"),
					(_("Demo Session"), row.name),
				],
				cta_text=_("Open Demo Session"),
				cta_url=frappe.utils.get_url("/app/demo-session/{0}".format(row.name)),
				reference_doctype="Demo Session",
				reference_name=row.name,
			)
		except Exception:
			frappe.log_error(
				title=_("Reminder email to {0} failed for {1}").format(user, row.name),
				message=frappe.get_traceback(),
			)
	# remember the target date so the next run of the daily job skips this
	# session (dedupe is per session-day, not per user)
	frappe.db.set_value("Demo Session", row.name, "last_reminder_date", tomorrow)
	return sent


def send_demo_hour_reminders():
	"""Frequent job (runs on the 'all' scheduler tick): remind the consultant
	and the sales person (in-app notification + email) about every demo that
	starts within the next hour.

	Idempotent: each session is reminded once per scheduled slot, tracked in
	Demo Session.last_hour_reminder (the scheduled start datetime).
	Rescheduling to a different slot triggers a fresh reminder for the new
	slot; re-runs of the job never double-send."""
	if not frappe.db.exists("DocType", "Demo Session"):
		return
	now = now_datetime()
	window_end = frappe.utils.add_to_date(now, hours=1)
	today = frappe.utils.today()
	sessions = frappe.get_all(
		"Demo Session",
		filters={
			"demo_status": ["in", ["Scheduled", "Rescheduled"]],
			"scheduled_date": today,
		},
		fields=[
			"name", "customer", "lead", "demo_request", "sales_person",
			"functional_consultant", "start_time", "end_time", "meeting_link",
			"last_hour_reminder",
		],
		limit_page_length=500,
	) or []
	sent = 0
	for row in sessions:
		if not row.get("start_time"):
			continue
		start = frappe.utils.get_datetime(
			"{0} {1}".format(today, str(row.get("start_time"))[:5])
		)
		# only demos starting within the next hour (not already started)
		if not (now <= start <= window_end):
			continue
		# dedupe per scheduled slot: normalize datetimes before comparing
		if str(row.get("last_hour_reminder") or "")[:16] == str(start)[:16]:
			continue
		sent += _send_hour_reminder(row, start)
	if sent:
		frappe.db.commit()


def _send_hour_reminder(row, start):
	"""Send the 1-hour-before reminder for one session to both the sales person
	and the consultant; returns how many notifications were created."""
	party = row.customer or row.lead or row.demo_request or row.name
	subject = _("Demo Starting Soon — {0} at {1} (Session {2})").format(
		party, start.strftime("%H:%M"), row.name
	)
	recipients = [row.sales_person]
	consultant_user = (
		frappe.db.get_value("Functional Consultant", row.functional_consultant, "user")
		if row.functional_consultant
		else None
	)
	if consultant_user:
		recipients.append(consultant_user)

	sent = 0
	for user in {r for r in recipients if r and r != "Guest"}:
		create_notification(user, subject, "Demo Session", row.name)
		sent += 1
		email = frappe.db.get_value("User", user, "email")
		if not email:
			continue
		try:
			send_branded_email(
				recipients=[email],
				subject=subject,
				heading=_("Demo Starting Soon"),
				intro=_("Demo Session {0} for {1} starts in about an hour.").format(row.name, party),
				rows=[
					(_("Starts At"), start.strftime("%H:%M")),
					(_("Time"), "{0} - {1}".format(row.start_time or "-", row.end_time or "-")),
					(_("Meeting Link"), row.meeting_link or "-"),
					(_("Demo Session"), row.name),
				],
				cta_text=_("Open Demo Session"),
				cta_url=frappe.utils.get_url("/app/demo-session/{0}".format(row.name)),
				reference_doctype="Demo Session",
				reference_name=row.name,
			)
		except Exception:
			frappe.log_error(
				title=_("Hour reminder email to {0} failed for {1}").format(user, row.name),
				message=frappe.get_traceback(),
			)
	# remember the slot so the next run of the job skips this session
	frappe.db.set_value("Demo Session", row.name, "last_hour_reminder", start)
	return sent


# ------------------------------------------------------------------
# permission filters
# ------------------------------------------------------------------

def get_permission_query_conditions(user=None):
	"""Consultants see only their own sessions; sales users see sessions of their
	requests; managers see everything. The read-only Feedback Viewer role is NOT
	bypassed here - Feedback reads sessions directly with ignore_permissions."""
	user = user or frappe.session.user
	if not user or user == "Administrator":
		return ""
	roles = frappe.get_roles(user)
	# Managers still see everything; the read-only Feedback Viewer role must NOT
	# bypass the list filter (it only needs Feedback, which reads sessions
	# directly with ignore_permissions). A consultant who also carries the
	# Feedback Viewer role must still see only their own sessions.
	if any(r in roles for r in ("System Manager", "Sales Manager", "Functional Team Manager")):
		return ""
	if "Functional Consultant" in roles:
		return (
			"(`tabDemo Session`.`functional_consultant` in "
			"(select `tabFunctional Consultant`.`name` from `tabFunctional Consultant` "
			"where `tabFunctional Consultant`.`user` = {0}))"
		).format(frappe.db.escape(user))
	if "Sales User" in roles:
		return (
			"(`tabDemo Session`.`demo_request` in "
			"(select `tabDemo Request`.`name` from `tabDemo Request` "
			"where `tabDemo Request`.`sales_person` = {0} or `tabDemo Request`.`owner` = {0}))"
		).format(frappe.db.escape(user))
	return ""


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	if any(r in roles for r in ("System Manager", "Sales Manager", "Functional Team Manager")):
		return True
	if "Feedback Viewer" in roles or "Developer" in roles:
		# The feedback-only roles (standard 'Developer' / legacy 'Feedback
		# Viewer') are read-only: they can open session details (from Demo
		# Feedback) but never start/complete/cancel a demo.
		return ptype == "read"
	if "Functional Consultant" in roles:
		if doc.get("functional_consultant"):
			consultant_user = frappe.db.get_value(
				"Functional Consultant", doc.get("functional_consultant"), "user"
			)
			return consultant_user == user
		return False
	if "Sales User" in roles and doc.get("demo_request"):
		request = frappe.db.get_value(
			"Demo Request", doc.get("demo_request"), ["sales_person", "owner"], as_dict=True
		)
		if request:
			return request.sales_person == user or request.owner == user
		return False
	return False
