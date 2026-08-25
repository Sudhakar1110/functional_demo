# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Helpers shared by the Sales / Functional / Manager portal pages (www/)."""

import frappe
from frappe import _

SALES_ROLES = ("Sales User", "Sales Manager")
FUNCTIONAL_ROLES = ("Functional Consultant", "Functional Team Manager")
MANAGER_ROLES = ("Sales Manager", "Functional Team Manager")
# Feedback-only roles: a user carrying either one sees ONLY the Demo Feedback
# page (portal /feedback + desk /app/demo-feedback). The standard Frappe
# 'Developer' role is used as the feedback-only role here, and the legacy custom
# 'Feedback Viewer' role is kept as an equivalent alias for existing installs.
DEVELOPER_ROLES = ("Feedback Viewer", "Developer")


# ---------------------------------------------------------------------------
# role helpers
# ---------------------------------------------------------------------------

def user_roles(user=None):
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	# Only the Administrator account gets every portal section. System Manager
	# is NOT injected here - accounts that carry it along with a sales or
	# functional role must still see exactly what their portal role allows
	# (sales: all content, functional: functional only, developer: feedback).
	if user == "Administrator":
		roles |= set(SALES_ROLES + FUNCTIONAL_ROLES + MANAGER_ROLES)
	return roles


def is_sales(user=None):
	return bool(user_roles(user) & set(SALES_ROLES))


def is_functional(user=None):
	return bool(user_roles(user) & set(FUNCTIONAL_ROLES))


def is_manager(user=None):
	return bool(user_roles(user) & set(MANAGER_ROLES))


def is_admin(user=None):
	"""Site admins (Administrator / System Manager) are never restricted by
	the feedback-only rule. Note: only the Administrator account itself sees
	every section; System Manager users still follow their portal roles for
	the sidebar."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return "System Manager" in user_roles(user)


def is_developer(user=None):
	"""The feedback-only roles (standard 'Developer' / legacy 'Feedback
	Viewer') may view the Dev Feedback page. Administrator is excluded."""
	user = user or frappe.session.user
	if user == "Administrator":
		return False
	return bool(user_roles(user) & set(DEVELOPER_ROLES))


def can_manage_consultants(user=None):
	"""Functional Team Managers and System Managers can create/link
	consultant profiles (the desk-side Functional Consultant doctype is
	restricted to exactly these two roles)."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(user_roles(user) & {"Functional Team Manager", "System Manager"})


# ---------------------------------------------------------------------------
# mail notifications toggle (per-user)
# ---------------------------------------------------------------------------

# Table for storing per-user mail notification preferences. Created
# lazily on first access so the app never breaks on a fresh install
# before the first toggle.
_MAIL_PREFS_TABLE = "tabUser Mail Prefs"


def _ensure_mail_prefs_table():
	"""Create the User Mail Prefs table if it does not exist."""
	if frappe.db.sql("SHOW TABLES LIKE 'tabUser Mail Prefs'"):
		return
	try:
		frappe.db.sql(
			"""CREATE TABLE IF NOT EXISTS `tabUser Mail Prefs` (
				`user` VARCHAR(140) NOT NULL PRIMARY KEY,
				`mail_enabled` INT(1) NOT NULL DEFAULT 1,
				`modified` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
			) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
		)
		frappe.db.commit()
	except Exception:
		# table already exists or permissions issue - ignore
		pass


def _get_mail_pref(user):
	"""Return the mail_enabled value (1 or 0) for a user."""
	_ensure_mail_prefs_table()
	result = frappe.db.sql(
		"SELECT mail_enabled FROM `tabUser Mail Prefs` WHERE user = %s",
		(user,),
	)
	if result:
		return int(result[0][0])
	return 1  # default: enabled


def _set_mail_pref(user, value):
	"""Set the mail_enabled value (1 or 0) for a user."""
	_ensure_mail_prefs_table()
	try:
		frappe.db.sql(
			"""INSERT INTO `tabUser Mail Prefs` (user, mail_enabled)
			VALUES (%s, %s)
			ON DUPLICATE KEY UPDATE mail_enabled = %s""",
			(user, value, value),
		)
		frappe.db.commit()
	except Exception:
		# fallback: try update then insert
		try:
			frappe.db.sql(
				"UPDATE `tabUser Mail Prefs` SET mail_enabled = %s WHERE user = %s",
				(value, user),
			)
			if frappe.db.sql("SELECT changes()") == [(0,)]:
				frappe.db.sql(
					"INSERT INTO `tabUser Mail Prefs` (user, mail_enabled) VALUES (%s, %s)",
					(user, value),
				)
			frappe.db.commit()
		except Exception:
			pass


