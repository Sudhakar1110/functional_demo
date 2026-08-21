# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, now_datetime, today

from functional_demo.portal import create_notification, send_branded_email


class DemoRequest(Document):
	def validate(self):
		self.validate_sales_person()
		self.fetch_contact_details()
		self.validate_consultant()
		self.validate_schedule_conflict()
		self.validate_follow_up_date()
		self.validate_trial_dates()
		self.set_sla_due_date()
		self.apply_priority_rule()

	def after_insert(self):
		self.log_activity("Created", remarks="Demo Request created")

	def on_update(self):
		self.log_status_and_assignment_activity()
		self.assign_consultant_todo()
		self.create_opportunity_on_conversion()

	# ------------------------------------------------------------------
	# validation
	# ------------------------------------------------------------------

	def validate_sales_person(self):
		if not self.sales_person:
			self.sales_person = frappe.session.user

	def fetch_contact_details(self):
		"""Auto-populate the contact person / number / email from the selected
		Customer or Lead so the sales user does not have to type them again."""
		if self.customer:
			if not self.contact_person:
				self.set_primary_contact("Customer", self.customer)
			return

		if self.lead:
			if not self.contact_person:
				self.set_primary_contact("Lead", self.lead)
			lead = frappe.db.get_value(
				"Lead", self.lead, ["email_id", "phone", "mobile_no"], as_dict=True
			)
			if lead:
				self.email = self.email or lead.email_id
				self.contact_number = self.contact_number or lead.mobile_no or lead.phone

	def set_primary_contact(self, party_type, party_name):
		contact = get_primary_contact(party_type, party_name)
		if not contact:
			return
		self.contact_person = contact.name
		details = frappe.db.get_value(
			"Contact", contact.name, ["email_id", "phone", "mobile_no"], as_dict=True
		)
		if details:
			self.email = self.email or details.email_id
			self.contact_number = self.contact_number or (details.mobile_no or details.phone)

	def validate_consultant(self):
		"""Validate consultant assignment.

		With the new Manager Review flow, a new Demo Request does NOT require
		a Functional Consultant at creation time — the sales user creates the
		request and then sends it to the Functional Team Manager for review.
		The consultant is mandatory only after the manager assigns one
		(i.e. when the request moves to Assigned / Scheduled / later states
		AND a consultant is still missing).
		"""
		if self.functional_consultant:
			consultant = frappe.db.get_value(
				"Functional Consultant",
				self.functional_consultant,
				["status", "user"],
				as_dict=True,
			)
			if not consultant:
				frappe.throw(
					_("Functional Consultant {0} was not found.").format(self.functional_consultant)
				)
			if consultant.status == "Inactive":
				frappe.throw(
					_("Functional Consultant {0} is inactive. Only active consultants can be assigned.").format(
						self.functional_consultant
					),
					title=_("Consultant Not Active"),
				)
		elif not self.is_new():
			# For existing requests: a consultant is required once the request
			# has been assigned (Assigned / Scheduled / later states).  During
			# the Manager Review phase (or just requested), no consultant is
			# needed yet.
			status = self.workflow_state or self.status
			needs_consultant = status in (
				"Assigned", "Scheduled", "Demo In Progress", "Demo Completed", "Follow-up Required"
			)
			if needs_consultant:
				frappe.throw(
					_("Please assign a Functional Consultant before the demo moves forward."),
					title=_("Consultant Required"),
				)

	def validate_schedule_conflict(self):
		"""Warn (and prevent) conflicting schedules for the same consultant on the
		same date. The Demo Session validates actual overlaps."""
		if not (self.functional_consultant and self.preferred_demo_date and self.preferred_demo_time):
			return
		if self.workflow_state not in ("Assigned", "Scheduled", "Demo In Progress"):
			return
		conflicts = frappe.db.sql(
			"""
			select ds.name
			from `tabDemo Session` ds
			where ds.functional_consultant = %(consultant)s
				and ds.scheduled_date = %(date)s
				and ds.demo_status not in ('Cancelled', 'Completed', 'Closed')
				and (ds.demo_request is null or ds.demo_request = '' or ds.demo_request != %(self_name)s)
			""",
			{
				"consultant": self.functional_consultant,
				"date": self.preferred_demo_date,
				"self_name": self.name or "",
			},
		)
		if conflicts:
			frappe.throw(
				_("Functional Consultant {0} already has a demo scheduled on {1} ({2}). Please pick a different date, time or consultant.").format(
					self.functional_consultant, self.preferred_demo_date, conflicts[0][0]
				),
				title=_("Schedule Conflict"),
			)

	def validate_follow_up_date(self):
		if self.follow_up_date and self.follow_up_date < today():
			frappe.throw(_("Follow-up Date cannot be in the past."))

	def validate_trial_dates(self):
		"""Trial period (set once the lead is converted) must be a valid window:
		both dates present, end date on or after the start date."""
		if self.trial_start_date and self.trial_end_date and self.trial_end_date < self.trial_start_date:
			frappe.throw(_("Trial End Date cannot be before the Trial Start Date."))

	def set_sla_due_date(self):
		"""Every new request gets an SLA target: the date by which it should be
		scheduled (default 2 days, configurable per request). The daily job
		flags requests that miss it and escalates them to the managers."""
		if self.is_new() and not self.sla_due_date:
			self.sla_due_date = add_days(today(), int(self.sla_days or 2))

	def apply_priority_rule(self):
		"""Auto-set the priority from the lead value / customer tier when the
		priority was not explicitly chosen (still the default 'Medium')."""
		if not self.is_new() or self.priority != "Medium" or not (self.lead or self.customer):
			return
		self.priority = suggested_priority(self.lead, self.customer)

	# ------------------------------------------------------------------
	# activity history (audit trail)
	# ------------------------------------------------------------------

	def log_status_and_assignment_activity(self):
		# on_update runs AFTER the db write in v15, so the pre-save values
		# must come from get_doc_before_save() (db_get would return the new value)
		before = self.get_doc_before_save()
		old_status = before.get("status") if before else None
		old_consultant = before.get("functional_consultant") if before else None

		if old_status and old_status != self.status:
			self.log_activity(
				"Status Changed",
				status=self.status,
				remarks="{0} -> {1}".format(old_status, self.status),
			)

		if old_consultant != self.functional_consultant:
			if old_consultant:
				self.log_activity(
					"Consultant Reassigned",
					remarks="{0} -> {1}".format(old_consultant, self.functional_consultant or "Unassigned"),
				)
			elif self.functional_consultant:
				self.log_activity("Consultant Assigned", remarks="Assigned to {0}".format(self.functional_consultant))

	def log_activity(self, activity_type, status=None, remarks=None):
		row = frappe.new_doc("Demo Request Activity")
		row.update(
			{
				"parent": self.name,
				"parentfield": "demo_request_activity",
				"parenttype": "Demo Request",
				"activity_type": activity_type,
				"activity_date": now_datetime(),
				"user": frappe.session.user,
				"status": status or self.status,
				"remarks": remarks,
			}
		)
		row.db_insert()

	def create_opportunity_on_conversion(self):
		"""Business rule: when a Demo Request is marked Converted, automatically
		create an ERPNext Opportunity so the win flows into the standard sales
		pipeline. The link is kept via the custom_demo_request custom field; the
		opportunity is created exactly once (guarded against re-runs)."""
		if self.workflow_state != "Converted":
			return
		# on_update runs AFTER the db write in v15, so the pre-save workflow
		# state must come from get_doc_before_save() to detect the transition.
		before = self.get_doc_before_save()
		if before and before.get("workflow_state") == "Converted":
			return  # already converted before this save
		if not self.customer:
			# The 'Sales Person' field is a Lead record representing the internal
			# sales person, NOT the prospect. Without a 'Leads' (Customer) on the
			# request there is no real party to create the Opportunity against, so
			# the win is recorded on the request only - never on the sales
			# person's own Lead record.
			self.add_comment(
				"Comment",
				_("Opportunity not created: this request has no Leads (Customer) record — the Sales Person is not a prospect."),
			)
			return

		try:
			if frappe.db.exists("Opportunity", {"custom_demo_request": self.name}):
				return
			company = (
				frappe.db.get_single_value("Global Defaults", "default_company")
				or frappe.defaults.get_user_default("company")
				or frappe.db.get_value("Company", {}, "name")
			)
			if not company:
				return
			opportunity = frappe.new_doc("Opportunity")
			opportunity.opportunity_from = "Customer"
			opportunity.party_name = self.customer
			opportunity.customer_name = frappe.db.get_value(
				"Customer", self.customer, "customer_name"
			) or self.customer
			opportunity.title = _("Demo: {0}").format(self.customer)
			opportunity.transaction_date = today()
			opportunity.company = company
			opportunity.source = _ensure_lead_source("Demo")
			opportunity.opportunity_owner = self.sales_person
			if self.contact_person:
				opportunity.contact_person = self.contact_person
			opportunity.custom_demo_request = self.name
			opportunity.insert(ignore_permissions=True)

			self.add_comment(
				"Comment",
				_("Opportunity {0} was created from this converted demo.").format(opportunity.name),
			)
		except Exception:
			# never block the conversion because the Opportunity could not be created
			frappe.log_error(
				title=_("Demo conversion -> Opportunity creation failed"),
				message=frappe.get_traceback(),
			)

	def assign_consultant_todo(self):
		"""Create a ToDo for the assigned consultant (standard ERPNext assignment)
		and email them so they know a demo has been handed to them.

		With the new Manager Review flow, a ToDo is also created for the
		Functional Team Manager when the request enters Manager Review (so they
		know a demo needs their attention)."""
		before = self.get_doc_before_save()
		old_status = before.get("workflow_state") or before.get("status") if before else None
		new_status = self.workflow_state or self.status

		# --- Manager Review notification: when the request moves to Manager Review ---
		if new_status == "Manager Review" and old_status != "Manager Review":
			self._notify_managers_pending_review()

		# --- Consultant assignment notification (unchanged logic) ---
		old_consultant = before.get("functional_consultant") if before else None
		if not self.functional_consultant or old_consultant == self.functional_consultant:
			return
		user = frappe.db.get_value("Functional Consultant", self.functional_consultant, "user")
		if not user:
			return
		# in-app notification (portal + desk bells) on every (re)assignment
		create_notification(
			user,
			_("Demo Request Assigned to You — {0} ({1})").format(
				self.customer or self.lead or "-", self.name
			),
			"Demo Request",
			self.name,
		)
		# email on every (re)assignment - independent of the ToDo dedupe below
		self.notify_consultant_assigned(user)

		if frappe.db.exists(
			"ToDo",
			{
				"reference_type": "Demo Request",
				"reference_name": self.name,
				"owner": user,
				"status": ["in", ["Open", "Overdue"]],
			},
		):
			return
		todo = frappe.new_doc("ToDo")
		todo.description = _(
			"You have been assigned Demo Request {0} ({1}). Please review the customer requirements and confirm your availability."
		).format(self.name, self.customer or self.lead)
		todo.reference_type = "Demo Request"
		todo.reference_name = self.name
		todo.role = "Functional Consultant"
		todo.owner = user
		todo.insert(ignore_permissions=True)

	def _notify_managers_pending_review(self):
		"""Notify all Functional Team Managers that a demo request is waiting
		for their review and consultant assignment."""
		managers = frappe.get_all(
			"User",
			filters=[
				["Has Role", "role", "=", "Functional Team Manager"],
				["User", "enabled", "=", 1],
			],
			fields=["name"],
		)
		party = self.customer or self.lead or "-"
		for m in managers:
			create_notification(
				m.name,
				_("Demo Request Pending Your Review — {0} ({1})").format(party, self.name),
				"Demo Request",
				self.name,
			)
		# email the managers as well
		self._email_managers_pending_review(managers, party)

	def _email_managers_pending_review(self, managers, party):
		"""Send a branded email to every Functional Team Manager about the
		pending review request."""
		for m in managers:
			try:
				email = frappe.db.get_value("User", m.name, "email")
				if not email:
					continue
				send_branded_email(
					recipients=[email],
					subject=_("Demo Request Pending Review — {0}").format(party),
					heading=_("Demo Request Awaiting Manager Review"),
					intro=_("A new demo request has been submitted and requires your review. Please assign a Functional Consultant."),
					rows=[
						(_("Customer / Lead"), party),
						(_("Interested Template"), self.interested_module or "-"),
						(_("Priority"), self.priority or "-"),
						(_("Preferred Date"), self.preferred_demo_date or "-"),
						(_("Demo Request"), self.name),
					],
					cta_text=_("Review & Assign Consultant"),
					cta_url=frappe.utils.get_url("/app/demo-request/{0}".format(self.name)),
					reference_doctype="Demo Request",
					reference_name=self.name,
				)
			except Exception:
				frappe.log_error(
					title=_("Manager review notification email failed for {0}").format(m.name),
					message=frappe.get_traceback(),
				)

	def notify_consultant_assigned(self, user):
		"""Email the assigned consultant the details of the demo request.

		Fires from on_update whenever the consultant changes (assign or
		reassign), so it covers the desk form, the portal's assign / bulk
		assign and the auto-assign at request creation. A mail failure is
		logged but must never block the assignment itself."""
		try:
			consultant = frappe.db.get_value(
				"Functional Consultant",
				self.functional_consultant,
				["user", "email"],
				as_dict=True,
			)
			# the linked User's email wins (that is where assignments are
			# delivered); fall back to the consultant profile's email field
			email = (
				frappe.db.get_value("User", user, "email")
				or ((consultant.get("email") or "").strip() if consultant else "")
				or ""
			)
			if not email:
				# log so a missing address is never silently lost
				frappe.log_error(
					title=_("Consultant email missing - no mail sent for Demo Request {0}").format(self.name),
					message=_(
						"The consultant {0} (user {1}) has no email on their User or consultant profile."
					).format(self.functional_consultant, user),
				)
				return

			party = self.customer or self.lead or "-"
			subject = _("Demo Request Assigned to You — {0}").format(party)
			# In-app notification (shows in portal bell + desk bell)
			create_notification(
				user,
				subject,
				"Demo Request",
				self.name,
			)
			# Email notification
			send_branded_email(
				recipients=[email],
				subject=subject,
				heading=_("Demo Request Assigned"),
				intro=_("You have been assigned Demo Request {0} by {1}.").format(
					self.name, frappe.session.user
				),
				rows=[
					(_("Customer / Lead"), party),
					(_("Interested Template"), self.interested_module or "-"),
					(_("Priority"), self.priority or "-"),
					(_("Preferred Date"), self.preferred_demo_date or "-"),
					(_("Demo Request"), self.name),
				],
				cta_text=_("Open Demo Request"),
				cta_url=frappe.utils.get_url("/app/demo-request/{0}".format(self.name)),
				reference_doctype="Demo Request",
				reference_name=self.name,
			)
		except Exception:
			# never block the assignment because the email could not be sent
			frappe.log_error(
				title=_("Assignment email to {0} failed for Demo Request {1}").format(
					user, self.name
				),
				message=frappe.get_traceback(),
			)


