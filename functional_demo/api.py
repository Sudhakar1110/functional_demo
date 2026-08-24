# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Whitelisted API endpoints used by the Demo Execution screen and quick actions."""

import frappe
from frappe import _

from functional_demo.portal import can_manage_consultants, create_notification, is_functional, is_sales
from functional_demo.sales_demo.doctype.demo_request.demo_request import (
	change_status,
	get_primary_contact,
	suggested_priority,
)
from functional_demo.sales_demo.doctype.demo_session.demo_session import (
	create_calendar_event,
)


# ---------------------------------------------------------------------------
# small shared helpers
# ---------------------------------------------------------------------------

def _as_list(value):
	"""Normalize a JSON array / comma separated string / list into a Python list."""
	if not value:
		return []
	if isinstance(value, str):
		import json

		try:
			parsed = json.loads(value)
			return parsed if isinstance(parsed, list) else []
		except Exception:
			return [v.strip() for v in value.split(",") if v.strip()]
	return list(value)


def _clean_error():
	"""Return the last meaningful line of the current traceback."""
	tb = frappe.get_traceback()
	return next(
		(
			line.strip()
			for line in reversed(tb.splitlines())
			if line.strip() and not line.strip().startswith("File ")
		),
		_("unknown error"),
	)


def _ensure_customer(customer_name, contact_person=None, contact_number=None, email=None):
	"""Return an existing Customer matching the name, or create it (with a
	linked Contact carrying the provided details) so the portal can auto-create
	a customer from a free-typed name - the record then appears in the desk too.

	Returns (customer_name, contact_name) where contact_name is the linked
	Contact created (or None)."""
	name = (customer_name or "").strip()
	if not name:
		return "", None
	existing = frappe.db.get_value("Customer", {"customer_name": name}, "name")
	if existing:
		return existing, None
	if frappe.db.exists("Customer", name):
		return name, None

	cust = frappe.new_doc("Customer")
	cust.customer_name = name
	cust.insert(ignore_permissions=True)

	contact_name = None
	person = (contact_person or "").strip() or name
	try:
		contact = frappe.new_doc("Contact")
		contact.first_name = person
		contact.is_primary_contact = 1
		contact.append(
			"links",
			{"link_doctype": "Customer", "link_name": cust.name, "link_title": name},
		)
		if email:
			contact.email_id = email
		if contact_number:
			contact.mobile_no = contact_number
		contact.insert(ignore_permissions=True)
		contact_name = contact.name
	except Exception:
		# the customer is already created - a missing Contact must never
		# block the demo request
		frappe.log_error(
			title=_("Could not create Contact for new lead {0}").format(name),
			message=frappe.get_traceback(),
		)
	return cust.name, contact_name


# ---------------------------------------------------------------------------
# Lookup helpers (auto-fetch customer / lead / consultant / template details)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_customer_details(customer=None):
	"""Auto-fetch primary contact details for a Customer.

	The argument is optional so a client that fires the call without a value
	(e.g. a stale bundle or an empty field change) gets an empty dict instead
	of a TypeError 500."""
	if not customer:
		return {}
	contact = get_primary_contact("Customer", customer)
	details = {
		"contact_person": contact.name if contact else "",
		"contact_number": "",
		"email": "",
	}
	if contact:
		contact_doc = frappe.db.get_value(
			"Contact", contact.name, ["email_id", "phone", "mobile_no"], as_dict=True
		)
		if contact_doc:
			details["email"] = contact_doc.email_id or ""
			details["contact_number"] = contact_doc.mobile_no or contact_doc.phone or ""
	return details


@frappe.whitelist()
def get_lead_details(lead=None):
	"""Auto-fetch details for a Lead.

	The argument is optional so a client that fires the call without a value
	(e.g. a stale bundle or an empty field change) gets an empty dict instead
	of a TypeError 500."""
	if not lead:
		return {}
	lead_doc = frappe.db.get_value(
		"Lead", lead, ["lead_name", "email_id", "phone", "mobile_no", "company_name"], as_dict=True
	)
	if not lead_doc:
		return {}
	# contact_person must be a real Contact document (the field is a Link) -
	# resolve the lead's primary contact exactly like customers do, and only
	# fall back to the lead name when no contact exists yet.
	contact = get_primary_contact("Lead", lead)
	return {
		"contact_person": contact.name if contact else "",
		"contact_number": lead_doc.mobile_no or lead_doc.phone or "",
		"email": lead_doc.email_id or "",
	}


@frappe.whitelist()
def get_available_consultants(module=None, include_inactive=0):
	"""List Functional Consultants (active by default), optionally filtered by
	an ERPNext module they specialize in. Also returns their current workload."""
	# Exclude only explicitly-Inactive consultants. This MUST be filtered in
	# Python: Frappe stores an unset Select field as NULL, and SQL treats
	# NULL != 'Inactive' as unknown (row excluded) - so both '=' and 'not in'
	# filters silently hid consultants whose status was never set.
	# ignore_permissions: consultants are shared reference data - the portal
	# is already gated by role, so no user/role setup should ever hide them.
	consultants = frappe.get_all(
		"Functional Consultant",
		filters={} if include_inactive else None,
		ignore_permissions=True,
		fields=[
			"name",
			"consultant_name",
			"user",
			"specialization",
			"availability",
			"experience_years",
			"status",
		],
		order_by="consultant_name asc",
	)
	if not include_inactive:
		consultants = [c for c in consultants if (c.get("status") or "") != "Inactive"]

	# ERPNext modules per consultant (child table - fetched separately for safety)
	modules_map = {}
	names = [c.name for c in consultants]
	if names:
		for row in frappe.get_all(
			"Consultant Module",
			filters={"parent": ["in", names]},
			fields=["parent", "module"],
		):
			modules_map.setdefault(row.parent, []).append(row.module)

	# workload: scheduled/in-progress demo sessions per consultant
	workload = dict(
		frappe.db.sql(
			"""select functional_consultant, count(*) from `tabDemo Session`
			where demo_status in ('Scheduled', 'In Progress')
			group by functional_consultant"""
		)
	)

	out = []
	for c in consultants:
		modules = modules_map.get(c.name) or []
		if module and module not in modules and c.get("specialization") != module:
			continue
		out.append(
			{
				"name": c.name,
				"consultant_name": c.consultant_name,
				"user": c.user,
				"specialization": c.specialization,
				"availability": c.availability,
				"experience_years": c.experience_years,
				"status": c.status,
				"modules": modules,
				"active_demos": int(workload.get(c.name) or 0),
			}
		)
	return out


# ---------------------------------------------------------------------------
# Demo Request quick actions
# ---------------------------------------------------------------------------

@frappe.whitelist()
def _party_and_consultant(doc):
	"""Friendly labels for a demo's party (customer/lead) and consultant, used
	in the smart success popups - e.g. 'Acme Corp' and 'Jack Wilson' instead of
	the raw ERPNext names."""
	if not doc:
		return "", ""
	if getattr(doc, "doctype", "") == "Demo Session" and doc.get("demo_request"):
		try:
			req = frappe.get_doc("Demo Request", doc.demo_request)
		except Exception:
			req = doc
	else:
		req = doc
	party = ""
	if req.get("customer"):
		party = frappe.db.get_value("Customer", req.customer, "customer_name") or req.customer
	elif req.get("lead"):
		party = frappe.db.get_value("Lead", req.lead, "lead_name") or req.lead
	consultant = ""
	consultant_name = req.get("functional_consultant")
	if consultant_name:
		consultant = (
			frappe.db.get_value("Functional Consultant", consultant_name, "consultant_name")
			or consultant_name
		)
	return party, consultant


def _fmt_date(value):
	"""Pretty date for success popups (falls back to the raw value)."""
	if not value:
		return ""
	try:
		return frappe.utils.format_date(value, "medium")
	except Exception:
		return str(value)


