# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Whitelisted API endpoints used by the Demo Execution screen and quick actions."""

import frappe
from frappe import _

from functional_demo.portal import can_manage_consultants
from functional_demo.sales_demo.doctype.demo_request.demo_request import (
	change_status,
	get_primary_contact,
)
from functional_demo.sales_demo.doctype.demo_session.demo_session import (
	create_calendar_event,
)


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
	return {
		"contact_person": lead_doc.lead_name or "",
		"contact_number": lead_doc.mobile_no or lead_doc.phone or "",
		"email": lead_doc.email_id or "",
	}


@frappe.whitelist()
def get_available_consultants(module=None, include_inactive=0):
	"""List Functional Consultants (active by default), optionally filtered by
	an ERPNext module they specialize in. Also returns their current workload."""
	filters = {"status": "Active"} if not include_inactive else {}
	consultants = frappe.get_all(
		"Functional Consultant",
		filters=filters,
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


@frappe.whitelist()
def get_consultant_templates(consultant=None):
	"""List active demo templates belonging to a Functional Consultant."""
	if not consultant:
		return []
	return frappe.get_all(
		"Functional Demo Template",
		filters={"functional_consultant": consultant, "is_active": 1},
		fields=["name", "template_name", "erpnext_module", "business_area", "demo_objective"],
		order_by="template_name asc",
	)


# ---------------------------------------------------------------------------
# Demo Request quick actions
# ---------------------------------------------------------------------------

@frappe.whitelist()
def schedule_demo(demo_request=None, scheduled_date=None, start_time=None, end_time=None, meeting_link=None):
	"""Schedule (or reschedule) a demo for a Demo Request and create a Demo Session.

	Arguments are optional so a client that fires the call without a value gets
	a clear popup instead of a TypeError 500."""
	if not demo_request:
		frappe.throw(
			_("Demo Request is missing. Please refresh the page and try again."),
			title=_("Missing Request"),
		)
	if not scheduled_date:
		frappe.throw(_("Please select a scheduled date."))

	dr = frappe.get_doc("Demo Request", demo_request)
	frappe.has_permission("Demo Request", "write", doc=dr, throw=True)

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
			ds.reschedule_count = int(ds.reschedule_count or 0) + 1
			ds.flags.rescheduling = True
			ds.save(ignore_permissions=True)
			frappe.msgprint(_("Demo Session {0} rescheduled to {1}.").format(ds.name, scheduled_date))
		else:
			ds = frappe.new_doc("Demo Session")
			ds.demo_request = dr.name
			ds.scheduled_date = scheduled_date
			ds.start_time = start_time
			ds.end_time = end_time
			ds.meeting_link = meeting_link
			ds.insert(ignore_permissions=True)
			frappe.msgprint(_("Demo Session {0} scheduled for {1}.").format(ds.name, scheduled_date))

		# keep the Demo Request in sync (fields first, then the workflow move)
		dr.preferred_demo_date = scheduled_date
		dr.preferred_demo_time = start_time or dr.preferred_demo_time
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
	change_status(dr, "Follow-up Required", ignore_permissions=True)

	frappe.msgprint(_("Follow-up {0} created. A task has been assigned to {1}.").format(fu.name, fu.assigned_to))
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
	frappe.msgprint(_("Demo Request {0} marked as {1}.").format(dr.name, result))
	return dr.status


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
	ds = frappe.get_doc("Demo Session", demo_session)
	frappe.has_permission("Demo Session", "read", doc=ds, throw=True)

	request_doc = frappe.get_doc("Demo Request", ds.demo_request) if ds.demo_request else None
	consultant = None
	if ds.functional_consultant:
		consultant = frappe.db.get_value(
			"Functional Consultant",
			ds.functional_consultant,
			["consultant_name", "user", "specialization", "availability", "email"],
			as_dict=True,
		)

	can_write = frappe.has_permission("Demo Session", "write", doc=ds)

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
	}


@frappe.whitelist()
def start_demo_session(demo_session=None):
	ds = _get_session(demo_session)
	ds.start_demo()
	frappe.msgprint(_("Demo Session {0} started. Good luck!").format(ds.name))
	return {"demo_status": ds.demo_status}