# ------------------------------------------------------------------
# helpers used across the app
# ------------------------------------------------------------------

def suggested_priority(lead=None, customer=None):
	"""Priority rule shared by the desk form and the portal:

	- Leads with an opportunity amount >= 1,00,000  -> High
	- Leads with an amount below 10,000              -> Low
	- Platinum / Gold customers                      -> High
	- everything else                                -> Medium
	"""
	amount = 0
	if lead:
		# opportunity_amount is a standard ERPNext Lead field, but the column may
		# be missing on sites whose Lead doctype was never synced with it - a
		# missing column must never break priority calculation (or the whole demo
		# request creation), so skip the read and fall back to the customer tier
		# rule instead.
		if frappe.db.has_column("Lead", "opportunity_amount"):
			try:
				value = frappe.db.get_value("Lead", lead, "opportunity_amount")
				amount = float(value or 0)
			except Exception:
				amount = 0
	if amount >= 100000:
		return "High"
	if lead and 0 < amount < 10000:
		return "Low"
	if customer:
		group = frappe.db.get_value("Customer", customer, "customer_group")
		if group in ("Platinum", "Gold"):
			return "High"
	return "Medium"


def run_sla_escalation_checks():
	"""Daily scheduled job: flag Demo Requests whose SLA window has passed
	without being scheduled, and escalate them to the managers."""
	if not frappe.db.exists("DocType", "Demo Request"):
		return
	overdue = frappe.get_all(
		"Demo Request",
		filters=[
			["workflow_state", "in", ["Requested", "Manager Review", "Assigned"]],
			["sla_due_date", "<", frappe.utils.today()],
			["sla_breached", "=", 0],
		],
		fields=["name", "sla_due_date", "escalated"],
		limit_page_length=100,
	) or []
	changed = False
	for row in overdue:
		frappe.db.set_value("Demo Request", row.name, "sla_breached", 1)
		if not row.get("escalated"):
			frappe.db.set_value(
				"Demo Request", row.name, {"escalated": 1, "escalated_on": frappe.utils.today()}
			)
			_escalate_to_managers(row.name, row.get("sla_due_date"))
			_log_sla_activity(row.name, row.get("sla_due_date"))
		changed = True
	if changed:
		frappe.db.commit()