@frappe.whitelist()
def schedule_demo(demo_request=None, scheduled_date=None, start_time=None, end_time=None, meeting_link=None, interested_module=None, name=None):
	"""Schedule (or reschedule) a demo for a Demo Request and create a Demo Session.

	Arguments are optional so a client that fires the call without a value gets
	a clear popup instead of a TypeError 500."""
	# Belt & braces for stale portal bundles: older pages posted the request
	# under the key 'name' (or wrapped the payload in an 'args' dict), which
	# would otherwise raise 'unexpected keyword argument' / 'Demo Request is
	# missing' before the function body even runs - accept both so a cached
	# page can never block scheduling.
	demo_request = demo_request or name
	if not demo_request:
		fd = frappe.local.form_dict or {}
		if isinstance(fd.get("args"), dict):
			demo_request = fd["args"].get("demo_request") or fd["args"].get("name")
		demo_request = demo_request or fd.get("demo_request") or fd.get("name")
	if not demo_request:
		# log what actually arrived so the real cause is never lost to a
		# truncated popup - the portal error dialog only shows the last line
		frappe.log_error(
			title=_("Schedule Demo: missing request name"),
			message="form_dict={0}\nargs={1}\nkwargs demo_request={2!r} name={3!r}".format(
				str(frappe.local.form_dict or {})[:500],
				str(getattr(frappe.local, "request", None))[:200],
				demo_request,
				name,
			),
		)
		frappe.throw(
			_("Demo Request is missing. Please refresh the page (Ctrl+Shift+R) and try again. Server received: {0}").format(
				str(frappe.local.form_dict or {})[:300]
			),
			title=_("Missing Request"),
		)
	dr = frappe.get_doc("Demo Request", demo_request)
	frappe.has_permission("Demo Request", "write", doc=dr, throw=True)

	# Auto-fill the date when the click sends none: first the request's
	# preferred date, then today. Scheduling should never be blocked by an
	# empty date (stale page, forgotten picker, or a request created without
	# a preferred slot) - the session can always be rescheduled later.
	if not scheduled_date:
		scheduled_date = dr.preferred_demo_date or frappe.utils.today()

	if not dr.functional_consultant:
		frappe.throw(
			_("Please assign a Functional Consultant before scheduling the demo."),
			title=_("Consultant Required"),
		)

	try:
		session_name = frappe.db.get_value(
			"Demo Session",
			{"demo_request": dr.name, "demo_status": ["in", ["Scheduled", "In Progress"]]},
			"name",
		)

		if session_name:
			ds = frappe.get_doc("Demo Session", session_name)
			frappe.has_permission("Demo Session", "write", doc=ds, throw=True)
			ds.scheduled_date = scheduled_date
			ds.start_time = start_time
			ds.end_time = end_time
			ds.meeting_link = meeting_link
			# keep the Interested Template chosen at scheduling (falls back to
			# the request's value when the dialog sent none)
			ds.interested_module = interested_module or ds.interested_module
			# auto-select the request's consultant - a session created before the
			# consultant was always copied can be empty, so top it up on reschedule
			if not ds.functional_consultant:
				ds.functional_consultant = dr.functional_consultant
			ds.reschedule_count = int(ds.reschedule_count or 0) + 1
			# a rescheduled session is marked Rescheduled (still active/startable)
			if ds.demo_status == "Scheduled":
				ds.demo_status = "Rescheduled"
			ds.flags.rescheduling = True
			ds.save(ignore_permissions=True)
			party, consultant = _party_and_consultant(dr)
			frappe.msgprint(
				_("Demo {0} rescheduled to {1}{2}{3}.").format(
					ds.name,
					_fmt_date(scheduled_date),
					" for " + party if party else "",
					" with " + consultant if consultant else "",
				)
			)
		else:
			ds = frappe.new_doc("Demo Session")
			ds.demo_request = dr.name
			# auto-select: the session always carries the request's consultant so
			# the form never shows 'No consultant selected'
			ds.functional_consultant = dr.functional_consultant
			ds.consultant_user = dr.consultant_user
			# the Interested Template chosen at scheduling (falls back to the
			# request's value) - feedback on this demo groups under this template
			ds.interested_module = interested_module or dr.interested_module
			ds.scheduled_date = scheduled_date
			ds.start_time = start_time
			ds.end_time = end_time
			ds.meeting_link = meeting_link
			ds.insert(ignore_permissions=True)
			party, consultant = _party_and_consultant(dr)
			frappe.msgprint(
				_("Demo {0} scheduled for {1}{2}{3}.").format(
					ds.name,
					_fmt_date(scheduled_date),
					" for " + party if party else "",
					" with " + consultant if consultant else "",
				)
			)

		# keep the Demo Request in sync (fields first, then the workflow move).
		# A template chosen at scheduling also updates the request, so the
		# request list/reports and the session always agree.
		dr.preferred_demo_date = scheduled_date
		dr.preferred_demo_time = start_time or dr.preferred_demo_time
		if interested_module:
			dr.interested_module = interested_module
		dr.save(ignore_permissions=True)
		change_status(dr, "Scheduled", ignore_permissions=True)

		create_calendar_event(ds)
		return {"demo_session": ds.name, "demo_request": dr.name}
	except frappe.exceptions.ValidationError:
		# known validation failures (schedule conflict, missing date, permissions) -
		# the framework already raised a clean message for these
		raise
	except Exception:
		traceback = frappe.get_traceback()
		frappe.log_error(title=_("Demo scheduling failed"), message=traceback)
		last_line = next(
			(l.strip() for l in reversed(traceback.splitlines()) if l.strip() and not l.strip().startswith("File ")),
			_("unknown error"),
		)
		frappe.throw(
			_("The demo could not be scheduled because of a technical error: {0}").format(last_line),
			title=_("Scheduling Failed"),
		)


@frappe.whitelist()
def create_demo_follow_up(demo_request=None, follow_up_date=None, next_action=None, assigned_to=None):
	"""Create a Demo Follow Up record + ToDo for a Demo Request.

	Arguments are optional so a client that fires the call without a value gets
	a clear popup instead of a TypeError 500."""
	if not demo_request:
		frappe.throw(
			_("Demo Request is missing. Please refresh the page and try again."),
			title=_("Missing Request"),
		)
	if not follow_up_date:
		frappe.throw(_("Please select a follow-up date."))
	if not is_sales():
		frappe.throw(_("Only the sales team can create follow-ups."), frappe.PermissionError)

	dr = frappe.get_doc("Demo Request", demo_request)
	frappe.has_permission("Demo Request", "write", doc=dr, throw=True)

	fu = frappe.new_doc("Demo Follow Up")
	fu.demo_request = dr.name
	fu.customer = dr.customer
	fu.sales_person = dr.sales_person
	fu.functional_consultant = dr.functional_consultant
	fu.follow_up_date = follow_up_date
	fu.next_action = next_action
	fu.assigned_to = assigned_to or dr.sales_person
	fu.insert(ignore_permissions=True)

	dr.follow_up_date = follow_up_date
	dr.next_action = next_action
	dr.save(ignore_permissions=True)
	try:
		change_status(dr, "Follow-up Required", ignore_permissions=True)
	except Exception:
		# The request transition to "Follow-up Required" is role-gated in the
		# workflow, so the caller (e.g. a consultant or manager) may be blocked
		# even though the follow-up itself was created. Apply the state directly
		# (status + workflow_state, exactly what the workflow would write) and
		# log - never fail the action or roll back the follow-up.
		frappe.log_error(
			title=_("Demo Request {0} could not be moved to 'Follow-up Required'").format(dr.name),
			message=frappe.get_traceback(),
		)
		frappe.db.set_value(
			"Demo Request", dr.name, {"status": "Follow-up Required", "workflow_state": "Follow-up Required"}
		)

	party, _consultant = _party_and_consultant(dr)
	frappe.msgprint(
		_("Follow-up {0} created for {1}. Assigned to {2}.").format(
			fu.name, party or dr.name, fu.assigned_to or dr.sales_person or "-"
		)
	)
	return fu.name


@frappe.whitelist()
def set_demo_result(demo_request=None, result=None):
	"""Set the final result on a Demo Request (Converted / Not Interested / Closed).

	Arguments are optional so a client that fires the call without a value gets
	a clear popup instead of a TypeError 500."""
	if not demo_request:
		frappe.throw(
			_("Demo Request is missing. Please refresh the page and try again."),
			title=_("Missing Request"),
		)
	if not result:
		frappe.throw(_("Please choose a result (Converted / Not Interested / Closed)."))
	allowed = ["Converted", "Not Interested", "Closed"]
	if result not in allowed:
		frappe.throw(_("Invalid result. Choose from {0}.").format(", ".join(allowed)))

	dr = frappe.get_doc("Demo Request", demo_request)
	frappe.has_permission("Demo Request", "write", doc=dr, throw=True)
	dr = change_status(dr, result, ignore_permissions=True)
	party, _consultant = _party_and_consultant(dr)
	frappe.msgprint(_("Demo {0} for {1} marked as {2}.").format(dr.name, party or "-", result))
	return dr.status