def is_mail_notifications_enabled(user=None):
	"""Return True when mail notifications are ON for the user (the default).
	
	Per-user setting stored in User Mail Prefs table. Each user controls
	their own email notification preference.
	"""
	user = user or frappe.session.user
	return _get_mail_pref(user) == 1


@frappe.whitelist()
def get_mail_notifications_status():
	"""Return the current mail notifications setting for the current user."""
	return is_mail_notifications_enabled()


@frappe.whitelist()
def toggle_mail_notifications():
	"""Toggle the mail notifications setting for the current user.
	
	All logged-in users can toggle their own email notification preference.
	Returns the new state (True = enabled, False = disabled).
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(
			_("Please log in to change this setting."),
			frappe.PermissionError,
		)
	current = is_mail_notifications_enabled(user)
	new_value = 0 if current else 1
	_set_mail_pref(user, new_value)
	return not current


# ---------------------------------------------------------------------------
# results visibility toggle (site-wide, admin-only)
# ---------------------------------------------------------------------------

RESULTS_HIDDEN_KEY = "demo_portal_results_hidden"


def is_results_hidden():
	"""Return True when Results are hidden for all users (admin toggled ON).
	
	Site-wide setting stored via frappe.db.get_default so it persists
	across reloads and applies to every user.
	"""
	return frappe.db.get_default(RESULTS_HIDDEN_KEY) == "1"


@frappe.whitelist()
def get_results_visibility_status():
	"""Return the current results visibility setting."""
	return {"hidden": is_results_hidden()}


@frappe.whitelist()
def toggle_results_visibility():
	"""Toggle the results visibility setting. Admin / System Manager only.
	
	When ON, results are hidden for ALL users. When OFF, results are shown.
	Returns the new state dict.
	"""
	if not is_admin():
		frappe.throw(
			_("Only administrators can change this setting."),
			frappe.PermissionError,
		)
	current = is_results_hidden()
	new_value = "1" if not current else "0"
	frappe.db.set_default(RESULTS_HIDDEN_KEY, new_value)
	frappe.db.commit()
	return {"hidden": not current}


def consultant_of_user(user=None):
	"""Functional Consultant record linked to the current user.		Administrator gets a consultant profile auto-created on first access so the
		whole portal (My Sessions, Follow-ups, …) works right away for the site
		admin — no manual ERPNext setup needed to test."""
	user = user or frappe.session.user
	name = frappe.db.get_value("Functional Consultant", {"user": user}, "name")
	if name:
		return name
	if user == "Administrator":
		return _ensure_admin_consultant()
	return None


def _ensure_admin_consultant():
	"""Idempotently create a Functional Consultant record for Administrator."""
	existing = frappe.db.get_value("Functional Consultant", {"user": "Administrator"}, "name")
	if existing:
		return existing
	try:
		doc = frappe.new_doc("Functional Consultant")
		doc.consultant_name = "Administrator"
		doc.user = "Administrator"
		doc.specialization = "Custom Application"
		doc.status = "Active"
		doc.availability = "Available"
		doc.insert(ignore_permissions=True)
		return doc.name
	except Exception:
		# never break the portal if auto-creation fails - fall back to the
		# normal guard screen (with the one-click 'Link my user' button)
		frappe.log_error(
			title=_("Could not auto-create Administrator consultant profile"),
			message=frappe.get_traceback(),
		)
		return None


def guard(required_roles):
	"""Raise a permission error unless the user has one of the given roles
	(or is a System Manager)."""
	if "System Manager" in user_roles():
		return
	for role in required_roles:
		if role in user_roles():
			return
	frappe.throw(
		_("You do not have permission to view this page."),
		frappe.PermissionError,
	)


# ---------------------------------------------------------------------------
# sidebar navigation (left-hand menu, role aware)
# ---------------------------------------------------------------------------

def _icon(paths):
	"""Wrap SVG paths into a small line-style icon (inherits currentColor)."""
	return (
		'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
		'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
		+ paths
		+ "</svg>"
	)


ICON_HOME = _icon('<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>')
ICON_SALES = _icon('<line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/>')
ICON_LEADS = _icon('<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>')
ICON_REQUESTS = _icon('<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>')
ICON_RESULTS = _icon('<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>')
ICON_FUNCTIONAL = _icon('<circle cx="12" cy="12" r="10"/><line x1="22" x2="18" y1="12" y2="12"/><line x1="6" x2="2" y1="12" y2="12"/><line x1="12" x2="12" y1="6" y2="2"/><line x1="12" x2="12" y1="22" y2="18"/>')
ICON_SESSIONS = _icon('<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>')
ICON_FOLLOWUPS = _icon('<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>')
ICON_TRIALS = _icon('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>')
ICON_MANAGER = _icon('<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>')
ICON_FEEDBACK = _icon('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>')
ICON_DRIVE = _icon('<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><line x1="12" x2="12" y1="11" y2="17"/><polyline points="9 14 12 17 15 14"/>')
ICON_CONSULTANT_ACTIVITY = _icon('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/><polyline points="14 7 16 7 16 9"/><polyline points="22 11 20 13 22 15"/><line x1="22" y1="11" x2="22" y2="15"/>')
ICON_ASSIGNED = _icon('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="16 11 18 13 22 9"/><line x1="22" y1="11" x2="22" y2="15"/>')
ICON_DAILY_UPDATE = _icon('<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/><path d="m9 16 2 2 4-4"/>')
ICON_FOLLOWUP_TRACKER = _icon('<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/><line x1="12" x1="12" y1="2" y2="4"/><line x1="12" y1="12" y2="12"/><path d="m9 16 2 2 4-4"/>')

def sidebar_items(active):
	"""Sidebar menu for the current user. The sales team sees all content
	(sales + functional); functional team members see only functional-related
	sections (never the sales ones); the feedback-only Developer role sees only
	Feedback."""
	if is_developer():
		return [
			{"label": _("Developer Feedback"), "route": "/dev_feedback", "icon": ICON_FEEDBACK, "active": active == "dev_feedback"},
			{"label": _("Settings"), "route": "/portal_settings", "icon": ICON_MANAGER, "active": active == "settings"},
		]

	items = [{"label": _("Home"), "route": "/demo_portal", "icon": ICON_HOME, "active": active == "home"}]

	results_hidden = is_results_hidden()
	if is_sales():
		items += [
			{"label": _("Sales Home"), "route": "/sales_portal", "icon": ICON_SALES, "active": active == "sales"},
			{"label": _("Sales"), "route": "/sales_portal/my_leads", "icon": ICON_LEADS, "active": active == "leads"},
			{"label": _("Demo Requests"), "route": "/sales_portal/demo_requests", "icon": ICON_REQUESTS, "active": active == "requests"},
		]
		if not results_hidden or is_admin():
			items.append({"label": _("Results"), "route": "/sales_portal/results", "icon": ICON_RESULTS, "active": active == "results"})
		items += [
			{"label": _("Follow-ups"), "route": "/functional_portal/follow_ups", "icon": ICON_FOLLOWUPS, "active": active == "follow_ups"},
		]

	# Manager-only items: Trial Dashboard, End of Day, Follow-up Tracker, Functional Home
	if is_manager():
		items += [
			{"label": _("Trial Dashboard"), "route": "/sales_portal/trials", "icon": ICON_TRIALS, "active": active == "trials"},
			{"label": _("End of Day"), "route": "/sales_portal/daily_update", "icon": ICON_DAILY_UPDATE, "active": active == "daily_update"},
			{"label": _("Follow-up Tracker"), "route": "/sales_portal/followup_tracker", "icon": ICON_FOLLOWUP_TRACKER, "active": active == "followup_tracker"},
			{"label": _("Functional Home"), "route": "/functional_portal", "icon": ICON_FUNCTIONAL, "active": active == "functional"},
		]

	# Functional sections are shared - the sales team sees My Sessions
	if is_sales() or is_functional() or is_manager():
		items += [
			{"label": _("My Sessions"), "route": "/functional_portal/my_sessions", "icon": ICON_SESSIONS, "active": active == "sessions"},
		]

	# The Drive is consultant-only - the sales team never sees it
	if is_functional():
		items += [{"label": _("Drive"), "route": "/functional_portal/drive", "icon": ICON_DRIVE, "active": active == "drive"}]

	if is_manager():
		items += [{"label": _("Manager Dashboard"), "route": "/manager_portal", "icon": ICON_MANAGER, "active": active == "manager"}]

	if can_manage_consultants():
		items += [{"label": _("Consultants"), "route": "/functional_portal/consultants", "icon": ICON_FUNCTIONAL, "active": active == "consultants"}]

	# Consultant Activity — Functional Team Manager only (not Sales Manager)
	if "Functional Team Manager" in user_roles():
		items.append({"label": _("Consultant Activity"), "route": "/consultant_calendar", "icon": ICON_CONSULTANT_ACTIVITY, "active": active == "consultant_activity" or active == "consultant_calendar"})
		items.append({"label": _("Assign Demo"), "route": "/assigned_demo", "icon": ICON_ASSIGNED, "active": active == "assigned_demo"})

	# Feedback is only visible to managers (Functional Team Manager / Sales Manager)
	if is_manager():
		items.append({"label": _("Feedback"), "route": "/feedback", "icon": ICON_FEEDBACK, "active": active == "feedback"})
		items.append({"label": _("Session Feedback"), "route": "/session_feedback", "icon": ICON_FEEDBACK, "active": active == "session_feedback"})

	# Settings (all logged-in users)
	items.append({"label": _("Settings"), "route": "/portal_settings", "icon": ICON_MANAGER, "active": active == "settings"})

	return items


def create_notification(for_user, subject, document_type, document_name):
	"""Create an in-app Notification Log for the user - it shows in the portal
	notification bell and in the ERPNext desk bell (both read Notification Log).
	Also fires a Web Push (OS-level popup with sound) to the user's subscribed
	browsers when the site has VAPID keys configured, so the user sees the
	notification even when they are on another page/site entirely.	A failure is logged but never blocks the action that triggered it.
		
	Skips when mail notifications are disabled by the admin."""
	if not for_user or for_user == "Guest":
		return
	try:
		# Frappe v15+ turned Notification Log.type from a Select into a Link to
		# the Notification Type doctype - ensure the standard 'Alert' record
		# exists so the insert can never fail on the link (older versions just
		# ignore this and accept 'Alert' as a Select option).
		_ensure_notification_type("Alert")
		note = frappe.new_doc("Notification Log")
		note.for_user = for_user
		note.type = "Alert"
		note.document_type = document_type
		note.document_name = document_name
		note.subject = subject
		note.insert(ignore_permissions=True)
		# push the new notification to the user's open portal pages instantly via
		# the realtime (websocket) channel - the bell refreshes immediately
		# instead of waiting for the next polling interval. Best-effort: if
		# realtime is not configured, the client's polling fallback still works.
		try:
			frappe.publish_realtime(
				"demo_portal_notification",
				{
					"name": note.name,
					"subject": subject,
					"document_type": document_type,
					"document_name": document_name,
				},
				user=for_user,
				after_commit=True,
			)
		except Exception:
			pass
	except Exception:
		frappe.log_error(
			title=_("Notification Log creation failed for {0}").format(for_user),
			message=frappe.get_traceback(),
		)

	_send_web_push(for_user, subject, document_type, document_name, note.name)

def _push_target_url(document_type, document_name):
	"""Portal route a Web Push notification should open when clicked - mirrors
	the bell's docHref() so both go to the same place."""
	if document_type == "Demo Request" and document_name:
		return "/sales_portal/demo_request?name={0}".format(document_name)
	if document_type == "Demo Session" and document_name:
		return "/functional_portal/session?name={0}".format(document_name)
	if document_type == "Demo Follow Up":
		return "/functional_portal/follow_ups"
	return "/demo_portal"