def _escalate_to_managers(request_name, sla_due_date):
	"""Notify every Sales / Functional manager AND the sales person about the breached request."""
	managers = {
		r[0]
		for r in frappe.db.sql(
			"""select distinct u.name from `tabUser` u
		join `tabHas Role` hr on hr.parent = u.name
		where hr.role in ('Sales Manager', 'Functional Team Manager')
			and u.enabled = 1 and u.name != 'Guest'"""
		)
	}
	# Also notify the sales person who owns the request
	req = frappe.db.get_value("Demo Request", request_name, ["sales_person", "customer", "lead"], as_dict=True)
	if req and req.sales_person:
		managers.add(req.sales_person)
		party = req.customer or req.lead or request_name
		# Send email to the sales person
		email = frappe.db.get_value("User", req.sales_person, "email")
		if email:
			try:
				send_branded_email(
					recipients=[email],
					subject=_("SLA Breached — {0} for {1}").format(request_name, party),
					heading=_("SLA Breached"),
					intro=_("Demo Request {0} for {1} was due to be scheduled by {2} but has no demo yet.").format(
						request_name, party, sla_due_date
					),
					rows=[
						(_("Request"), request_name),
						(_("Customer / Lead"), party),
						(_("SLA Due Date"), str(sla_due_date)),
					],
					cta_text=_("Open Demo Request"),
					cta_url=frappe.utils.get_url("/app/demo-request/{0}".format(request_name)),
					reference_doctype="Demo Request",
					reference_name=request_name,
				)
			except Exception:
				frappe.log_error(
					title=_("SLA breach email failed for {0}").format(request_name),
					message=frappe.get_traceback(),
				)
	for user in managers:
		create_notification(
			user,
			_("SLA Breached — {0} was due to be scheduled by {1} but has no demo yet.").format(
				request_name, sla_due_date
			),
			"Demo Request",
			request_name,
		)