@frappe.whitelist()
def set_trial_period(demo_request=None, trial_start_date=None, trial_end_date=None):
	"""Set the trial period on a converted demo request (sales team only).

	The trial window is when the converted customer gets full access; a
	reminder email goes to the sales person one day before the trial end date.
	"""
	if not is_sales():
		frappe.throw(_("Only the sales team can set the trial period."), frappe.PermissionError)
	if not demo_request:
		frappe.throw(
			_("Demo Request is missing. Please refresh the page and try again."),
			title=_("Missing Request"),
		)
	if not trial_start_date or not trial_end_date:
		frappe.throw(_("Please select both the trial start and end dates."))
	if trial_end_date < trial_start_date:
		frappe.throw(_("Trial End Date cannot be before the Trial Start Date."))

	dr = frappe.get_doc("Demo Request", demo_request)
	frappe.has_permission("Demo Request", "write", doc=dr, throw=True)
	before = dr.get_doc_before_save()
	dr.trial_start_date = trial_start_date
	dr.trial_end_date = trial_end_date
	# changing the dates re-arms the reminder (it fires 1 day before the end)
	if before and (before.trial_start_date != trial_start_date or before.trial_end_date != trial_end_date):
		dr.trial_reminder_sent = 0
	dr.save()

	frappe.msgprint(
		_("Trial period set from {0} to {1}. A reminder will be sent to the sales person one day before it ends.").format(
			trial_start_date, trial_end_date
		)
	)
	return {"trial_start_date": dr.trial_start_date, "trial_end_date": dr.trial_end_date}


@frappe.whitelist()
def send_trial_reminder(demo_request=None):
	"""Send the trial-ending reminder (email + in-app notification) to the sales
	person of a converted demo request right now - used to verify the reminder
	works, or to nudge the sales person ahead of the scheduled one-day-before
	reminder. Sales team only."""
	if not is_sales():
		frappe.throw(_("Only the sales team can send the trial reminder."), frappe.PermissionError)
	if not demo_request:
		frappe.throw(
			_("Demo Request is missing. Please refresh the page and try again."),
			title=_("Missing Request"),
		)

	dr = frappe.get_doc("Demo Request", demo_request)
	frappe.has_permission("Demo Request", "read", doc=dr, throw=True)
	if dr.status != "Converted":
		frappe.throw(_("Trial reminders apply only to converted demo requests."))
	if not (dr.trial_start_date and dr.trial_end_date):
		frappe.throw(_("Set the trial start and end dates before sending the reminder."))

	from functional_demo.install import _notify_trial_period_reminder

	# mark_sent=False: a manual send is a verification / early nudge and must
	# not suppress the scheduled one-day-before reminder.
	_notify_trial_period_reminder(
		{
			"name": dr.name,
			"customer": dr.customer,
			"lead": dr.lead,
			"sales_person": dr.sales_person,
			"owner": dr.owner,
			"trial_start_date": dr.trial_start_date,
			"trial_end_date": dr.trial_end_date,
		},
		mark_sent=False,
	)
	frappe.db.commit()
	frappe.msgprint(
		_("Trial reminder sent to the sales person ({0}).").format(dr.sales_person or "-")
	)
	return True


@frappe.whitelist()
def cancel_demo_request(demo_request=None, reason=None, name=None):
	"""Cancel a Demo Request from the portal: close its open demo sessions and
	move the request to Cancelled (the workflow's role rules apply).

	Cancelling is idempotent: a request that is already Cancelled / Closed /
	Converted / Not Interested returns its current status quietly (no error
	popup), so a stale page or a double click can never scare the user.

	The argument is optional so a client that fires the call without a value
	(a stale cached page) gets a clear popup instead of a TypeError 500."""
	# Belt & braces for stale portal bundles: older pages posted the request
	# under the key 'name' - accept it too so the framework does not raise
	# 'unexpected keyword argument' before this function even runs.
	demo_request = demo_request or name
	# Ultimate fallback: dig the name out of whatever the client actually sent
	# (form_dict may hold the raw body or a nested 'args' dict on odd clients).
	if not demo_request:
		fd = frappe.local.form_dict or {}
		if isinstance(fd.get("args"), dict):
			demo_request = fd["args"].get("demo_request") or fd["args"].get("name")
		demo_request = demo_request or fd.get("demo_request") or fd.get("name")
	if not demo_request:
		# log what actually arrived so the real cause is never lost to a
		# truncated popup - the portal error dialog only shows the last line
		frappe.log_error(
			title=_("Cancel Demo Request: missing request name"),
			message="form_dict={0}\nargs={1}\nkwargs demo_request={2!r} name={3!r}".format(
				str(frappe.local.form_dict or {})[:500],
				str(getattr(frappe.local, "request", None))[:200],
				demo_request,
				name,
			),
		)
		frappe.throw(
			_("Demo Request is missing. Please refresh the page (Ctrl+Shift+R) and try again. Server received: {0}").format(
				str(frappe.local.form_dict or {})[:300]
			),
			title=_("Missing Request"),
		)

	doc = frappe.get_doc("Demo Request", demo_request)

	current = doc.get("workflow_state") or doc.get("status") or "Draft"
	if current in ("Cancelled", "Closed", "Converted", "Not Interested"):
		# Already in a final state - nothing to cancel. Return quietly so a
		# stale page or a second click shows a confirmation, not an error.
		return {"status": current, "already": True}

	# Move the request to Cancelled FIRST - if the user's role does not allow
	# the cancel transition, nothing is changed (no partial state). Some states
	# have no Cancel transition at all in the workflow (Follow-up Required,
	# Demo Completed) or gate it to managers (Demo In Progress) - in those
	# cases apply the final state directly, exactly like the workflow would,
	# so a cancellation is never blocked by the role rules.
	try:
		change_status(doc, "Cancelled", ignore_permissions=True)
	except Exception:
		frappe.log_error(
			title=_("Demo Request {0} could not be moved to Cancelled via the workflow").format(
				doc.name
			),
			message=frappe.get_traceback(),
		)
		frappe.db.set_value(
			"Demo Request", doc.name, {"status": "Cancelled", "workflow_state": "Cancelled"}
		)
		doc = frappe.get_doc("Demo Request", doc.name)

	# Now close any open demo sessions (without re-triggering the session ->
	# request sync; the request is already Cancelled).
	for session_name in frappe.get_all(
		"Demo Session",
		filters={"demo_request": doc.name, "demo_status": ["in", ["Scheduled", "In Progress"]]},
		pluck="name",
	):
		session = frappe.get_doc("Demo Session", session_name)
		session.flags.skip_request_sync = True
		session.demo_status = "Cancelled"
		if reason:
			session.consultant_remarks = (
				session.consultant_remarks + "\n" + reason
				if session.consultant_remarks
				else reason
			)
		session.save(ignore_permissions=True)

	party, _consultant = _party_and_consultant(doc)
	frappe.msgprint(_("Demo {0} for {1} cancelled.").format(doc.name, party or "-"))
	return {"status": doc.get("status") or doc.get("workflow_state")}


@frappe.whitelist()
def unassign_consultant(demo_request=None):
	"""Unassign the Functional Consultant from an Assigned Demo Request and move
	it back to Requested (the workflow's role rules apply).

	The argument is optional so a client that fires the call without a value
	gets a clear popup instead of a TypeError 500."""
	if not demo_request:
		frappe.throw(
			_("Demo Request is missing. Please refresh the page and try again."),
			title=_("Missing Request"),
		)

	doc = frappe.get_doc("Demo Request", demo_request)
	frappe.has_permission("Demo Request", "write", doc=doc, throw=True)

	if (doc.get("workflow_state") or doc.get("status")) != "Assigned":
		frappe.throw(
			_("Only an Assigned Demo Request can be unassigned. This request is {0}.").format(
				doc.get("workflow_state") or doc.get("status") or "Draft"
			),
			title=_("Cannot Unassign"),
		)

	# move Assigned -> Requested (the workflow's 'Unassign Consultant' transition)
	change_status(doc, "Requested", ignore_permissions=True)

	# now clear the consultant (allowed in Requested state) and log the change
	doc = frappe.get_doc("Demo Request", demo_request)
	doc.functional_consultant = None
	doc.consultant_user = None
	doc.save(ignore_permissions=True)

	frappe.msgprint(
		_("Consultant unassigned from {0}. The request is back to Requested.").format(demo_request)
	)
	return {"status": doc.status}