def _send_web_push(for_user, subject, document_type, document_name, notification_name=None):
	"""Send an OS-level Web Push (with sound) to every browser the user has
	subscribed. Requires VAPID keys in site_config.json (vapid_public_key /
	vapid_private_key / vapid_subject) and the 'pywebpush' package installed -
	until then this is a silent no-op and the in-app notifications still cover
	everything. Expired subscriptions (HTTP 404/410) are cleaned up."""
	import json

	public_key = frappe.conf.get("vapid_public_key")
	private_key = frappe.conf.get("vapid_private_key")
	if not (public_key and private_key):
		return
	# the doctype may not exist yet on sites that have not run migrate
	if not frappe.db.exists("DocType", "Web Push Subscription"):
		return
	try:
		subs = frappe.get_all(
			"Web Push Subscription",
			filters={"user": for_user, "enabled": 1},
			fields=["name", "subscription"],
			limit_page_length=20,
		)
		if not subs:
			return

		from pywebpush import WebPushException, webpush

		payload = json.dumps(
			{
				"title": subject or "New notification",
				"body": "Sales & Functional Demo Management",
				"url": frappe.utils.get_url(_push_target_url(document_type, document_name)),
				"sound": "/chime.wav",
				"name": notification_name or "",
			}
		).encode("utf-8")
		vapid_claims = {"sub": frappe.conf.get("vapid_subject") or "mailto:admin@example.com"}

		for row in subs:
			try:
				webpush(
					subscription_info=json.loads(row.subscription),
					data=payload,
					vapid_private_key=private_key,
					vapid_claims=vapid_claims,
				)
			except WebPushException as e:
				# 404/410 = the browser dropped the subscription - clean it up so
				# we never push to a dead endpoint again
				if e.response is not None and e.response.status_code in (404, 410):
					frappe.db.delete("Web Push Subscription", row.name)
				else:
					frappe.log_error(
						title=_("Web Push failed for {0}").format(for_user),
						message=frappe.get_traceback(),
					)
			except Exception:
				frappe.log_error(
					title=_("Web Push failed for {0}").format(for_user),
					message=frappe.get_traceback(),
				)
		frappe.db.commit()
	except ImportError:
		# 'pywebpush' is not installed on this bench - in-app notifications still work
		pass
	except Exception:
		frappe.log_error(
			title=_("Web Push setup failed for {0}").format(for_user),
			message=frappe.get_traceback(),
		)