def _log_sla_activity(request_name, sla_due_date):
	"""Append an audit entry to the request's activity timeline."""
	row = frappe.new_doc("Demo Request Activity")
	row.update(
		{
			"parent": request_name,
			"parentfield": "demo_request_activity",
			"parenttype": "Demo Request",
			"activity_type": "SLA Breached",
			"activity_date": frappe.utils.now_datetime(),
			"status": "Escalated",
			"remarks": _("Not scheduled by the SLA due date {0}. Escalated to managers.").format(sla_due_date),
		}
	)
	row.db_insert()


def run_followup_overdue_checks():
	"""Daily scheduled job: notify about follow-ups that are overdue."""
	if not frappe.db.exists("DocType", "Demo Follow Up"):
		return
	today = frappe.utils.today()
	overdue = frappe.get_all(
		"Demo Follow Up",
		filters=[
			["status", "in", ["Open", "In Progress"]],
			["follow_up_date", "<", today],
		],
		fields=["name", "demo_request", "customer", "sales_person", "assigned_to", "follow_up_date"],
		limit_page_length=200,
	) or []
	for fu in overdue:
		party = fu.customer or fu.demo_request or fu.name
		# Notify assigned person
		if fu.assigned_to:
			create_notification(
				fu.assigned_to,
				_("Follow-up Overdue — {0} for {1} was due on {2}").format(fu.name, party, fu.follow_up_date),
				"Demo Follow Up",
				fu.name,
			)
		# Notify sales person if different from assigned
		if fu.sales_person and fu.sales_person != fu.assigned_to:
			create_notification(
				fu.sales_person,
				_("Follow-up Overdue — {0} for {1} was due on {2}").format(fu.name, party, fu.follow_up_date),
				"Demo Follow Up",
				fu.name,
			)
	if overdue:
		frappe.db.commit()


