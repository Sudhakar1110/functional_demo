# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

app_name = "functional_demo"
app_title = "Sales & Functional Demo Management"
app_publisher = "Functional Demo Team"
app_description = """Complete Sales & Functional Demo Management application for Frappe v15 / ERPNext v15.
Manages the full workflow: Customer Acquisition -> Requirement Collection -> Demo Request ->
Functional Consultant Assignment -> Demo Scheduling -> Consultant-specific Demo Template ->
Demo Execution -> Feedback -> Follow-up -> Conversion/Closure."""
app_icon = "octicon octicon-play"
app_color = "#1F4E79"
app_email = "support@example.com"
app_license = "GNU General Public License (v3)"
source_link = "https://github.com/Sudhakar1110/functional_demo"
develop_version = "15.x.x-develop"

# ERPNext is required - we reuse Lead, Customer, Contact, Employee, User, Event, ToDo etc.
required_apps = ["erpnext"]

before_install = "functional_demo.install.before_install"
after_install = "functional_demo.install.after_install"
# Keep already-installed sites in sync - the migrate hooks below (workflow
# states, consultant statuses, approval removal) are all idempotent, so this
# is safe to run on every migrate.
after_migrate = "functional_demo.install.after_migrate"

# Demo Execution screen: ships as a standard Page doctype (Sales Demo > Page >
# demo-execution) - its JS is loaded by Frappe for the /app/demo-execution route.
# Only the shared CSS is included globally so the styling also applies in other views.
app_include_css = [
	"/assets/functional_demo/css/demo_execution.css",
	"/assets/functional_demo/css/demo_feedback.css",
]

# Portal (website) pages: the shared styles + JS are inlined directly in each
# page template (templates/includes/portal_style.html / portal_script.html) so the
# design renders without a `bench build` on the server. The menu items below are
# the role-based portal menu for the website navbar.
get_standard_portal_menu_items = "functional_demo.portal.get_standard_portal_menu_items"

# Per-doctype form customizations
doctype_js = {
	"Demo Request": "public/js/demo_request.js",
	"Demo Session": "public/js/demo_session.js",
	"Demo Follow Up": "public/js/demo_follow_up.js",
	"Functional Demo Template": "public/js/functional_demo_template.js",
}

# Per-doctype list view customizations (status indicators, quick filters)
doctype_list_js = {
	"Demo Request": ["public/js/demo_request_list.js"],
	"Demo Session": ["public/js/demo_session_list.js"],
}

# Row-level permission filters (consultants/sales users only see their own work)
permission_query_conditions = {
	"Demo Request": "functional_demo.sales_demo.doctype.demo_request.demo_request.get_permission_query_conditions",
	"Demo Session": "functional_demo.sales_demo.doctype.demo_session.demo_session.get_permission_query_conditions",
	"Functional Demo Template": "functional_demo.sales_demo.doctype.functional_demo_template.functional_demo_template.get_permission_query_conditions",
	"Demo Follow Up": "functional_demo.sales_demo.doctype.demo_follow_up.demo_follow_up.get_permission_query_conditions",
	"Functional Consultant": "functional_demo.sales_demo.doctype.functional_consultant.functional_consultant.get_permission_query_conditions",
}

# Document-level permission checks
has_permission = {
	"Demo Request": "functional_demo.sales_demo.doctype.demo_request.demo_request.has_permission",
	"Demo Session": "functional_demo.sales_demo.doctype.demo_session.demo_session.has_permission",
	"Functional Demo Template": "functional_demo.sales_demo.doctype.functional_demo_template.functional_demo_template.has_permission",
	"Demo Follow Up": "functional_demo.sales_demo.doctype.demo_follow_up.demo_follow_up.has_permission",
	"Functional Consultant": "functional_demo.sales_demo.doctype.functional_consultant.functional_consultant.has_permission",
	"Consultant Drive File": "functional_demo.sales_demo.doctype.consultant_drive_file.consultant_drive_file.has_permission",
}

# Scheduled jobs
scheduler_events = {
	# the "all" tick runs every few minutes - used for the 1-hour-before
	# demo reminder so it fires close to exactly 60 minutes ahead
	"all": [
		"functional_demo.sales_demo.doctype.demo_session.demo_session.send_demo_hour_reminders",
	],
	"daily": [
		"functional_demo.install.mark_overdue_follow_ups",
		"functional_demo.sales_demo.doctype.demo_request.demo_request.run_sla_escalation_checks",
		"functional_demo.sales_demo.doctype.demo_session.demo_session.send_demo_reminders",
	],
}

# Fixtures shipped at app root: `functional_demo/fixtures/*.json`
fixtures = ["Role", "Workflow"]