def send_branded_email(
	recipients,
	subject,
	heading,
	intro,
	rows,
	cta_text=None,
	cta_url=None,
	reference_doctype=None,
	reference_name=None,
):
	"""Send a professional, on-brand HTML email (navy/mint design system, the
	same look as the portal). rows is a list of (label, value) pairs rendered
	as a clean two-column table; cta_text / cta_url render a mint action
	button. Mail failures are logged by the callers, never raised here.
	
	Skips sending when mail notifications are disabled by the admin."""
	if not is_mail_notifications_enabled():
		return
	import html as _html

	def esc(value):
		return _html.escape(str(value if value not in (None, "") else "-"), quote=True)

	rows_html = "".join(
		"<tr>"
		'<td style="padding:9px 0;width:190px;vertical-align:top;color:#71717B;font-size:13px;">{0}</td>'
		'<td style="padding:9px 0;vertical-align:top;color:#05133C;font-size:13px;font-weight:600;">{1}</td>'
		"</tr>".format(esc(label), esc(value))
		for label, value in rows
	)
	cta_html = ""
	if cta_text and cta_url:
		cta_html = (
			'<div style="text-align:center;margin:24px 0 4px;">'
			'<a href="{0}" style="display:inline-block;background:#14F1B1;color:#05133C;'
			'text-decoration:none;font-weight:700;font-size:14px;padding:12px 28px;border-radius:10px;">{1}</a>'
			"</div>"
		).format(esc(cta_url), esc(cta_text))

	html = (
		'<div style="background:#F4F6FA;padding:28px 16px;font-family:Arial,Helvetica,sans-serif;">'
		'<div style="max-width:560px;margin:0 auto;background:#FFFFFF;border-radius:14px;overflow:hidden;border:1px solid #E5E7EB;">'
		'<div style="background:linear-gradient(90deg,#05133C 0%,#091526 100%);padding:20px 26px;">'
		'<div style="color:#FFFFFF;font-size:16px;font-weight:700;">Sales &amp; Functional Demo Management</div>'
		'<div style="color:#14F1B1;font-size:11px;margin-top:2px;letter-spacing:0.5px;text-transform:uppercase;">Demo Portal</div>'
		"</div>"
		'<div style="height:3px;background:linear-gradient(90deg,#14F1B1 0%,#114EFF 100%);"></div>'
		'<div style="padding:24px 26px;">'
		'<h2 style="margin:0 0 6px;color:#05133C;font-size:18px;">{heading}</h2>'
		'<p style="margin:0 0 12px;color:#71717B;font-size:13px;line-height:1.6;">{intro}</p>'
		'<table style="width:100%;border-collapse:collapse;">{rows}</table>'
		"{cta}"
		"</div>"
		'<div style="padding:14px 26px;background:#F9FAFB;border-top:1px solid #EEF0F3;color:#9CA3AF;font-size:11px;">'
		"This is an automated notification from the Sales &amp; Functional Demo Portal. Please do not reply to this email."
		"</div>"
		"</div></div>"
	).format(heading=esc(heading), intro=esc(intro), rows=rows_html, cta=cta_html)

	frappe.sendmail(
		recipients=recipients,
		subject=subject,
		html=html,
		reference_doctype=reference_doctype,
		reference_name=reference_name,
		now=True,
	)


