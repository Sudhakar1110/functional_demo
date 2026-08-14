# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, now_datetime, today


class DemoRequest(Document):
	def validate(self):
		self.validate_sales_person()
		self.fetch_contact_details()
		self.validate_consultant()
		self.validate_schedule_conflict()
		self.validate_follow_up_date()
		self.set_reassignment_flag()
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
		elif self.is_new():
			# Same business rule as the portal: a new Demo Request must already
			# be allocated to a Functional Consultant (the desk form previously
			# allowed creating a consultant-less Draft, which the portal blocked).
			frappe.throw(
				_("Please select a Functional Consultant to run this demo. Every demo request needs a consultant."),
				title=_("Consultant Required"),
			)
		elif self.workflow_state in ("Assigned", "Scheduled", "Demo In Progress", "Demo Completed", "Follow-up Required"):
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

	def set_reassignment_flag(self):
		old = self.db_get("functional_consultant")
		self.consultant_reassigned = 1 if (old and old != self.functional_consultant) else 0

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
		if not (self.customer or self.lead):
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
			opportunity.opportunity_from = "Customer" if self.customer else "Lead"
			opportunity.party_name = self.customer or self.lead
			if self.customer:
				opportunity.customer_name = frappe.db.get_value(
					"Customer", self.customer, "customer_name"
				) or self.customer
			opportunity.title = _("Demo: {0}").format(self.customer or self.lead)
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
		and email them so they know a demo has been handed to them."""
		before = self.get_doc_before_save()
		old = before.get("functional_consultant") if before else None
		if not self.functional_consultant or old == self.functional_consultant:
			return
		user = frappe.db.get_value("Functional Consultant", self.functional_consultant, "user")
		if not user or user == "Administrator":
			return
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
			# the consultant's own email field wins; fall back to the linked User
			email = (
				(consultant.get("email") or "").strip()
				if consultant and consultant.get("email")
				else frappe.db.get_value("User", user, "email") or ""
			)
			if not email:
				return

			subject = _("Demo Request {0} assigned to you").format(self.name)
			message = _(
				"Hi,\n\n"
				"You have been assigned Demo Request {0} by {1}.\n\n"
				"Customer / Lead: {2}\n"
				"Interested Template: {3}\n"
				"Priority: {4}\n"
				"Preferred Date: {5}\n\n"
				"Please review the customer requirements and confirm your availability.\n\n"
				"Open the request: {6}\n"
			).format(
				self.name,
				frappe.session.user,
				self.customer or self.lead or "-",
				self.interested_module or "-",
				self.priority or "-",
				self.preferred_demo_date or "-",
				frappe.utils.get_url("/app/demo-request/{0}".format(self.name)),
			)
			frappe.sendmail(
				recipients=[email],
				subject=subject,
				message=message,
				reference_doctype="Demo Request",
				reference_name=self.name,
				now=True,
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
			["workflow_state", "in", ["Requested", "Assigned"]],
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
	"""Notify every Sales / Functional manager about the breached request."""
	managers = {
		r[0]
		for r in frappe.db.sql(
			"""select distinct u.name from `tabUser` u
			join `tabHas Role` hr on hr.parent = u.name
			where hr.role in ('Sales Manager', 'Functional Team Manager')
				and u.enabled = 1 and u.name != 'Guest'"""
		)
	}
	for user in managers:
		note = frappe.new_doc("Notification Log")
		note.for_user = user
		note.type = "Alert"
		note.document_type = "Demo Request"
		note.document_name = request_name
		note.subject = _(
			"SLA breached: {0} was due to be scheduled by {1} but has no demo yet."
		).format(request_name, sla_due_date)
		note.insert(ignore_permissions=True)


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
			"user": frappe.session.user or "Administrator",
			"status": "Escalated",
			"remarks": _("Not scheduled by the SLA due date {0}. Escalated to managers.").format(
				sla_due_date
			),
		}
	)
	row.db_insert()


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
	Assigned, or Scheduled -> Demo In Progress -> Demo Completed) are applied in
	order even when no direct transition exists. Every step is validated by the
	framework against the current user's roles, so users can only move the
	request along transitions their role allows. Jumps further than three
	transitions ahead are not allowed.
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
	# The path is capped at 3 transitions: real flows never need more than
	# Draft -> Requested -> Assigned -> Scheduled, and jumping further ahead
	# (e.g. straight to Converted without a demo) must not be possible.
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
		if depth >= 3:
			continue  # do not explore deeper than 3 transitions
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