@frappe.whitelist()
def complete_demo_session(demo_session=None, feedback=None):
	"""Complete a demo and record customer feedback."""
	ds = _get_session(demo_session)
	ds.complete_demo(feedback or {})
	frappe.msgprint(_("Demo Session {0} completed and feedback recorded.").format(ds.name))
	return {
		"demo_status": ds.demo_status,
		"request_status": frappe.db.get_value("Demo Request", ds.demo_request, "status"),
	}


@frappe.whitelist()
def cancel_demo_session(demo_session=None, reason=None):
	ds = _get_session(demo_session)
	ds.cancel_demo(reason)
	frappe.msgprint(_("Demo Session {0} cancelled.").format(ds.name))
	return {"demo_status": ds.demo_status}


@frappe.whitelist()
def reschedule_demo_session(demo_session=None, scheduled_date=None, start_time=None, end_time=None, meeting_link=None):
	if not scheduled_date:
		frappe.throw(_("Please select a new date."))
	ds = _get_session(demo_session)
	ds.reschedule_demo(scheduled_date, start_time, end_time, meeting_link)
	frappe.msgprint(_("Demo Session {0} rescheduled to {1}.").format(ds.name, scheduled_date))
	return {"demo_status": ds.demo_status}


@frappe.whitelist()
def create_follow_up_from_session(demo_session=None, follow_up_date=None, next_action=None, assigned_to=None):
	"""Create a follow-up directly from a completed demo session."""
	if not follow_up_date:
		frappe.throw(_("Please select a follow-up date."))
	ds = _get_session(demo_session)
	fu = ds.create_follow_up(follow_up_date, next_action, assigned_to)
	frappe.msgprint(_("Follow-up {0} created.").format(fu.name))
	return {"follow_up": fu.name}


@frappe.whitelist()
def set_session_final_result(demo_session=None, result=None):
	"""Close a demo session with a final result (Converted / Not Interested / Closed / Pending).

	Arguments are optional so a client that fires the call without a value gets
	a clear popup instead of a TypeError 500."""
	if not result:
		frappe.throw(_("Please choose a final result."))
	ds = _get_session(demo_session)
	ds.set_final_result(result)
	frappe.msgprint(_("Demo Session {0} marked as {1}.").format(ds.name, result))
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
# Portal actions (used by the Sales / Functional / Manager portal pages)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_demo_request(customer=None, lead=None, company=None, contact_person=None, contact_number=None, email=None, interested_module=None, customer_requirements=None, business_process_requirements=None, priority="Medium", preferred_demo_date=None, preferred_demo_time=None, demo_type=None, sales_remarks=None, functional_consultant=None):
	"""Create a Demo Request from the Sales Portal web form."""
	from functional_demo.sales_demo.doctype.demo_request.demo_request import change_status

	# A party (customer or lead) is required - the demo is for someone.
	# The message tells the user exactly what to do so the popup is never cryptic.
	if not customer and not lead:
		frappe.throw(
			_("Please select a Customer or a Lead before creating the demo request. "
			  "Type in the Customer (or Lead) box and pick a suggestion from the list, then try again."),
			title=_("Customer or Lead Required"),
		)

	# The party must be a real record - a free-typed name is not enough.
	if customer and not frappe.db.exists("Customer", customer):
		frappe.throw(
			_("Customer \"{0}\" was not found. Please pick a customer from the suggestions list.").format(
				customer
			),
			title=_("Customer Not Found"),
		)
	if lead and not frappe.db.exists("Lead", lead):
		frappe.throw(
			_("Lead \"{0}\" was not found. Please pick a lead from the suggestions list.").format(lead),
			title=_("Lead Not Found"),
		)

	# Business rule: every demo must be allocated to a Functional Consultant at creation
	if not functional_consultant:
		frappe.throw(
			_("Please select a Functional Consultant to run this demo."),
			title=_("Consultant Required"),
		)

	doc = frappe.new_doc("Demo Request")
	doc.customer = customer
	doc.lead = lead
	doc.company = company
	doc.contact_person = contact_person
	doc.contact_number = contact_number
	doc.email = email
	doc.interested_module = interested_module
	doc.customer_requirements = customer_requirements
	doc.business_process_requirements = business_process_requirements
	doc.priority = priority or "Medium"
	doc.preferred_demo_date = preferred_demo_date
	doc.preferred_demo_time = preferred_demo_time
	doc.demo_type = demo_type
	doc.sales_remarks = sales_remarks
	doc.functional_consultant = functional_consultant
	# fetch_from does NOT run on API inserts - resolve the consultant's user so
	# the 'Consultant Assigned' / 'Demo Scheduled' notifications can reach them
	doc.consultant_user = frappe.db.get_value(
		"Functional Consultant", functional_consultant, "user"
	)
	doc.insert()  # respects role permissions; sales_person defaults to the session user

	# move the new request from Draft to Requested
	try:
		change_status(doc, "Requested")
	except Exception:
		# the request is still created; the sales team can move it from the desk
		frappe.log_error(
			title=_("Portal: Demo Request could not be moved to Requested"),
			message=frappe.get_traceback(),
		)

	frappe.msgprint(_("Demo Request {0} created.").format(doc.name))
	return {"name": doc.name}