def get_primary_contact(party_type, party_name):
	"""Return the primary (or first) Contact linked to a Customer/Lead."""
	if not party_type or not party_name:
		return None
	# NOTE: the order_by MUST be qualified with the Contact table. The
	# Dynamic Link filters join `tabDynamic Link`, which also has a `creation`
	# column, so a bare `creation asc` makes MySQL raise 'Column 'creation' in
	# order clause is ambiguous'.
	names = frappe.get_all(
		"Contact",
		filters=[
			["Dynamic Link", "link_doctype", "=", party_type],
			["Dynamic Link", "link_name", "=", party_name],
			["is_primary_contact", "=", 1],
		],
		limit=1,
		order_by="`tabContact`.`creation` asc",
	)
	if not names:
		names = frappe.get_all(
			"Contact",
			filters=[
				["Dynamic Link", "link_doctype", "=", party_type],
				["Dynamic Link", "link_name", "=", party_name],
			],
			limit=1,
			order_by="`tabContact`.`creation` asc",
		)
	if not names:
		return None
	return frappe.get_doc("Contact", names[0].name)


def _ensure_lead_source(source_name):
	"""Return the Lead Source matching source_name, creating it if missing."""
	if frappe.db.exists("Lead Source", source_name):
		return source_name
	doc = frappe.new_doc("Lead Source")
	doc.source_name = source_name
	doc.insert(ignore_permissions=True)
	return doc.name