def _ensure_notification_type(type_name):
	"""Idempotently create a Notification Type record (Frappe v15+ only).

	Notification Log.type used to be a Select ('Alert', 'Assignment', ...) and is
	a Link to the Notification Type doctype in current Frappe - the record must
	exist or inserting the Notification Log fails silently. Old versions don't
	have the doctype at all, in which case nothing is done."""
	if not frappe.db.exists("DocType", "Notification Type"):
		return
	if frappe.db.exists("Notification Type", type_name):
		return
	try:
		nt = frappe.new_doc("Notification Type")
		nt.type_name = type_name
		nt.enabled = 1
		nt.insert(ignore_permissions=True)
	except Exception:
		# created concurrently elsewhere or unavailable - the Notification Log
		# insert below will surface any real problem
		pass


def greeting():
	"""Time-of-day greeting, e.g. 'Good morning'."""
	hour = frappe.utils.now_datetime().hour
	if hour < 12:
		return _("Good morning")
	if hour < 17:
		return _("Good afternoon")
	return _("Good evening")


# Status display mapping — only changes what the user sees, not the DB value
STATUS_DISPLAY = {
	"Converted": "Demo Completed",
}


def display_status(val):
	"""Return the user-friendly display name for a status value."""
	return STATUS_DISPLAY.get(val, val) if val else val


