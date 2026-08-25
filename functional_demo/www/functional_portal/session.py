# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.api import get_demo_execution_data
from functional_demo.portal import portal_context


def get_context(context):
	portal_context(
		context,
		_("Demo Session"),
		["Sales User", "Sales Manager", "Functional Consultant", "Functional Team Manager", "Feedback Viewer", "Developer"],
		active="sessions",
		subtitle=_("Session details, demo feedback and actions"),
	)
	name = frappe.form_dict.get("name") or ""
	if not name:
		context.missing = True
		return context

	# get_demo_execution_data lets every portal role view session details
	# read-only (Demo Feedback / Results list every session). An error here
	# means the session is missing/invalid - show a friendly card instead of
	# a raw error.
	try:
		data = get_demo_execution_data(name)
	except Exception:
		context.access_denied = True
		return context
	if data.get("session") and data["session"].get("scheduled_date"):
		data["session"]["scheduled_date"] = frappe.utils.format_date(
			data["session"]["scheduled_date"], "medium"
		)
	# Raw datetimes (e.g. 2026-08-17 11:05:42.016086) are hard to read on the
	# page - show them as "17 Aug 2026, 11:05 AM" instead.
	for key in ("started_on", "completed_on"):
		if data.get("session") and data["session"].get(key):
			data["session"][key] = frappe.utils.format_datetime(
				data["session"][key], "dd MMM yyyy, hh:mm a"
			)
	# A follow-up already exists for this session - the Create Follow-up
	# button must not show again (no duplicate follow-ups).
	session_name = (data.get("session") or {}).get("name")
	context.has_follow_up = bool(
		frappe.db.exists("Demo Follow Up", {"demo_session": session_name}) if session_name else False
	)

	# Fetch follow-up history for this session with version tracking
	follow_ups = []
	follow_up_history = []
	if session_name:
		follow_ups = frappe.get_all(
			"Demo Follow Up",
			filters={"demo_session": session_name},
			fields=[
				"name", "follow_up_date", "status", "outcome",
				"next_action", "remarks", "description", "assigned_to",
				"subject", "creation", "modified", "owner",
			],
			order_by="creation desc",
			ignore_permissions=True,
		) or []
		for fu in follow_ups:
			fu["due_display"] = (
				frappe.utils.format_date(fu.get("follow_up_date"), "medium")
				if fu.get("follow_up_date") else "-"
			)
			fu["created_display"] = (
				frappe.utils.format_datetime(fu.get("creation"), "dd MMM yyyy, hh:mm a")
				if fu.get("creation") else "-"
			)
			fu["modified_display"] = (
				frappe.utils.format_datetime(fu.get("modified"), "dd MMM yyyy, hh:mm a")
				if fu.get("modified") else "-"
			)
			if fu.get("assigned_to"):
				fu["assigned_display"] = (
					frappe.db.get_value("User", fu["assigned_to"], "full_name")
					or fu["assigned_to"]
				)
			else:
				fu["assigned_display"] = "-"
			if fu.get("owner"):
				fu["owner_display"] = (
					frappe.db.get_value("User", fu["owner"], "full_name")
					or fu["owner"]
				)
			else:
				fu["owner_display"] = "-"

			# Fetch discussion notes for this follow-up (filter out empty/null)
			fu["discussion_notes_list"] = []
			try:
				notes = frappe.get_all(
					"Follow Up Note",
					filters={"parent": fu.name, "parenttype": "Demo Follow Up"},
					fields=["name", "note", "note_by", "note_date"],
					order_by="note_date asc",
					ignore_permissions=True,
				) or []
				for note in notes:
					# Skip notes with empty or NULL content
					note_text = (note.get("note") or "").strip()
					if not note_text or note_text.upper() == "NULL":
						continue
					note["note_by_display"] = (
						frappe.db.get_value("User", note["note_by"], "full_name")
						or note.get("note_by") or "-"
					)
					note["note_date_display"] = (
						frappe.utils.format_datetime(note.get("note_date"), "dd MMM yyyy, hh:mm a")
						if note.get("note_date") else "-"
					)
					fu["discussion_notes_list"].append(note)
			except Exception:
				pass

			# Fetch version history for this follow-up
			versions = frappe.get_all(
				"Version",
				filters={
					"ref_doctype": "Demo Follow Up",
					"docname": fu.name,
				},
				fields=["name", "creation", "owner"],
				order_by="creation asc",
				ignore_permissions=True,
			) or []

			# Add the initial creation as first entry
			follow_up_history.append({
				"type": "created",
				"follow_up": fu.name,
				"subject": fu.get("subject") or fu.name,
				"date": fu.created_display,
				"user": fu.owner_display,
				"details": "Follow-up created",
				"status": fu.get("status"),
				"outcome": fu.get("outcome"),
				"follow_up_date": fu.due_display,
				"next_action": fu.get("next_action"),
				"remarks": fu.get("remarks"),
				"description": fu.get("description"),
				"assigned_to": fu.assigned_display,
				"discussion_notes": fu.get("discussion_notes_list", []),
				"sort_key": fu.get("creation") or "",
			})

			# Match each discussion note to its closest version update
			note_version_map = {}  # version_name -> [notes]
			all_notes = fu.get("discussion_notes_list", [])
			if all_notes and versions:
				for note in all_notes:
					note_date_str = str(note.get("note_date") or "")
					best_version = None
					best_diff = None
					for v in versions:
						v_date_str = str(v.get("creation") or "")
						if not note_date_str or not v_date_str:
							continue
						# Calculate time difference in seconds
						try:
							note_dt = frappe.utils.get_datetime(note_date_str)
							v_dt = frappe.utils.get_datetime(v_date_str)
							diff = abs((note_dt - v_dt).total_seconds())
						except Exception:
							diff = 999999
						if best_diff is None or diff < best_diff:
							best_diff = diff
							best_version = v.name
					if best_version:
						note_version_map.setdefault(best_version, []).append(note)
				# If multiple notes map to same version, keep closest only
				for vname, nlist in list(note_version_map.items()):
					if len(nlist) > 1:
						v_creation = str(next(
							(vv.get("creation") or "") for vv in versions if vv.name == vname
						), "")
						best_note = None
						best_diff = None
						for n in nlist:
							n_date = str(n.get("note_date") or "")
							try:
								n_dt = frappe.utils.get_datetime(n_date)
								v_dt = frappe.utils.get_datetime(v_creation)
								diff = abs((n_dt - v_dt).total_seconds())
							except Exception:
								diff = 999999
							if best_diff is None or diff < best_diff:
								best_diff = diff
								best_note = n
						note_version_map[vname] = [best_note] if best_note else []

			# Add each version update
			for v in versions:
				# Get the diff from the version
				try:
					version_doc = frappe.get_doc("Version", v.name)
					changed = []
					if hasattr(version_doc, "changed") and version_doc.changed:
						for ch in version_doc.changed:
							field_label = ch[0] if isinstance(ch, (list, tuple)) else str(ch)
							old_val = ch[1] if isinstance(ch, (list, tuple)) and len(ch) > 1 else ""
							new_val = ch[2] if isinstance(ch, (list, tuple)) and len(ch) > 2 else ""
							if field_label in ("follow_up_date", "status", "outcome", "next_action", "remarks", "assigned_to"):
								changed.append("{0}: {1} \u2192 {2}".format(field_label, old_val or "-", new_val or "-"))
				except Exception:
					changed = []

				v_date = frappe.utils.format_datetime(v.get("creation"), "dd MMM yyyy, hh:mm a") if v.get("creation") else "-"
				v_user = "-"
				if v.get("owner"):
					v_user = frappe.db.get_value("User", v["owner"], "full_name") or v["owner"]

				follow_up_history.append({
					"type": "updated",
					"follow_up": fu.name,
					"subject": fu.get("subject") or fu.name,
					"date": v_date,
					"user": v_user,
					"details": ", ".join(changed) if changed else "Status updated",
					"status": fu.get("status"),
					"outcome": fu.get("outcome"),
					"follow_up_date": fu.due_display,
					"next_action": fu.get("next_action"),
					"remarks": fu.get("remarks"),
					"description": fu.get("description"),
					"assigned_to": fu.assigned_display,
					"discussion_notes": note_version_map.get(v.name, []),
					"sort_key": v.get("creation") or "",
				})

	# Sort history by date (newest first)
	follow_up_history.sort(key=lambda x: x.get("sort_key", ""), reverse=True)

	context.follow_ups = follow_ups
	context.follow_up_history = follow_up_history
	context.data = data
	return context
