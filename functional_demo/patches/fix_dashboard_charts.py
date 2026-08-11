# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Patch: repair Group By dashboard charts and workspace placement.

Frappe v15 requires `group_by_field` for 'Group By' Dashboard Charts. Charts
created from the initial fixtures shipped the legacy `x_field` key, which v15
ignores - leaving `group_by_field` empty and crashing the chart renderer with:

    TypeError: argument of type 'NoneType' is not iterable
    (frappe.desk.doctype.dashboard_chart.dashboard_chart.get_group_by_chart_config)

This patch sets `group_by_field` directly on the affected chart records and
also parents both app workspaces under the Home workspace. It runs
automatically on `bench migrate` (one-time per site, tracked via Patch Log).
"""

import frappe

from functional_demo.install import fix_dashboard_charts, fix_workspace_parents


def execute():
	fix_dashboard_charts()
	fix_workspace_parents()
	frappe.db.commit()
	frappe.clear_cache()