def portal_context(context, title, required_roles, active, subtitle=""):
	"""Standard context setup for login-required, role-guarded portal pages."""
	context.login_required = True
	context.no_cache = 1
	# Belt & braces: force a fresh render with no-store headers for every portal
	# page so a stale cached copy can never be served to the browser again.
	frappe.local.no_cache = True
	frappe.local.flags.disable_website_cache = True
	if frappe.session.user == "Guest":
		# redirect to the login page (the framework's own login redirect runs
		# after get_context, so we must handle guests here before guard() throws)
		frappe.local.flags.redirect_location = "/login?redirect-to={0}".format(
			frappe.utils.get_url()
		)
		raise frappe.Redirect
	context.title = title
	context.subtitle = subtitle
	context.is_sales = is_sales()
	context.is_functional = is_functional()
	context.is_manager = is_manager()
	context.is_developer = is_developer()
	context.full_name = frappe.utils.get_fullname(frappe.session.user)
	context.greeting = greeting()
	context.today_pretty = frappe.utils.now_datetime().strftime("%A, %d %B %Y")
	context.sidebar_items = sidebar_items(active)
	context.display_status = display_status
	# Full-bleed dashboard layout: skip the standard website container
	# (web.html renders <main class="container my-4"> unless full_width is set)
	context.full_width = True
	guard(required_roles)
	return context


# ---------------------------------------------------------------------------
# stats (lists go through frappe.get_all, so row-level permission filters and
# ERPNext user permissions are respected automatically)
# ---------------------------------------------------------------------------

def _count(doctype, filters=None):
	return len(frappe.get_all(doctype, filters=filters or {}, fields=["name"]) or [])