# ---------------------------------------------------------------------------
# Bulk actions (Demo Requests list page)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def bulk_send_to_manager(requests=None):
	"""Sales user sends many Demo Requests to the Functional Team Manager
	for review at once (bulk version of assign_to_manager)."""
	names = _as_list(requests)
	if not names:
		frappe.throw(_("Please select at least one demo request."), title=_("Nothing Selected"))

	done, errors = [], []
	for name in names:
		try:
			doc = frappe.get_doc("Demo Request", name)
			frappe.has_permission("Demo Request", "write", doc=doc, throw=True)
			current = doc.get("workflow_state") or doc.get("status") or "Draft"
			if current == "Manager Review":
				done.append(name)
				continue
			from functional_demo.sales_demo.doctype.demo_request.demo_request import change_status
			if current in (None, "", "Draft"):
				doc = change_status(doc, "Requested")
				doc = frappe.get_doc("Demo Request", name)
			if (doc.get("workflow_state") or doc.get("status")) == "Requested":
				doc = change_status(doc, "Manager Review")
			done.append(name)
		except Exception:
			errors.append("{0}: {1}".format(name, _clean_error()))

	msg = _("{0} request(s) sent to Functional Team Manager for review.").format(len(done))
	if errors:
		msg += " " + _("{0} failed: {1}").format(len(errors), "; ".join(errors))
	frappe.msgprint(msg)
	return {"done": done, "errors": errors}


@frappe.whitelist()
def bulk_assign_consultant(requests=None, consultant=None):
	"""Assign one Functional Consultant to many Demo Requests at once.

	Each request is checked individually - requests that fail (permission, rule,
	scheduling) are reported in the response instead of aborting the whole batch.
	A consultant assignment is direct: the request moves straight to Assigned
	(no manager approval step). Used by Functional Team Manager / Sales Manager."""
	names = _as_list(requests)
	if not names:
		frappe.throw(_("Please select at least one demo request."), title=_("Nothing Selected"))
	if not consultant:
		frappe.throw(_("Please select a Functional Consultant."))
	if not frappe.db.exists("Functional Consultant", consultant):
		frappe.throw(_("Functional Consultant {0} was not found.").format(consultant))

	consultant_user = frappe.db.get_value("Functional Consultant", consultant, "user")
	done, errors = [], []
	for name in names:
		try:
			doc = frappe.get_doc("Demo Request", name)
			frappe.has_permission("Demo Request", "write", doc=doc, throw=True)
			doc.functional_consultant = consultant
			doc.consultant_user = consultant_user
			doc.save()
			state = doc.get("workflow_state") or doc.get("status") or "Draft"
			if state in ("Draft", "Requested", "Manager Review"):
				change_status(doc, "Assigned")
			done.append(name)
		except Exception:
			errors.append("{0}: {1}".format(name, _clean_error()))

	msg = _("Consultant assigned to {0} request(s).").format(len(done))
	if errors:
		msg += " " + _("{0} failed: {1}").format(len(errors), "; ".join(errors))
	frappe.msgprint(msg)
	return {"done": done, "errors": errors}


@frappe.whitelist()
def bulk_reschedule_demo(requests=None, scheduled_date=None, start_time=None, end_time=None):
	"""Move many Demo Requests to a new preferred date (and time) in one go,
	updating any open Demo Session for each request as well."""
	names = _as_list(requests)
	if not names:
		frappe.throw(_("Please select at least one demo request."), title=_("Nothing Selected"))
	if not scheduled_date:
		frappe.throw(_("Please select a new date."))

	done, errors = [], []
	for name in names:
		try:
			doc = frappe.get_doc("Demo Request", name)
			frappe.has_permission("Demo Request", "write", doc=doc, throw=True)
			doc.preferred_demo_date = scheduled_date
			if start_time:
				doc.preferred_demo_time = start_time
			doc.save()

			session_name = frappe.db.get_value(
				"Demo Session",
				{"demo_request": name, "demo_status": ["in", ["Scheduled", "In Progress"]]},
				"name",
			)
			if session_name:
				session = frappe.get_doc("Demo Session", session_name)
				session.scheduled_date = scheduled_date
				if start_time:
					session.start_time = start_time
				if end_time:
					session.end_time = end_time
				# mark an already-scheduled session as Rescheduled
				if session.demo_status == "Scheduled":
					session.demo_status = "Rescheduled"
				session.save(ignore_permissions=True)
				create_calendar_event(session)
			done.append(name)
		except Exception:
			errors.append("{0}: {1}".format(name, _clean_error()))

	msg = _("{0} request(s) rescheduled to {1}.").format(len(done), scheduled_date)
	if errors:
		msg += " " + _("{0} failed: {1}").format(len(errors), "; ".join(errors))
	frappe.msgprint(msg)
	return {"done": done, "errors": errors}


@frappe.whitelist()
def export_demo_requests(status=None):
	"""Export the visible Demo Requests (honouring the current status filter)
	as CSV text - the portal downloads it as a file."""
	import csv
	import io

	filters = {}
	if status:
		filters["status"] = status

	# Export EVERYTHING that matches the filter - page through the result set
	# instead of silently truncating at 500 rows.
	rows = []
	start = 0
	while True:
		batch = frappe.get_all(
			"Demo Request",
			filters=filters,
			fields=[
				"name", "customer", "lead", "company", "contact_person", "email",
				"interested_module", "priority", "functional_consultant", "sales_person",
				"preferred_demo_date", "preferred_demo_time", "demo_type", "status",
				"sla_due_date", "sla_breached", "creation",
			],
			order_by="creation desc",
			start=start,
			limit_page_length=500,
		) or []
		rows.extend(batch)
		if len(batch) < 500:
			break
		start += 500

	buf = io.StringIO()
	writer = csv.writer(buf)
	# 'Sales Person' appears twice in a request (the Lead record and the owning
	# User) - keep the labels distinct so the columns are not ambiguous.
	writer.writerow(
		["Request", "Customer", "Sales Person (Lead)", "Company", "Contact Person", "Email",
		 "Interested Template", "Priority", "Functional Consultant", "Sales Person (User)",
		 "Preferred Date", "Preferred Time", "Demo Type", "Status", "SLA Due Date",
		 "SLA Breached", "Created"]
	)
	for r in rows:
		writer.writerow(
			[r.get("name"), r.get("customer"), r.get("lead"), r.get("company"),
			 r.get("contact_person"), r.get("email"), r.get("interested_module"),
			 r.get("priority"), r.get("functional_consultant"), r.get("sales_person"),
			 r.get("preferred_demo_date"), r.get("preferred_demo_time"), r.get("demo_type"),
			 r.get("status"), r.get("sla_due_date"), "Yes" if r.get("sla_breached") else "",
			 (r.get("creation") or "")[:10]]
		)
	return buf.getvalue()


# ---------------------------------------------------------------------------
# Demo Session quick actions (used by the form and the Execution screen)
# ---------------------------------------------------------------------------

def _get_session(name):
	"""Fetch a Demo Session for a write action, with a friendly error when the
	name is missing (so a stale client can never raise a TypeError 500)."""
	if not name:
		frappe.throw(
			_("Demo Session is missing. Please refresh the page and try again."),
			title=_("Missing Session"),
		)
	ds = frappe.get_doc("Demo Session", name)
	frappe.has_permission("Demo Session", "write", doc=ds, throw=True)
	return ds


