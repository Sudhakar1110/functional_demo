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

	try:
		data = get_demo_execution_data(name)
	except Exception:
		context.access_denied = True
		return context
	if data.get("session") and data["session"].get("scheduled_date"):
		data["session"]["scheduled_date"] = frappe.utils.format_date(
			data["session"]["scheduled_date"], "medium"
		)
	for key in ("started_on", "completed_on"):
		if data.get("session") and data["session"].get(key):
			data["session"][key] = frappe.utils.format_datetime(
				data["session"][key], "dd MMM yyyy, hh:mm a"
			)

	session_name = (data.get("session") or {}).get("name")
	context.has_follow_up = bool(
		frappe.db.exists("Demo Follow Up", {"demo_session": session_name}) if session_name else False
	)

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

			# Fetch discussion notes (filter out empty/null)
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

			# Fetch version history
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

			# Build the "Follow-up Created" entry with all notes
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

			# --- Match each note to its closest version update ---
			note_version_map = {}  # version_name -> [notes]
			all_notes = fu.get("discussion_notes_list", [])
			if all_notes and versions:
				for note in all_notes:
					note_date_val = note.get("note_date")
					if not note_date_val:
						continue
					best_version_name = None
					best_diff = None
					for v in versions:
						v_creation_val = v.get("creation")
						if not v_creation_val:
							continue
						try:
							if isinstance(note_date_val, str):
								note_dt = frappe.utils.get_datetime(note_date_val)
							else:
								note_dt = note_date_val
							if isinstance(v_creation_val, str):
								v_dt = frappe.utils.get_datetime(v_creation_val)
							else:
								v_dt = v_creation_val
							diff = abs((note_dt - v_dt).total_seconds())
						except Exception:
							continue
						if best_diff is None or diff < best_diff:
							best_diff = diff
							best_version_name = v.name
					if best_version_name:
						note_version_map.setdefault(best_version_name, []).append(note)

				# If multiple notes mapped to same version, keep closest only
				for vname in list(note_version_map.keys()):
					nlist = note_version_map[vname]
					if len(nlist) > 1:
						v_creation_val = None
						for vv in versions:
							if vv.name == vname:
								v_creation_val = vv.get("creation")
								break
						if not v_creation_val:
							continue
						try:
							if isinstance(v_creation_val, str):
								v_dt = frappe.utils.get_datetime(v_creation_val)
							else:
								v_dt = v_creation_val
						except Exception:
							continue
						best_note = None
						best_diff2 = None
						for n in nlist:
							nd = n.get("note_date")
							if not nd:
								continue
							try:
								if isinstance(nd, str):
									n_dt = frappe.utils.get_datetime(nd)
								else:
									n_dt = nd
								diff2 = abs((n_dt - v_dt).total_seconds())
							except Exception:
								continue
							if best_diff2 is None or diff2 < best_diff2:
								best_diff2 = diff2
								best_note = n
						note_version_map[vname] = [best_note] if best_note else []

			# Build each version update entry
			for v in versions:
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