@frappe.whitelist()
def assign_consultant(demo_request=None, consultant=None):
	"""Assign (or reassign) a Functional Consultant on a Demo Request and move
	the workflow to 'Assigned' when the request is still in its early stages.

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

	doc.functional_consultant = consultant
	# fetch_from does NOT run on API saves - keep consultant_user in sync so the
	# 'Consultant Assigned' / 'Consultant Reassigned' notifications can reach them
	doc.consultant_user = frappe.db.get_value("Functional Consultant", consultant, "user")
	doc.save()  # validate runs: only Active consultants, reassignment flag, ToDo + notifications

	if doc.workflow_state in (None, "", "Draft", "Requested"):
		from functional_demo.sales_demo.doctype.demo_request.demo_request import change_status

		doc = change_status(doc, "Assigned")

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
def get_unlinked_users():
	"""Enabled users who do not yet have a Functional Consultant profile.
	Used by the 'Consultant Profiles' manager card in the portal."""
	_guard_consultant_manager()
	linked = {
		row[0]
		for row in frappe.db.sql(
			"select user from `tabFunctional Consultant` where ifnull(user, '') != ''"
		)
	}
	users = frappe.get_all(
		"User",
		filters=[["enabled", "=", 1]],
		fields=["name", "full_name", "email"],
		order_by="full_name asc",
	)
	out = []
	for u in users:
		if u.name in ("Guest", "Administrator") or u.name in linked:
			continue
		out.append(
			{
				"user": u.name,
				"full_name": u.full_name or u.name,
				"email": u.email or "",
			}
		)
	return out


@frappe.whitelist()
def create_consultant_profile(user=None, consultant_name=None, specialization=None):
	"""One-click: create a Functional Consultant profile linked to a User.
	The doctype's on_update hook grants the Functional Consultant role.

	The user argument is optional so a client that fires the call without a
	value (e.g. a stale cached page) gets a clear popup instead of a TypeError
	500 from the framework."""
	_guard_consultant_manager()
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

	doc = frappe.new_doc("Functional Consultant")
	doc.consultant_name = consultant_name
	doc.user = user
	doc.specialization = specialization or ""
	doc.status = "Active"
	doc.availability = "Available"
	doc.insert(ignore_permissions=True)  # role guard enforced above

	frappe.msgprint(
		_("Consultant profile {0} created for {1}. The Functional Consultant role has been granted.").format(
			doc.name, full_name
		)
	)
	return {"name": doc.name, "consultant_name": doc.consultant_name}


@frappe.whitelist()
def update_follow_up(follow_up=None, status=None, outcome=None, remarks=None, next_action=None, discussion_note=None):
	"""Update a Demo Follow Up from the portal: complete it, record the outcome,
	and optionally append a discussion note (creates a Follow Up Note row).

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
	if discussion_note:
		doc.add_discussion_note(discussion_note)
	doc.save()

	frappe.msgprint(_("Follow-up {0} updated.").format(follow_up))
	return {"status": doc.status, "outcome": doc.outcome}