@frappe.whitelist()
def get_demo_execution_data(demo_session=None):
	"""Load everything the consultant needs for the demo on a single screen.

	The argument is optional so a client that fires the call without a value
	gets a clear popup instead of a TypeError 500."""
	if not demo_session:
		frappe.throw(
			_("Demo Session is missing. Please refresh the page and try again."),
			title=_("Missing Session"),
		)
	# Session details are shared reference data - Demo Feedback / Results list
	# every session, so any portal role may open a session's details read-only
	# (demo ID, template, consultant, requirements). Write actions stay gated
	# by can_write below, so document-level read permission is not enforced
	# here.
	from functional_demo.portal import is_developer, is_functional, is_manager, is_sales

	ds = frappe.get_doc("Demo Session", demo_session)
	if not (
		frappe.session.user == "Administrator"
		or is_sales()
		or is_functional()
		or is_manager()
		or is_developer()
	):
		frappe.throw(
			_("You do not have permission to view this demo session."),
			frappe.PermissionError,
		)

	request_doc = frappe.get_doc("Demo Request", ds.demo_request) if ds.demo_request else None
	consultant = None
	if ds.functional_consultant:
		consultant = frappe.db.get_value(
			"Functional Consultant",
			ds.functional_consultant,
			["consultant_name", "user", "specialization", "availability", "email"],
			as_dict=True,
		)

	from functional_demo.sales_demo.doctype.demo_session.demo_session import (
		can_cancel_session,
		can_execute_session_action,
	)

	can_write = frappe.has_permission("Demo Session", "write", doc=ds)
	# Restrict write access: only the assigned functional consultant may
	# edit the session. Managers and other consultants see it read-only.
	if can_write and ds.functional_consultant:
		consultant_user = frappe.db.get_value(
			"Functional Consultant", ds.functional_consultant, "user"
		)
		if consultant_user and frappe.session.user != consultant_user:
			can_write = False

	return {
		"session": {
			"name": ds.name,
			"demo_status": ds.demo_status,
			"scheduled_date": ds.scheduled_date,
			"start_time": str(ds.start_time or ""),
			"end_time": str(ds.end_time or ""),
			"meeting_link": ds.meeting_link,
			"demo_type": ds.demo_type,
			"demo_notes": ds.demo_notes,
			"overall_feedback": ds.overall_feedback,
			"interested": ds.interested,
			"requirements_met": ds.requirements_met,
			"follow_up_required": ds.follow_up_required,
			"follow_up_date": ds.follow_up_date,
			"next_action": ds.next_action,
			"consultant_remarks": ds.consultant_remarks,
			"final_result": ds.final_result,
			"started_on": ds.started_on,
			"completed_on": ds.completed_on,
		},
		"request": {
			"name": ds.demo_request,
			"status": request_doc.status if request_doc else "",
			"customer_requirements": request_doc.customer_requirements if request_doc else "",
			"business_process_requirements": request_doc.business_process_requirements if request_doc else "",
			"priority": request_doc.priority if request_doc else "",
			"lead": request_doc.lead if request_doc else "",
		},
		"customer": {
			"customer": ds.customer,
			"lead": ds.lead,
			"contact_person": ds.contact_person,
			"contact_number": ds.contact_number,
			"email": ds.email,
			"company": ds.company,
		},
		"team": {
			"sales_person": ds.sales_person,
			"functional_consultant": ds.functional_consultant,
			"consultant_name": consultant.consultant_name if consultant else "",
			"consultant_specialization": consultant.specialization if consultant else "",
			"consultant_email": consultant.email if consultant else "",
		},
		"template": {
			"name": ds.demo_template,
			"template_name": frappe.db.get_value("Functional Demo Template", ds.demo_template, "template_name")
			if ds.demo_template
			else "",
			"sections": [{"section": s.section, "content": s.content} for s in ds.template_sections],
			"snapshot_date": ds.template_snapshot_date,
		},
		"can_write": can_write,
		# consultant-action rights (start / complete / final result) and the
		# narrower cancel right - the execution screen shows buttons accordingly
		"can_execute": can_execute_session_action(ds),
		"can_cancel": can_cancel_session(ds),
	}


@frappe.whitelist()
def start_demo_session(demo_session=None):
	ds = _get_session(demo_session)
	ds.start_demo()
	party, consultant = _party_and_consultant(ds)
	frappe.msgprint(
		_("Demo {0} for {1} started with {2}. Good luck!").format(
			ds.name, party or "-", consultant or ds.functional_consultant or "-"
		)
	)
	return {"demo_status": ds.demo_status}


@frappe.whitelist()
def complete_demo_session(demo_session=None, feedback=None):
	"""Complete a demo and record customer feedback (including final result)."""
	ds = _get_session(demo_session)
	ds.complete_demo(feedback or {})
	party, _consultant = _party_and_consultant(ds)
	frappe.msgprint(_("Demo {0} for {1} completed and feedback recorded.").format(ds.name, party or "-"))
	return {
		"demo_status": ds.demo_status,
		"final_result": ds.final_result,
		"request_status": frappe.db.get_value("Demo Request", ds.demo_request, "status"),
	}


@frappe.whitelist()
def cancel_demo_session(demo_session=None, reason=None):
	ds = _get_session(demo_session)
	ds.cancel_demo(reason)
	party, _consultant = _party_and_consultant(ds)
	frappe.msgprint(_("Demo {0} for {1} cancelled.").format(ds.name, party or "-"))
	return {"demo_status": ds.demo_status}


@frappe.whitelist()
def reschedule_demo_session(demo_session=None, scheduled_date=None, start_time=None, end_time=None, meeting_link=None):
	if not scheduled_date:
		frappe.throw(_("Please select a new date."))
	ds = _get_session(demo_session)
	ds.reschedule_demo(scheduled_date, start_time, end_time, meeting_link)
	party, consultant = _party_and_consultant(ds)
	frappe.msgprint(
		_("Demo {0} rescheduled to {1}{2}{3}.").format(
			ds.name,
			_fmt_date(scheduled_date),
			" for " + party if party else "",
			" with " + consultant if consultant else "",
		)
	)
	return {"demo_status": ds.demo_status}


@frappe.whitelist()
def create_follow_up_from_session(demo_session=None, follow_up_date=None, next_action=None, assigned_to=None):
	"""Create a follow-up directly from a completed demo session."""
	if not follow_up_date:
		frappe.throw(_("Please select a follow-up date."))
	if not is_sales():
		frappe.throw(_("Only the sales team can create follow-ups."), frappe.PermissionError)
	ds = _get_session(demo_session)
	fu = ds.create_follow_up(follow_up_date, next_action, assigned_to)
	party, _consultant = _party_and_consultant(ds)
	frappe.msgprint(
		_("Follow-up {0} created for {1}.").format(fu.name, party or ds.customer or ds.demo_request)
	)
	return {"follow_up": fu.name}


# ---------------------------------------------------------------------------
# Consultant Drive (shared consultant-only file library)
# ---------------------------------------------------------------------------


def _safe_filename(filename):
	"""Make an uploaded filename safe for URLs: whitespace and characters like
	#, %, & or quotes break attachment links in the desk, so collapse them to
	dashes and keep only letters, digits, dot, dash and underscore."""
	import re

	name = re.sub(r"\s+", "-", filename or "").strip(" .-_")
	name = re.sub(r"[^A-Za-z0-9._-]", "-", name)
	return name or "file"


def _guard_consultant_drive():
	"""The Drive is consultant-only: Functional Consultant / Functional Team
	Manager (and System Manager / Administrator). Sales roles never get in."""
	if not is_functional():
		frappe.throw(_("Only the consultant team can access the Drive."), frappe.PermissionError)


@frappe.whitelist()
def consultant_drive_upload(title=None, description=None, file=None):
	"""Upload a file to the shared consultant Drive (multipart POST)."""
	_guard_consultant_drive()
	if not title:
		frappe.throw(_("Please give the file a title."))
	filedata = None
	if file is not None:
		# passed as a base64/JSON string by some clients
		filedata = file
	else:
		files = getattr(frappe.request, "files", None) or {}
		filedata = files.get("file")
	if not filedata or not getattr(filedata, "filename", None):
		frappe.throw(_("Please choose a file to upload."))

	# Create the Drive entry first (its hash name is required to attach the
	# File record). The whole request is one transaction, so if anything below
	# fails the entry is rolled back and never appears file-less.
	doc = frappe.new_doc("Consultant Drive File")
	doc.title = title
	doc.description = description or ""
	doc.uploaded_by = frappe.session.user
	doc.insert()

	# Store the bytes in a private File record attached to this Drive entry.
	# Built directly instead of via frappe.utils.file_manager.save_file because
	# that helper's signature (dt/dn) differs across Frappe versions. The
	# filename is sanitized (no spaces/special chars) so the desk attachment
	# link resolves and opens the file instead of showing the raw path.
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": _safe_filename(filedata.filename),
			"content": filedata.stream.read(),
			"is_private": 1,
			"attached_to_doctype": "Consultant Drive File",
			"attached_to_name": doc.name,
		}
	).insert(ignore_permissions=True)

	frappe.db.set_value(
		"Consultant Drive File",
		doc.name,
		{"file": file_doc.file_url, "file_size": file_doc.file_size or 0},
		update_modified=True,
	)

	frappe.msgprint(_("{0} uploaded to the Drive.").format(title))
	return {"name": doc.name, "file_url": doc.file}


@frappe.whitelist()
def consultant_drive_download(name=None):
	"""Serve a Drive file for download (GET link from the portal)."""
	_guard_consultant_drive()
	if not name:
		frappe.throw(_("File is missing."))
	doc = frappe.get_doc("Consultant Drive File", name)
	file_doc = frappe.get_doc("File", {"file_url": doc.file})
	content = file_doc.get_content()
	frappe.response.filename = file_doc.file_name or "download"
	frappe.response.filecontent = content
	frappe.response.type = "download"


