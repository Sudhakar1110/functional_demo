# functional_demo — Sales & Functional Demo Management

[![CI](https://github.com/Sudhakar1110/functional_demo/actions/workflows/ci.yml/badge.svg)](https://github.com/Sudhakar1110/functional_demo/actions/workflows/ci.yml)

A production-ready **Frappe v15 / ERPNext v15** application that manages the complete
business process between the **Sales Team** and the **Functional / Demo Team**:

```
Customer Acquisition → Requirement Collection → Demo Request → Functional Consultant
Assignment → Demo Scheduling → Consultant-Specific Demo Template → Demo Execution →
Feedback → Follow-up → Conversion / Closure
```

It is built for **non-technical users**: minimal data entry, automatic field
population, role-based screens, quick actions, friendly messages and clear status
indicators — while the backend follows proper Frappe v15 / ERPNext v15 standards.

---

## Features

- **Demo Request** with a full workflow
  (`Draft → Requested → Assigned → Scheduled → Demo In Progress → Demo Completed →
  Follow-up Required → Converted / Not Interested / Cancelled / Closed`).
- **Functional Consultant** master (User/Employee link, specialization, ERPNext
  modules, skills, availability, active/inactive) with workload visibility.
- **Consultant-specific Demo Templates** — each consultant maintains their own
  reusable templates (objective, scenario, steps, features, configuration points,
  benefits, questions, FAQs, follow-up points).
- **Immutable template snapshots** — the selected template content is copied into
  each **Demo Session**; later edits to the master template never change historical
  sessions.
- **Demo Session lifecycle** — schedule, start, complete, reschedule, cancel,
  feedback, follow-up and final result, all with one-click actions.
- **Demo Execution screen** — a single, friendly page for the consultant showing
  customer info, demo info, the full template content and quick actions
  (`/app/demo-execution`).
- **Follow-up management** using standard ERPNext **ToDo** assignments + a
  **Demo Follow Up** doc (open/in-progress/completed/overdue).
- **Converted → Opportunity** — marking a Demo Request *Converted* automatically
  creates an ERPNext **Opportunity** (linked via a custom field) so the win flows
  into the standard sales pipeline.
- **Role-based access** (row-level permission filters + doc-level checks).
- **Workspaces** — dedicated **Sales Demo Workspace** and **Functional Demo
  Workspace** with shortcuts, cards, number cards and charts.
- **13 reports** with filters (demo requests, sessions, consultant-wise,
  sales-person-wise, customer history, status, upcoming, completed, follow-ups,
  workload, template usage, module-wise, conversion funnel).
- **10 notifications** (created, assigned, scheduled, rescheduled, cancelled,
  starting soon, completed, follow-up required, follow-up due, reassigned) —
  email + in-app, using Frappe's standard Notification mechanism.
- **Audit trail** — track_changes versioning, activity history child table and
  timeline Communication entries.
- **Schedule-conflict prevention** for consultants.
- Reuses standard ERPNext DocTypes: **Lead, Customer, Contact, Opportunity,
  Employee, User, Event, ToDo, Communication**.

## Requirements

| Component | Version |
| --- | --- |
| Frappe Framework | **v15** (>= 15.0) |
| ERPNext | **v15** (installed on the site before this app) |
| Python | >= 3.10 |

> ERPNext is a **hard dependency** (`required_apps`). `Sales User` and
> `Sales Manager` are the standard ERPNext roles and are reused as-is.

## Installation

```bash
# 1. Get the app into your bench
cd frappe-bench
bench get-app https://github.com/Sudhakar1110/functional_demo

# 2. Install on your site (ERPNext must already be installed on the site)
bench --site your-site install-app functional_demo

# 3. (Optional, for fresh installs) rebuild and migrate
bench --site your-site migrate
bench build
```

The install automatically creates:

- The **Sales Demo** module.
- Custom roles: **Functional Consultant**, **Functional Team Manager**
  (`Sales User` / `Sales Manager` come from ERPNext).
- The **Demo Request Workflow** (active by default).
- Doctypes, Reports, Notifications, Workspaces, Number Cards, Dashboard Charts.
- A daily scheduled job that marks overdue follow-ups.

## Sample data

Populate the app with realistic demo records — consultant users & profiles,
customers/leads with contacts, reusable demo templates, and demo requests/sessions
spanning the whole workflow (including a converted one that auto-creates an
Opportunity):

```bash
bench --site your-site execute functional_demo.setup_demo_data.setup_demo_data
```

The script is **idempotent** — re-running it skips records that already exist.
The three sample consultant logins (`rahul.kumar@example.com`, `priya.sharma@example.com`,
`arun.patel@example.com`) get the *Functional Consultant* role and are listed at
run time; set their passwords via *Settings → Users* to log in and try the demo
execution screen.

## Setup (first time)

1. **Create users** (Settings → Users) for your sales people, consultants and
   managers, and assign the roles:
   - `Sales User` / `Sales Manager` (standard ERPNext roles)
   - `Functional Consultant` / `Functional Team Manager` (new roles)
2. **Create Functional Consultants** (Sales Demo → Functional Consultant) for each
   functional user — link the User, set specialization, ERPNext modules, skills,
   availability and status = Active. (Linking a User automatically grants the
   Functional Consultant role.)
3. **Create Demo Templates** per consultant (Sales Demo → Functional Demo
   Template) — e.g. *Accounting Demo*, *GST Demo*, *Sales Demo*.
4. Optionally create **Leads / Customers / Contacts** in ERPNext — the app
   auto-fetches the primary contact, phone and email when you select them.

## Quick start

### Sales user
1. Open the **Sales Demo Workspace**.
2. **+ New Demo Request** → select Lead or Customer (contact details auto-fill),
   capture requirements, select module/priority, save → **Submit Demo Request**.
3. **Assign Consultant** (choose by specialization/module — workload shown).
4. **Schedule Demo** → pick date/time/meeting link → a **Demo Session** is created
   and an **Event** is added to the calendar.
5. Track the status, then review results and **Create Follow-up** / **Set Result**
   (Converted / Not Interested / Closed).

### Functional consultant
1. Open the **Functional Demo Workspace** → **My Demos**.
2. Open your Demo Session → **Open Execution Screen** (or `/app/demo-execution`).
3. Review customer info, select **your demo template** (content is snapshotted),
   run the demo, then **Complete Demo** with feedback.
4. If follow-up is required, it is created automatically (with a ToDo).

### Managers
- Use the workspaces for number cards + charts, and the reports for workload,
  performance and conversion analysis.

## Reports

| Report | Purpose |
| --- | --- |
| Demo Request Report | All demo requests with filters |
| Demo Session Report | All sessions with filters |
| Consultant-wise Demo Report | Per-consultant totals + conversion |
| Sales Person-wise Demo Report | Per-sales-person pipeline + conversion |
| Customer Demo History | Per-customer history |
| Demo Status Report | Status breakdown |
| Upcoming Demo Report | Scheduled / in-progress sessions ahead |
| Completed Demo Report | Completed sessions + feedback |
| Follow-up Report | Follow-ups with status/outcome |
| Consultant Workload Report | Active/today/next-week demos + templates |
| Template Usage Report | Template usage and last-used dates |
| Module-wise Demo Report | Module-wise pipeline + conversion |
| Demo Conversion Report | Full funnel + conversion rate |

## Notifications

Shipped as standard Notification records (enable/disable them from
**Notifications** in the awesome bar). Sending requires outgoing email to be
configured; in-app notifications work out of the box. **Demo Starting Soon** and
**Follow-up Due** use the "days before" mechanism and fire once per day when the
scheduler runs.

## Permissions model

- **Sales User**: own Demo Requests (if_owner + query filter), read customers,
  create/schedule, manage follow-ups.
- **Sales Manager**: everything sales (all requests, reassign, reports).
- **Functional Consultant**: sees only demos/requests assigned to them; manages
  their own templates; completes demos and records feedback.
- **Functional Team Manager**: all consultants, all sessions, templates, workload,
  reassignments.
- **System Manager**: full access.

Row-level filters (`permission_query_conditions`) and doc-level checks
(`has_permission`) are defined in each doctype controller.

## Development

```bash
# run the app test suite (requires a site with the app installed)
bench --site your-site run-tests --app functional_demo
```

Project layout (Frappe v15 conventions — nested app package):

```
functional_demo/
├── functional_demo/     # the importable app package
│   ├── hooks.py         # app hooks (doctype_js, permissions, scheduler, fixtures)
│   ├── api.py           # whitelisted quick-action endpoints
│   ├── install.py       # install hooks + daily scheduler job
│   ├── setup_demo_data.py
│   ├── fixtures/        # Role + Workflow fixtures (synced on install/migrate)
│   ├── sales_demo/
│   │   ├── doctype/     # DocTypes + controllers + tests
│   │   ├── report/      # 13 script reports
│   │   ├── notification/# 10 standard notifications
│   │   ├── workspace/   # 2 workspaces
│   │   ├── dashboard_chart/  # charts
│   │   └── number_card/ # number cards
│   ├── public/js/       # client scripts + Demo Execution page
│   └── modules.txt, patches.txt
├── pyproject.toml       # pip packaging (bench installs the app editable)
└── setup.py
```

## License

GNU General Public License (v3). See [LICENSE](LICENSE).
