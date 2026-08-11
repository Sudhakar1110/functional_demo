# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Patch: create the Workflow State records used by the Demo Request workflow.

A workflow imported via fixture does not auto-create Workflow State documents.
Frappe v15 references these records from workflow-enabled forms, and missing
states surface as "Workflow State <name> not found". This patch creates the
records for the states defined in the Demo Request workflow.
"""

import frappe

from functional_demo.install import create_workflow_states


def execute():
	create_workflow_states()
	frappe.db.commit()