@frappe.whitelist()
def consultant_drive_delete(name=None):
	"""Delete a file from the shared consultant Drive."""
	_guard_consultant_drive()
	if not name:
		frappe.throw(_("File is missing."))
	doc = frappe.get_doc("Consultant Drive File", name)
	title = doc.title
	doc.delete()  # on_trash also removes the backing File record
	frappe.msgprint(_("{0} removed from the Drive.").format(title))
	return True


@frappe.whitelist()
def set_session_final_result(demo_session=None, result=None):
	"""Close a demo session with a final result (Converted / Not Interested / Closed / Pending).

	Arguments are optional so a client that fires the call without a value gets
	a clear popup instead of a TypeError 500."""
	if not result:
		frappe.throw(_("Please choose a final result."))
	ds = _get_session(demo_session)
	ds.set_final_result(result)
	party, _consultant = _party_and_consultant(ds)
	frappe.msgprint(_("Demo {0} for {1} marked as {2}.").format(ds.name, party or "-", result))
	return {"final_result": ds.final_result}


@frappe.whitelist()
def get_my_demo_sessions(demo_status=None):
	"""Sessions visible to the current user (permission filters apply)."""
	filters = {}
	if demo_status:
		filters["demo_status"] = demo_status
	return frappe.get_list(
		"Demo Session",
		filters=filters,
		fields=["name", "customer", "scheduled_date", "start_time", "demo_status", "functional_consultant"],
		order_by="scheduled_date desc",
		limit_page_length=50,
	)


# ---------------------------------------------------------------------------
# Demo feedback (Feedback page - shared by the portal and the desk)
# ---------------------------------------------------------------------------

def get_demo_feedback_data():
	"""Return the feedback recorded against demos (completed sessions), newest
	first. Every entry carries a template name (Law Management, Hospitality,
	Retail & Supermarket, ...) so the Feedback page can group / filter by
	template. The name comes from the session's own Interested Template
	(chosen when the demo was scheduled), falling back to the Demo Request's
	Interested Template and then the Demo Template - so a session never falls
	through to "No Template" when the request recorded the customer's interest.

	Single source of truth for the portal Feedback page (/feedback) and the desk
	demo-feedback page (/app/demo-feedback), so both sides always show the same
	data. ignore_permissions: feedback is shared reference data for the whole
	sales + functional team - both pages are already gated by role."""
	sessions = frappe.get_all(
		"Demo Session",
		filters={"demo_status": ["in", ["Completed", "Follow-up Required", "Closed"]]},
		fields=[
			"name", "demo_request", "customer", "lead", "scheduled_date", "completed_on",
			"overall_feedback", "interested", "requirements_met", "additional_requirements",
			"requested_changes", "follow_up_required", "follow_up_date", "next_action",
			"consultant_remarks", "final_result", "functional_consultant", "sales_person",
			"demo_template", "interested_module",
		],
		order_by="completed_on desc",
		ignore_permissions=True,
		limit_page_length=1000,
	) or []

	# template display names (bulk) - the session stores the template doc name,
	# the Feedback page shows the friendly Template Name (Law, Hospitality, ...)
	template_ids = {s.demo_template for s in sessions if s.demo_template}
	template_names = {}
	if template_ids:
		for t in frappe.get_all(
			"Functional Demo Template",
			filters={"name": ["in", list(template_ids)]},
			fields=["name", "template_name"],
			ignore_permissions=True,
		):
			template_names[t.name] = t.template_name or t.name

	# template fallback: the Demo Request's "Interested Template" (Law
	# Management, Hospitality, Retail & Supermarket, ...). Many sessions - e.g.
	# every one created from the portal - have no Demo Template linked, but the
	# request always records what the customer was interested in, so feedback
	# can still be grouped under a real, meaningful template name instead of
	# falling through to "No Template".
	request_ids = {s.demo_request for s in sessions if s.demo_request}
	request_templates = {}
	if request_ids:
		for r in frappe.get_all(
			"Demo Request",
			filters={"name": ["in", list(request_ids)]},
			fields=["name", "interested_module"],
			ignore_permissions=True,
		):
			if r.interested_module:
				request_templates[r.name] = r.interested_module

	# per-session feedback rows (child table, fetched in bulk)
	items_map = {}
	session_names = [s.name for s in sessions]
	if session_names:
		for row in frappe.get_all(
			"Demo Feedback Item",
			filters={"parent": ["in", session_names]},
			fields=["parent", "item_type", "description"],
			order_by="idx asc",
			ignore_permissions=True,
		):
			items_map.setdefault(row.parent, []).append(
				{"item_type": row.item_type or "Question", "description": row.description or ""}
			)

	# consultant display names (bulk)
	consultant_ids = {s.functional_consultant for s in sessions if s.functional_consultant}
	consultant_names = {}
	if consultant_ids:
		for c in frappe.get_all(
			"Functional Consultant",
			filters={"name": ["in", list(consultant_ids)]},
			fields=["name", "consultant_name"],
			ignore_permissions=True,
		):
			consultant_names[c.name] = c.consultant_name

	# sales person display names (bulk) - resolve User email to full name
	sales_person_ids = {s.sales_person for s in sessions if s.sales_person}
	sales_person_names = {}
	if sales_person_ids:
		for u in frappe.get_all(
			"User",
			filters={"name": ["in", list(sales_person_ids)]},
			fields=["name", "full_name", "email"],
			ignore_permissions=True,
		):
			sales_person_names[u.name] = u.full_name or u.email or u.name

	out = []
	for s in sessions:
		out.append(
			{
				"name": s.name,
				"customer": s.customer or "-",
				"sales_person": sales_person_names.get(s.sales_person) or s.sales_person or "-",
				"date": (
					frappe.utils.format_datetime(s.completed_on or s.scheduled_date, "dd MMM yyyy, hh:mm a")
					if (s.completed_on or s.scheduled_date)
					else "-"
				),
				"overall_feedback": s.overall_feedback or "",
				"interested": s.interested or "",
				"requirements_met": s.requirements_met or "",
				"feedback_items": items_map.get(s.name, []),
				"consultant": (
					consultant_names.get(s.functional_consultant)
					or s.functional_consultant
					or "-"
				),
				"final_result": s.final_result or "",
				"template": (
					s.interested_module
					or request_templates.get(s.demo_request)
					or template_names.get(s.demo_template)
					or "No Template"
				),
			}
		)
	return out


@frappe.whitelist()
def get_demo_feedback():
	"""Return the demo feedback entries (Feedback page - portal & desk)."""
	return get_demo_feedback_data()


# ---------------------------------------------------------------------------
# Portal notifications (bell in the portal topbar - in-app alerts)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_portal_notifications(limit=8):
	"""Recent in-app notifications (Notification Log) for the current user, used
	by the notification bell in the portal topbar."""
	user = frappe.session.user
	if not user or user == "Guest":
		return {"unread": 0, "items": []}
	# ignore_permissions: a user must always see their own notifications even
	# if their role has no generic read on the Notification Log doctype - the
	# desk bell does the same.
	items = frappe.get_all(
		"Notification Log",
		filters={"for_user": user},
		fields=["name", "subject", "type", "document_type", "document_name", "creation", "read"],
		order_by="creation desc",
		limit_page_length=int(limit) or 8,
		ignore_permissions=True,
	) or []
	unread = frappe.db.count("Notification Log", {"for_user": user, "read": 0})
	out = []
	for it in items:
		out.append(
			{
				"name": it.name,
				"subject": it.subject or "",
				"type": it.type or "",
				"document_type": it.document_type or "",
				"document_name": it.document_name or "",
				"creation": frappe.utils.pretty_date(it.creation) if it.creation else "",
				"read": 1 if it.read else 0,
			}
		)
	return {"unread": unread, "items": out}


@frappe.whitelist()
def mark_portal_notifications_read():
	"""Mark all of the current user's in-app notifications as read (bell action)."""
	frappe.db.sql(
		"update `tabNotification Log` set `read` = 1 where `for_user` = %s and `read` = 0",
		frappe.session.user,
	)
	frappe.db.commit()
	return True


# ---------------------------------------------------------------------------
# Web Push (service worker) - OS-level popups with sound, even on other pages
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_push_config():
	"""Return whether Web Push is configured on this site plus the public VAPID
	key (safe to expose) so the browser can subscribe. When VAPID keys are not
	configured the client silently skips Web Push and the in-app popups still
	cover everything."""
	public_key = frappe.conf.get("vapid_public_key") or ""
	private_key = frappe.conf.get("vapid_private_key") or ""
	return {
		"enabled": bool(public_key and private_key),
		"public_key": public_key,
		"sound": "/chime.wav",
	}


