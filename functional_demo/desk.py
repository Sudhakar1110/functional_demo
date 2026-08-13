# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Desk-side boot customizations (registered under `boot_session` in hooks.py)."""

import frappe


def hide_lead_from_desk(bootinfo):
	"""Keep the ERPNext desk free of the Lead workspace.

	Leads are managed from the sales portal (My Leads) only. Remove any
	'Lead' workspace - or child workspaces grouped under one - from the
	desk sidebar. Idempotent no-op when no such workspace exists.
	"""
	workspaces = bootinfo.get("allowed_workspaces") or []
	filtered = [
		ws
		for ws in workspaces
		if ws.get("name") != "Lead" and ws.get("parent_page") != "Lead"
	]
	if len(filtered) != len(workspaces):
		bootinfo["allowed_workspaces"] = filtered