def sales_stats(user=None):
	user = user or frappe.session.user
	today = frappe.utils.today()
	requests = frappe.get_all(
		"Demo Request", fields=["name", "status"], limit_page_length=1000, order_by="creation desc"
	) or []
	by_status = {}
	for r in requests:
		by_status[r.get("status")] = by_status.get(r.get("status"), 0) + 1

	total = len(requests)
	pending = sum(by_status.get(s, 0) for s in ("Draft", "Requested", "Manager Review"))
	assigned = by_status.get("Assigned", 0)
	scheduled = sum(by_status.get(s, 0) for s in ("Scheduled", "Demo In Progress"))
	completed = sum(by_status.get(s, 0) for s in ("Demo Completed", "Follow-up Required"))
	converted = by_status.get("Converted", 0)

	# Upcoming trial expirations: converted requests whose trial ends today or
	# in the next 7 days, soonest end first - so the sales team sees at a
	# glance which customers are about to lose access.
	end_limit = frappe.utils.add_days(today, 7)
	trial_expirations = frappe.get_all(
		"Demo Request",
		filters={
			"status": "Converted",
			"trial_end_date": ["between", [today, end_limit]],
		},
		fields=["name", "customer", "lead", "sales_person", "trial_start_date", "trial_end_date"],
		order_by="trial_end_date asc",
		limit_page_length=10,
	) or []

	return {
		"total_requests": total,
		"pending": pending,
		"manager_review": by_status.get("Manager Review", 0),
		"assigned": assigned,
		"scheduled": scheduled,
		"completed": completed,
		"converted": converted,
		"todays_demos": _count(
			"Demo Session",
			{"scheduled_date": today, "demo_status": ["in", ["Scheduled", "In Progress"]]},
		),
		"follow_ups_due": _count(
			"Demo Follow Up",
			{"status": ["in", ["Open", "In Progress"]], "follow_up_date": ["<=", today]},
		),
		"conversion_rate": round((converted / total * 100), 1) if total else 0,
		"trials_ending_soon": len(trial_expirations),
		"trial_expirations": trial_expirations,
		"recent_requests": frappe.get_all(
			"Demo Request",
			fields=["name", "customer", "lead", "sales_person", "status", "priority", "interested_module", "preferred_demo_date", "functional_consultant", "creation"],
			order_by="creation desc",
			limit_page_length=8,
		) or [],
	}


def functional_stats(user=None):
	user = user or frappe.session.user
	consultant = consultant_of_user(user)
	today = frappe.utils.today()
	empty = {
		"consultant": consultant,
		"todays_demos": 0, "in_progress": 0, "upcoming": 0,
		"completed": 0, "assigned_demos": 0, "templates": 0,
	}
	if not consultant:
		return empty

	sessions = frappe.get_all(
		"Demo Session",
		filters={"functional_consultant": consultant},
		fields=["name", "demo_status", "scheduled_date"],
		limit_page_length=1000,
	) or []

	# get_all returns Date fields as datetime.date on some drivers and as
	# strings on others - normalize both sides to 'YYYY-MM-DD' strings so the
	# comparison never raises (date >= str -> TypeError) and always matches.
	def _day(value):
		return str(value or "")[:10]

	todays = sum(
		1
		for s in sessions
		if s.get("demo_status") in ("Scheduled", "In Progress") and _day(s.get("scheduled_date")) == today
	)
	in_progress = sum(1 for s in sessions if s.get("demo_status") == "In Progress")
	upcoming = sum(
		1
		for s in sessions
		if s.get("demo_status") == "Scheduled" and _day(s.get("scheduled_date")) >= today
	)
	completed = sum(1 for s in sessions if s.get("demo_status") == "Completed")

	# Assigned Demo Requests (no active session yet)
	assigned_count = frappe.db.count(
		"Demo Request",
		{"functional_consultant": consultant, "status": "Assigned"},
	) or 0

	# Note: follow-up counts are intentionally absent here - follow-ups are
	# sales-team-only, so the functional dashboard never surfaces them.
	return {
		"consultant": consultant,
		"todays_demos": todays,
		"in_progress": in_progress,
		"upcoming": upcoming,
		"completed": completed,
		"assigned_demos": assigned_count,
		"recent_sessions": frappe.get_all(
			"Demo Session",
			filters={"functional_consultant": consultant},
			fields=["name", "customer", "interested_module", "scheduled_date", "start_time", "demo_status", "final_result"],
			order_by="scheduled_date desc",
			limit_page_length=8,
		) or [],
	}