@frappe.whitelist()
def subscribe_push(subscription=None):
	"""Save the current user's browser Web Push subscription (one per endpoint).

	Always scoped to the logged-in user - a user can never register a
	subscription for anyone else. Re-subscribing to the same endpoint updates
	the stored subscription instead of duplicating it."""
	import json

	if not subscription:
		return {"ok": False}
	if isinstance(subscription, str):
		try:
			subscription = json.loads(subscription)
		except Exception:
			return {"ok": False}
	endpoint = (subscription or {}).get("endpoint", "")
	if not endpoint:
		return {"ok": False}

	payload = json.dumps(subscription)
	existing = frappe.db.get_value(
		"Web Push Subscription",
		{"user": frappe.session.user, "endpoint": endpoint},
		"name",
	)
	if existing:
		frappe.db.set_value("Web Push Subscription", existing, "subscription", payload)
	else:
		doc = frappe.new_doc("Web Push Subscription")
		doc.user = frappe.session.user
		doc.endpoint = endpoint
		doc.subscription = payload
		doc.enabled = 1
		doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def unsubscribe_push(endpoint=None):
	"""Remove the current user's Web Push subscription for this endpoint (used
	when the browser drops it or the user disables notifications)."""
	if not endpoint:
		return {"ok": False}
	name = frappe.db.get_value(
		"Web Push Subscription",
		{"user": frappe.session.user, "endpoint": endpoint},
		"name",
	)
	if name:
		frappe.db.delete("Web Push Subscription", name)
		frappe.db.commit()
	return {"ok": True}


# ---------------------------------------------------------------------------
# Portal actions (used by the Sales / Functional / Manager portal pages)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_lead(lead_name=None, company_name=None, email=None, phone=None, status=None, source=None, notes=None):
	"""Create a Lead from the Sales Portal - the record lives in ERPNext but the
	sales user never has to leave the portal to create it.

	Arguments are optional so a client that fires the call without a value gets
	a clear popup instead of a TypeError 500."""
	lead_name = (lead_name or "").strip()
	if not lead_name:
		frappe.throw(_("Please enter a sales person name."), title=_("Name Required"))

	# Keep the lead list clean: when a Lead with the same email (or, if no
	# email was given, the same company) already exists, reuse it instead of
	# creating a duplicate - the portal shows the note as a success toast.
	company_name = (company_name or "").strip()
	email = (email or "").strip()
	existing = None
	if email:
		existing = frappe.db.get_value("Lead", {"email_id": email}, "name")
	if not existing and company_name:
		existing = frappe.db.get_value("Lead", {"company_name": company_name}, "name")
	if existing:
		return {
			"name": existing,
			"note": _("A sales person with the same email or company already exists, so {0} was reused instead of creating a duplicate.").format(existing),
		}

	doc = frappe.new_doc("Lead")
	doc.lead_name = lead_name
	if company_name:
		doc.company_name = company_name
	doc.email_id = email
	doc.mobile_no = (phone or "").strip()
	doc.status = status or "Lead"
	if source:
		doc.source = source
	doc.notes = notes
	# insert() (not ignore_permissions) so the standard ERPNext role checks
	# apply - the Sales User role already has create rights on Lead. owner and
	# lead_owner default to the session user, so the lead shows up under My Leads.
	doc.insert()

	# Link a Contact carrying the email/phone so the portal's auto-fetch
	# (get_lead_details) can pre-fill demo requests from this lead later.
	try:
		contact = frappe.new_doc("Contact")
		contact.first_name = lead_name
		contact.is_primary_contact = 1
		contact.append(
			"links",
			{"link_doctype": "Lead", "link_name": doc.name, "link_title": company_name or lead_name},
		)
		if doc.email_id:
			contact.email_id = doc.email_id
		if doc.mobile_no:
			contact.mobile_no = doc.mobile_no
		contact.insert(ignore_permissions=True)
	except Exception:
		# the lead is already created - a missing Contact must never block it
		frappe.log_error(
			title=_("Could not create Contact for new sales person {0}").format(doc.name),
			message=frappe.get_traceback(),
		)

	# NOTE: never call frappe.msgprint() here - if anything below raised, Frappe
	# would promote the msgprint text to the error message and hide the real
	# failure. The portal shows its own success toast from the response.
	return {"name": doc.name}


@frappe.whitelist()
def create_demo_request(customer=None, company=None, contact_person=None, contact_number=None, email=None, interested_module=None, customer_requirements=None, business_process_requirements=None, priority="Medium", preferred_demo_date=None, preferred_demo_time=None, demo_type=None, sales_remarks=None, functional_consultant=None):
	"""Create a Demo Request from the Sales Portal web form.

	The sales_person is always auto-set to the logged-in user — no dropdown needed.
	The 'lead' field is kept for backwards compatibility but is no longer
	sent from the form.
	"""
	from functional_demo.sales_demo.doctype.demo_request.demo_request import change_status

	# Auto-set sales_person to the logged-in user
	sales_person = frappe.session.user

	# A party (Customer/Lead) and contact details are OPTIONAL - the sales team
	# can create a request with only a Functional Consultant and fill in the
	# customer details later (their workflow is consultant-first and the site
	# may have no CRM records yet).

	# Free-typed customer names are auto-created as real Customer records (they
	# then appear in the desk too); if that fails for any reason we fall back to
	# a contact-only request instead of blocking the sales user.
	if customer and not frappe.db.exists("Customer", customer):
		try:
			customer, created_contact = _ensure_customer(
				customer, contact_person, contact_number, email
			)
			if created_contact:
				contact_person = created_contact
		except Exception:
			frappe.log_error(
				title=_("Auto-create Leads failed: {0}").format(customer),
				message=frappe.get_traceback(),
			)
			customer = ""

	# With the new Manager Review flow, the sales user creates the request
	# WITHOUT a consultant. The consultant is assigned later by the Functional
	# Team Manager after reviewing the request.  If a consultant is explicitly
	# provided (e.g. a manager creating a request directly), use it; otherwise
	# leave it empty so the request goes to Manager Review.
	auto_assigned_note = ""
	extra_remarks = []
	if contact_person and not frappe.db.exists("Contact", contact_person):
		extra_remarks.append(_("Contact person: {0}").format(contact_person))
		contact_person = ""
	if company and not frappe.db.exists("Company", company):
		extra_remarks.append(_("Company: {0}").format(company))
		company = ""

	doc = frappe.new_doc("Demo Request")
	doc.customer = customer
	doc.sales_person = sales_person  # auto-set to logged-in user
	doc.company = company
	doc.contact_person = contact_person
	doc.contact_number = contact_number
	doc.email = email
	doc.interested_module = interested_module
	doc.customer_requirements = customer_requirements
	doc.business_process_requirements = business_process_requirements
	# Priority rule: "Auto" (the portal default) computes the priority from the
	# customer tier; an explicit choice is always respected.
	doc.priority = suggested_priority("", customer) if priority in (None, "", "Auto") else priority
	doc.preferred_demo_date = preferred_demo_date
	doc.preferred_demo_time = preferred_demo_time
	doc.demo_type = demo_type
	doc.sales_remarks = "\n".join([r for r in [sales_remarks] + extra_remarks if r]) or None
	doc.functional_consultant = functional_consultant
	# fetch_from does NOT run on API inserts - resolve the consultant's user so
	# the 'Consultant Assigned' / 'Demo Scheduled' notifications can reach them
	doc.consultant_user = frappe.db.get_value(
		"Functional Consultant", functional_consultant, "user"
	)
	doc.insert()  # respects role permissions; sales_person defaults to the session user

	# ALL demo requests from the sales portal go to Manager Review.
	# The Functional Team Manager reviews and assigns the consultant.
	try:
		change_status(doc, "Requested")
		# Reload to pick up the new workflow_state after the first change_status
		doc = frappe.get_doc("Demo Request", doc.name)
		current = doc.get("workflow_state") or doc.get("status") or "Draft"
		if current == "Requested":
			change_status(doc, "Manager Review")
	except Exception:
		# the request is still created; the sales team can move it from the desk
		frappe.log_error(
			title=_("Portal: Demo Request could not be moved through workflow"),
			message=frappe.get_traceback(),
		)

	return {"name": doc.name, "note": auto_assigned_note or ""}