def change_status(doc, new_status, ignore_permissions=False):
	"""Move a Demo Request through its workflow with friendly validation.

	Walks the workflow graph so intermediate states (e.g. Draft -> Requested ->
	Manager Review -> Assigned, or Scheduled -> Demo In Progress ->
	Demo Completed) are applied in order even when no direct transition exists.
	Every step is validated by the framework against the current user's roles,
	so users can only move the request along transitions their role allows.
	Jumps further than four transitions ahead are not allowed.
	"""
	from collections import deque

	from frappe.model.workflow import get_workflow, get_workflow_safe_globals

	doc = frappe.get_doc(doc.doctype, doc.name)
	current = doc.get("workflow_state") or doc.get("status") or "Draft"
	if current == new_status:
		return doc

	workflow = get_workflow(doc.doctype)
	roles = frappe.get_roles()

	# Transitions per state, restricted to the current user's roles. This
	# mirrors frappe.model.workflow.get_transitions() but walks the Workflow
	# definition directly: get_transitions() reloads the document from the DB
	# (load_from_db), which wipes the simulated workflow_state set below and
	# used to limit every path to a single transition.
	transitions_from = {}
	for transition in workflow.transitions:
		if transition.allowed not in roles:
			continue
		transitions_from.setdefault(transition.state, []).append(transition)

	def transition_allowed(state, transition):
		if not transition.condition:
			return True
		# evaluate the condition against the simulated state so conditions can
		# inspect the request as it would look in that state
		simulated = {**doc.as_dict(), "workflow_state": state, "status": state}
		return frappe.safe_eval(
			transition.condition, get_workflow_safe_globals(), dict(doc=simulated)
		)

	# find a path through the workflow graph using role-allowed transitions.
	# The path is capped at 4 transitions: real flows may need
	# Draft -> Requested -> Manager Review -> Assigned -> Scheduled, and
	# jumping further ahead (e.g. straight to Converted without a demo)
	# must not be possible.
	parent = {current: None}
	queue = deque([(current, 0)])
	visited = set()
	while queue:
		state, depth = queue.popleft()
		if state in visited:
			continue
		visited.add(state)
		if state == new_status:
			break
		if depth >= 4:
			continue  # do not explore deeper than 4 transitions
		for transition in transitions_from.get(state, []):
			if not transition_allowed(state, transition):
				continue
			next_state = transition.next_state
			if next_state and next_state not in parent:
				parent[next_state] = state
				queue.append((next_state, depth + 1))

	if new_status not in parent:
		frappe.throw(
			_("Demo Request cannot move from '{0}' to '{1}' directly. Please use a supported action.").format(
				current, new_status
			),
			title=_("Invalid Status Change"),
		)

	# apply the path step by step
	path = []
	step = new_status
	while step is not None:
		path.append(step)
		step = parent.get(step)
	path.reverse()

	for state in path:
		doc.workflow_state = state
		doc.status = state  # keep the status field in sync with the workflow state
		doc.save(ignore_permissions=ignore_permissions)
		doc.reload()

	return doc