def manager_stats(role=None):
	"""Return dashboard stats. When *role* is 'functional' only consultant-
	related data is returned; when 'sales' only sales-related data.
	Both roles always get the shared pipeline counts."""
	today = frappe.utils.today()

	by_status = dict(
		frappe.db.sql(
			"select status, count(*) from `tabDemo Request` group by status"
		)
	)
	total = sum(by_status.values()) or 0
	converted = by_status.get("Converted", 0) or 0

	consultant_workload = frappe.db.sql(
		"""
		select fc.name, fc.consultant_name, fc.specialization, fc.availability,
			count(ds.name) as active_demos
		from `tabFunctional Consultant` fc
		left join `tabDemo Session` ds
			on ds.functional_consultant = fc.name and ds.demo_status in ('Scheduled', 'In Progress')
		where ifnull(fc.status, '') != 'Inactive'
		group by fc.name
		order by active_demos desc
		"""
	) if role != 'sales' else []

	sales_performance = frappe.db.sql(
		"""
		select sales_person,
			count(*) as total_requests,
			sum(case when status = 'Converted' then 1 else 0 end) as converted,
			sum(case when status in ('Scheduled', 'Demo In Progress') then 1 else 0 end) as scheduled
		from `tabDemo Request`
		group by sales_person
		order by total_requests desc
		"""
	) if role != 'functional' else []

	module_wise = frappe.db.sql(
		"select interested_module, count(*) from `tabDemo Request` group by interested_module order by count(*) desc"
	) or []

	recent_activity = frappe.get_all(
		"Demo Request Activity",
		fields=["activity_type", "activity_date", "user", "status", "remarks", "parent"],
		order_by="activity_date desc",
		limit_page_length=12,
	) or []
	for a in recent_activity:
		a["activity_display"] = (
			frappe.utils.format_datetime(a.get("activity_date"), "medium") if a.get("activity_date") else "-"
		)

	return {
		"total": total,
		"by_status": by_status,
		"pending": sum(by_status.get(s, 0) for s in ("Draft", "Requested", "Manager Review")),
		"assigned": by_status.get("Assigned", 0),
		"scheduled": sum(by_status.get(s, 0) for s in ("Scheduled", "Demo In Progress")),
		"completed": sum(by_status.get(s, 0) for s in ("Demo Completed", "Follow-up Required")),
		"converted": converted,
		"cancelled": by_status.get("Cancelled", 0) or 0,
		"conversion_rate": round(converted / total * 100, 1) if total else 0,
		"todays_demos": _count(
			"Demo Session",
			{"scheduled_date": today, "demo_status": ["in", ["Scheduled", "In Progress"]]},
		),
		# Follow-ups are sales-only: the manager dashboard shows the open
		# follow-up count only to sales managers (functional managers have no
		# Demo Follow Up permission at all, so a bare query would return 0).
		"open_follow_ups": _count(
			"Demo Follow Up", {"status": ["in", ["Open", "In Progress"]]}
		) if is_sales() else 0,
		"consultant_workload": consultant_workload,
		"sales_performance": sales_performance,
		"module_wise": module_wise,
		"recent_activity": recent_activity,
	}


# ---------------------------------------------------------------------------
# portal menu (Frappe shows these in the website menu by role)
# ---------------------------------------------------------------------------

def list_note(shown, total, label):
	"""Return a short 'showing latest X of Y' note when a portal list was
	truncated (shown < total), else an empty string. Pages set this on the
	context so templates can surface the truncation instead of hiding it."""
	if not total or shown >= total:
		return ""
	return _("Showing the latest {0} of {1} {2}. Narrow the filters to see older records.").format(
		shown, total, label
	)


def get_standard_portal_menu_items():
	return [
		{"title": _("Demo Portal"), "route": "/demo_portal", "role": "Sales User"},
		{"title": _("Demo Portal"), "route": "/demo_portal", "role": "Sales Manager"},
		{"title": _("Demo Portal"), "route": "/demo_portal", "role": "Functional Consultant"},
		{"title": _("Demo Portal"), "route": "/demo_portal", "role": "Functional Team Manager"},
		{"title": _("Consultant Drive"), "route": "/functional_portal/drive", "role": "Functional Consultant"},
		{"title": _("Consultant Drive"), "route": "/functional_portal/drive", "role": "Functional Team Manager"},
		{"title": _("Demo Feedback"), "route": "/feedback", "role": "Functional Team Manager"},
		{"title": _("Demo Feedback"), "route": "/feedback", "role": "Sales Manager"},
	]