@frappe.whitelist()
def assign_to_manager(demo_request=None):
	"""Sales user sends a Demo Request to the Functional Team Manager for
	review. The request moves to 'Manager Review' state so the manager can
	pick a consultant.

	Arguments are optional so a client that fires the call without a value
	gets a clear popup instead of a TypeError 500."""
	if not demo_request:
		frappe.throw(
			_("Demo Request is missing. Please refresh the page and try again."),
			title=_("Missing Request"),
		)

	doc = frappe.get_doc("Demo Request", demo_request)
	frappe.has_permission("Demo Request", "write", doc=doc, throw=True)

	current_state = doc.get("workflow_state") or doc.get("status") or "Draft"
	if current_state == "Manager Review":
		frappe.msgprint(_("{0} is already in Manager Review.").format(demo_request))
		return {"status": doc.get("status") or doc.get("workflow_state")}

	from functional_demo.sales_demo.doctype.demo_request.demo_request import change_status

	try:
		if current_state in (None, "", "Draft"):
			doc = change_status(doc, "Requested")
		doc = frappe.get_doc("Demo Request", demo_request)
		if (doc.get("workflow_state") or doc.get("status")) == "Requested":
			doc = change_status(doc, "Manager Review")
	except Exception:
		frappe.log_error(
			title=_("Portal: Could not send Demo Request to Manager Review"),
			message=frappe.get_traceback(),
		)
		frappe.throw(
			_("Could not send the request to the manager. Please try again or use the desk form."),
			title=_("Send Failed"),
		)

	frappe.msgprint(_("{0} sent to Functional Team Manager for review.").format(demo_request))
	return {"status": doc.get("status") or doc.get("workflow_state")}


@frappe.whitelist()
def assign_consultant(demo_request=None, consultant=None):
	"""Assign (or reassign) a Functional Consultant on a Demo Request and move
	the workflow to 'Assigned'. This is used by the Functional Team Manager
	(after reviewing the request) and by Sales Managers.

	Both arguments are optional so a client that fires the call without a value
	gets a clear popup instead of a TypeError 500."""
	if not demo_request:
		frappe.throw(
			_("Demo Request is missing. Please refresh the page and try again."),
			title=_("Missing Request"),
		)
	if not consultant:
		frappe.throw(_("Please select a Functional Consultant."))

	doc = frappe.get_doc("Demo Request", demo_request)
	frappe.has_permission("Demo Request", "write", doc=doc, throw=True)

	current_state = doc.get("workflow_state") or doc.get("status") or "Draft"
	doc.functional_consultant = consultant
	# fetch_from does NOT run on API saves - keep consultant_user in sync so the
	# 'Consultant Assigned' / 'Consultant Reassigned' notifications can reach them
	doc.consultant_user = frappe.db.get_value("Functional Consultant", consultant, "user")
	doc.save()  # validate runs: only Active consultants, reassignment flag, ToDo + notifications

	from functional_demo.sales_demo.doctype.demo_request.demo_request import change_status

	if current_state in (None, "", "Draft", "Requested", "Manager Review"):
		doc = change_status(doc, "Assigned", ignore_permissions=True)

	# Notify the sales person that their demo request has been assigned
	# to a consultant - they need to know the request is being actioned.
	sales_person = doc.get("sales_person")
	if sales_person and sales_person != frappe.session.user:
		consultant_name = frappe.db.get_value(
			"Functional Consultant", consultant, "consultant_name"
		) or consultant
		customer = frappe.db.get_value("Customer", doc.customer, "customer_name") if doc.customer else (doc.lead or "-")
		create_notification(
			sales_person,
			_("Demo Request {0} ({1}) has been assigned to consultant {2}.").format(
				demo_request, customer, consultant_name
			),
			"Demo Request",
			demo_request,
		)

	frappe.msgprint(_("Functional Consultant assigned to {0}.").format(demo_request))
	return {"status": doc.get("status") or doc.get("workflow_state")}


# ---------------------------------------------------------------------------
# Consultant profile linking (used by the Functional portal 'Link my user')
# ---------------------------------------------------------------------------

# Specializations come from the doctype itself so this list can never drift
SPECIALIZATIONS = [
	s
	for s in (
		frappe.get_meta("Functional Consultant").get_field("specialization").options or ""
	).split("\n")
	if s
]


def _guard_consultant_manager():
	"""Only Functional Team Managers / System Managers may manage consultant
	profiles (mirrors the Functional Consultant doctype permissions)."""
	if not can_manage_consultants():
		frappe.throw(
			_("Only Functional Team Managers can manage consultant profiles."),
			frappe.PermissionError,
		)


@frappe.whitelist()
def create_consultant_profile(
	user=None,
	consultant_name=None,
	specialization=None,
	templates=None,
	experience_years=None,
	availability=None,
	email=None,
	notes=None,
):
	"""Create a Functional Consultant profile linked to a User.
	The doctype's on_update hook grants the Functional Consultant role, so the
	profile exists in the desk (ERPNext) exactly like one created there.

	The user argument is optional so a client that fires the call without a
	value (e.g. a stale cached page) gets a clear popup instead of a TypeError
	500 from the framework."""
	_guard_consultant_manager()
	if not user:
		# Belt & braces: a stale cached page may fire this API without a value.
		# The 'Link my user' button links the person who is clicking, so fall
		# back to the session user instead of showing an error popup.
		user = frappe.session.user
	if not user:
		frappe.throw(
			_("Please select a user to link, then try again. If the page is stale, refresh it (Ctrl+Shift+R) and retry."),
			title=_("User Required"),
		)
	if user in ("Guest", "Administrator"):
		frappe.throw(_("This user cannot be linked to a consultant profile."))
	if not frappe.db.exists("User", user):
		frappe.throw(_("User {0} does not exist.").format(user))
	if not frappe.db.get_value("User", user, "enabled"):
		frappe.throw(_("User {0} is disabled.").format(user))
	if frappe.db.get_value("Functional Consultant", {"user": user}, "name"):
		frappe.throw(
			_("User {0} already has a consultant profile.").format(user),
			title=_("Already Linked"),
		)

	full_name = frappe.db.get_value("User", user, "full_name") or user
	if not consultant_name:
		consultant_name = full_name
	if specialization and specialization not in SPECIALIZATIONS:
		frappe.throw(_("Invalid specialization."))

	# templates = the multi-select template list (Law Management, Hospitality, ...)
	# saved into the erpnext_modules child table so matching against a demo
	# request's interested_module works. A single specialization is still
	# honoured for backward compatibility with the desk-side form.
	template_list = templates or []
	if isinstance(template_list, str):
		template_list = [template_list]
	if not template_list and specialization:
		template_list = [specialization]

	doc = frappe.new_doc("Functional Consultant")
	doc.consultant_name = consultant_name
	doc.user = user
	# specialization is a desk-side Select with its own options (Accounting,
	# CRM, ...) - only set it when the caller explicitly passes a valid one;
	# templates are what drives consultant-to-demo matching.
	doc.specialization = specialization or ""
	doc.status = "Active"
	doc.availability = availability or "Available"
	for t in template_list:
		doc.append("erpnext_modules", {"module": t})
	if experience_years:
		try:
			doc.experience_years = int(experience_years)
		except (TypeError, ValueError):
			frappe.throw(_("Experience must be a whole number of years."))
	if email:
		doc.email = email
	if notes:
		doc.notes = notes
	doc.insert(ignore_permissions=True)  # role guard enforced above

	frappe.msgprint(
		_("Consultant profile {0} created for {1}. The Functional Consultant role has been granted.").format(
			doc.name, full_name
		)
	)
	return {"name": doc.name, "consultant_name": doc.consultant_name}


@frappe.whitelist()
def update_follow_up(follow_up=None, status=None, outcome=None, remarks=None, next_action=None, discussion_note=None, follow_up_date=None):
	"""Update a Demo Follow Up from the portal: complete it, record the outcome,
	reschedule it, and optionally append a discussion note (creates a Follow Up Note row).

	The argument is optional so a client that fires the call without a value
	gets a clear popup instead of a TypeError 500."""
	if not follow_up:
		frappe.throw(
			_("Follow-up is missing. Please refresh the page and try again."),
			title=_("Missing Follow-up"),
		)
	doc = frappe.get_doc("Demo Follow Up", follow_up)
	frappe.has_permission("Demo Follow Up", "write", doc=doc, throw=True)

	if status:
		doc.status = status
	if outcome:
		doc.outcome = outcome
	if remarks:
		doc.remarks = remarks
	if next_action:
		doc.next_action = next_action
	if follow_up_date:
		doc.follow_up_date = follow_up_date
	if discussion_note:
		doc.add_discussion_note(discussion_note)
	doc.save()

	frappe.msgprint(_("Follow-up {0} updated.").format(follow_up))
	return {"status": doc.status, "outcome": doc.outcome}
