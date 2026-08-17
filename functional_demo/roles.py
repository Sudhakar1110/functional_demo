# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE
"""Custom roles created by functional_demo.

'Sales User' and 'Sales Manager' are standard ERPNext roles and are reused.
'Feedback Viewer' is the legacy read-only alias that sees only the Demo
Feedback page. The standard Frappe 'Developer' role is the feedback-only role
for this app: a user carrying it (or 'Feedback Viewer') sees only the Demo
Feedback page - both in the portal (/feedback) and in the desk
(/app/demo-feedback).
"""

ROLES = ["Functional Consultant", "Functional Team Manager", "Feedback Viewer"]