# ------------------------------------------------------------------
# permission filters
# ------------------------------------------------------------------
def get_permission_query_conditions(user=None):
	"""Sales users see their own requests; consultants see requests assigned to them;
	managers and System Manager see everything."""
	user = user or frappe.session.user
	if not user or user == "Administrator":
		return ""
	roles = frappe.get_roles(user)
	if any(r in roles for r in ("System Manager", "Sales Manager", "Functional Team Manager")):
		return ""
	if "Sales User" in roles:
		return "(`tabDemo Request`.`sales_person` = {0} or `tabDemo Request`.`owner` = {0})".format(
			frappe.db.escape(user)
		)
	if "Functional Consultant" in roles:
		return (
			"(`tabDemo Request`.`functional_consultant` in "
			"(select `tabFunctional Consultant`.`name` from `tabFunctional Consultant` "
			"where `tabFunctional Consultant`.`user` = {0}))"
		).format(frappe.db.escape(user))
	return ""


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	if any(r in roles for r in ("System Manager", "Sales Manager", "Functional Team Manager")):
		return True
	if "Sales User" in roles:
		if doc.get("sales_person") == user or doc.get("owner") == user:
			return True
		return False
	if "Functional Consultant" in roles:
		consultant_user = None
		if doc.get("functional_consultant"):
			consultant_user = frappe.db.get_value(
				"Functional Consultant", doc.get("functional_consultant"), "user"
			)
		return consultant_user == user
	return False
