# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, now_datetime, today

from functional_demo.portal import create_notification
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
		if self.demo_status not in ("Scheduled", "In Progress"):
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
			if self.demo_status != "Scheduled":
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
			subject = _("Demo scheduled: {0} on {1}").format(party, self.scheduled_date)
			message = _(
				"Hi,\n\n"
				"Demo Session {0} for {1} has been scheduled.\n\n"
				"Date: {2}\n"
				"Time: {3} - {4}\n"
				"Consultant: {5}\n"
				"Meeting link: {6}\n\n"
				"Open the session: {7}\n"
			).format(
				self.name,
				party,
				self.scheduled_date,
				self.start_time or "-",
				self.end_time or "-",
				consultant_name or "-",
				self.meeting_link or "-",
				frappe.utils.get_url("/app/demo-session/{0}".format(self.name)),
			)

			# sales person: in-app notification + email
			if self.sales_person:
				# in-app notification (portal + desk bells) - created even when the
				# sales person has no email (e.g. Administrator)
				create_notification(
					self.sales_person,
					_("Demo scheduled: {0} on {1} (Session {2})").format(
						party, self.scheduled_date, self.name
					),
					"Demo Session",
					self.name,
				)
				email = frappe.db.get_value("User", self.sales_person, "email")
				if email:
					frappe.sendmail(
						recipients=[email],
						subject=subject,
						message=message,
						reference_doctype="Demo Session",
						reference_name=self.name,
						now=True,
					)

			# consultant: in-app notification + email with the same schedule details
			if consultant_user:
				create_notification(
					consultant_user,
					_("Demo scheduled for you: {0} on {1} (Session {2})").format(
						party, self.scheduled_date, self.name
					),
					"Demo Session",
					self.name,
				)
				email = frappe.db.get_value("User", consultant_user, "email")
				if email:
					frappe.sendmail(
						recipients=[email],
						subject=_("Demo scheduled for you: {0} on {1}").format(party, self.scheduled_date),
						message=message,
						reference_doctype="Demo Session",
						reference_name=self.name,
						now=True,
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
			create_notification(
				sales_person,
				_("Demo completed: {0} ({1})").format(
					self.customer or self.lead or self.demo_request, self.name
				),
				"Demo Session",
				self.name,
			)
			email = frappe.db.get_value("User", sales_person, "email")
			if not email:
				return
			subject = _("Demo completed: {0} ({1})").format(
				self.customer or self.lead or self.demo_request, self.name
			)
			message = _(
				"Hi,\n\n"
				"Demo Session {0} for {1} has been completed.\n\n"
				"Interested: {2}\n"
				"Requirements met: {3}\n"
				"Overall feedback: {4}\n"
				"Follow-up required: {5}\n\n"
				"Open the session: {6}\n"
			).format(
				self.name,
				self.customer or self.lead or self.demo_request,
				self.interested or "-",
				self.requirements_met or "-",
				self.overall_feedback or "-",
				"Yes" if self.follow_up_required else "No",
				frappe.utils.get_url("/app/demo-session/{0}".format(self.name)),
			)
			frappe.sendmail(
				recipients=[email],
				subject=subject,
				message=message,
				reference_doctype="Demo Session",
				reference_name=self.name,
				now=True,
			)
		except Exception:
			frappe.log_error(
				title=_("Completed email to {0} failed for {1}").format(
					self.sales_person or "-", self.name
				),
				message=frappe.get_traceback(),
			)


# ------------------------------------------------------------------
# demo actions
# ------------------------------------------------------------------

	def start_demo(self):
		if self.demo_status in ("Completed", "Cancelled", "Closed"):
			frappe.throw(
				_("A {0} demo cannot be started. Please create a new session.").format(
					self.demo_status.lower()
				),
				title=_("Cannot Start"),
			)
		self.demo_status = "In Progress"
		self.save(ignore_permissions=True)

	def complete_demo(self, feedback=None):
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

		if self.follow_up_required:
			self.create_follow_up(
				self.follow_up_date or add_days(today(), 7), self.next_action, self.sales_person
			)
		self.notify_sales_completed()

	def cancel_demo(self, reason=None):
		if self.demo_status == "Completed":
			frappe.throw(_("A completed demo cannot be cancelled."), title=_("Cannot Cancel"))
		self.demo_status = "Cancelled"
		if reason:
			self.consultant_remarks = reason
		self.save(ignore_permissions=True)

	def reschedule_demo(self, scheduled_date, start_time=None, end_time=None, meeting_link=None):
		if not scheduled_date:
			frappe.throw(_("Please select a new date."))
		self.scheduled_date = scheduled_date
		self.start_time = start_time
		self.end_time = end_time
		self.meeting_link = meeting_link or self.meeting_link
		self.reschedule_count = int(self.reschedule_count or 0) + 1
		self.demo_status = "Scheduled"
		self.save(ignore_permissions=True)
		self.log_request_activity(
			"Demo Rescheduled", remarks="Session {0} rescheduled to {1}".format(self.name, scheduled_date)
		)
		create_calendar_event(self)
		self.notify_sales_scheduled()

	def create_follow_up(self, follow_up_date, next_action=None, assigned_to=None):
		"""Create a Demo Follow Up + ToDo, and move the Demo Request to Follow-up Required."""
		if not follow_up_date:
			follow_up_date = add_days(today(), 7)

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

		change_status(request, "Follow-up Required", ignore_permissions=True)
		return fu

	def set_final_result(self, result):
		allowed = ("Pending", "Converted", "Not Interested", "Closed")
		if result not in allowed:
			frappe.throw(_("Invalid result. Choose from {0}.").format(", ".join(allowed)))
		self.final_result = result
		self.demo_status = "Closed"
		self.save(ignore_permissions=True)
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
			note = frappe.new_doc("Notification Log")
			note.for_user = sales_person
			note.type = "Alert"
			note.document_type = "Demo Session"
			note.document_name = self.name
			note.subject = _(
				"Demo Session {0} closed with result '{1}'; Demo Request {2} was updated directly."
			).format(self.name, result, request.name)
			note.insert(ignore_permissions=True)

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
# permission filters
# ------------------------------------------------------------------

def get_permission_query_conditions(user=None):
	"""Consultants see their own sessions; sales users see sessions of their requests;
	managers and the read-only Developer role see everything."""
	user = user or frappe.session.user
	if not user or user == "Administrator":
		return ""
	roles = frappe.get_roles(user)
	if any(r in roles for r in ("System Manager", "Sales Manager", "Functional Team Manager", "Developer")):
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
	if "Developer" in roles:
		# Developer is read-only: it can open session details (from Demo
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
