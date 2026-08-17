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
- **Role-based access** (row-level permission filters + doc-level checks) with a
  role-aware **web portal**: Sales sees all content, the Functional team sees
  functional-only sections, and the **Developer** role sees feedback only.
- **Workspaces** — dedicated **Sales Demo Workspace** and **Functional Demo
  Workspace** with shortcuts, cards, number cards and charts.
- **12 reports** with filters (demo requests, sessions, consultant-wise,
  sales-person-wise, leads history, status, upcoming, completed, follow-ups,
  workload, module-wise, conversion funnel).
- **Notifications + emails** — in-app bell notifications (portal + desk) and
  direct emails built into the workflow code: consultant assignment/reassignment,
  demo scheduled/rescheduled, started, completed, cancelled, final result,
  follow-up created, plus a daily day-before-demo reminder and SLA escalation.
  (Legacy standard Notification doctypes are shipped disabled.)
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
- Daily scheduled jobs: marks overdue follow-ups (notifying the assignee /
  sales person), runs SLA escalation checks, and sends day-before-demo
  reminders.

## Sample data

Populate the app with realistic demo records — consultant users & profiles,
prospect companies (**Leads**) and lead records (**Sales Person**) with contacts,
reusable demo templates, and demo requests/sessions spanning the whole workflow
(including a converted one that auto-creates an Opportunity):

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
   shows them as **Sales Person** / **Leads** and auto-fetches the primary
   contact, phone and email when you select them.

## Quick start

### Sales user
1. Open the **Sales Demo Workspace**.
2. **+ New Demo Request** → select **Sales Person** (Lead) or **Leads**
   (Customer) — contact details auto-fill — capture requirements, select
   template/priority, save → **Submit Demo Request**.
3. **Assign Consultant** (choose by specialization/module — workload shown).
4. **Schedule Demo** → pick date/time/meeting link → a **Demo Session** is created
   and an **Event** is added to the calendar.
5. Track the status, then review results and **Create Follow-up** / **Set Result**
   (Converted / Not Interested / Closed).

### Functional consultant
1. Open the **Functional Demo Workspace** → **My Demos**.
2. Open your Demo Session → **Open Execution Screen** (or `/app/demo-execution`).
3. Review customer info, run the demo, then **Complete Demo** with feedback.
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
| Leads Demo History | Per-lead history |
| Demo Status Report | Status breakdown |
| Upcoming Demo Report | Scheduled / in-progress sessions ahead |
| Completed Demo Report | Completed sessions + feedback |
| Follow-up Report | Follow-ups with status/outcome |
| Consultant Workload Report | Active/today/next-week demos |
| Module-wise Demo Report | Module-wise pipeline + conversion |
| Demo Conversion Report | Full funnel + conversion rate |

## Notifications

Notifications are built into the workflow code: every event (consultant
assigned/reassigned, demo scheduled/rescheduled, demo started, completed,
cancelled, final result, follow-up created/overdue, follow-up marked
*Additional Demo Required*, the day-before-demo reminder and SLA escalation)
sends an **in-app notification** (portal bell + desk bell, via Notification Log)
and a **direct email** to the affected people. Emails require outgoing mail to
be configured; in-app notifications work out of the box.

The legacy standard Notification doctypes shipped in earlier versions are still
present but are **disabled** (`enabled = 0`) — do not enable them, they would
double-send alongside the code-based notifications.

### Popup notifications (portal)

While a portal page is open, new notifications also **pop up** (toast in the
top-right + a short chime), and when the browser tab is in the background an
**OS-level popup** is shown via the Notification API. The browser asks for
permission on your first click (or when you open the bell) — allow it once and
you are set.

### Web Push — popups even on *another* page / site

To receive a popup (with sound) even when you are **not on the site at all**
(e.g. working in another tab of another website), the site must have **Web
Push** enabled. Frappe does not ship this out of the box, so it is opt-in:

1. Generate a VAPID key pair (run from anywhere with Node):

   ```bash
   node -e "const c=require('crypto');const{publicKey,privateKey}=c.generateKeyPairSync('ec',{namedCurve:'prime256v1'});const jw=publicKey.export({format:'jwk'});const d=privateKey.export({format:'jwk'});const b64u=b=>Buffer.from(b,'base64').toString('base64url');const pub=b64u(Buffer.concat([Buffer.from([4]),Buffer.from(jw.x,'base64url'),Buffer.from(jw.y,'base64url')]).toString('base64'));console.log('vapid_public_key :',pub);console.log('vapid_private_key:',b64u(d.d));"
   ```

2. Configure the keys on the site and install the push library (on the bench):

   ```bash
   bench --site your-site set-config vapid_public_key "<public key>"
   bench --site your-site set-config vapid_private_key "<private key>"
   bench --site your-site set-config vapid_subject "mailto:admin@example.com"
   bench pip install pywebpush
   bench --site your-site migrate
   ```

3. The site must be served over **HTTPS** (service workers require a secure
   context; `localhost` works in development).

4. Each user clicks **Allow** once on the notification prompt — after that every
   event (scheduled, started, completed, cancelled, result, follow-up, SLA,
   reminders) delivers an OS popup with a chime (`/chime.wav`) even when they
   are on another page entirely. Expired subscriptions are cleaned up
   automatically (HTTP 404/410).

Without VAPID keys the feature is silently off — the in-app bell, portal popups
and emails continue to work as described above.

## Permissions model

- **Sales User**: own Demo Requests (if_owner + query filter), read customers,
  create/schedule, manage follow-ups.
- **Sales Manager**: everything sales (all requests, reassign, reports).
- **Functional Consultant**: sees only demos/requests assigned to them;
  completes demos and records feedback.
- **Functional Team Manager**: all consultants, all sessions, templates, workload,
  reassignments.
- **Developer** (standard Frappe role) / **Feedback Viewer** (legacy alias):
  feedback-only access - sees only the Demo Feedback page, both in the portal
  (`/feedback`) and in the desk (`/app/demo-feedback`).
- **System Manager**: full access.

Row-level filters (`permission_query_conditions`) and doc-level checks
(`has_permission`) are defined in each doctype controller. Demo execution
actions (start / complete / cancel / final result) are additionally gated in
the Demo Session controller so only functional-team users can run them.

## Development

```bash
# run the app test suite (requires a site with the app installed)
bench --site your-site run-tests --app functional_demo
```

## Troubleshooting

### `No module named 'functional_demo'` when running `bench install-app`

This means the app folder exists in `apps/` but was never **registered in the
bench's Python virtualenv** (the editable pip-install step). This app uses the
standard nested layout (`functional_demo/functional_demo/`), which is what
`bench get-app` expects, but a manual `git clone` / copy skips the pip step.

Fix it with one command (run from the bench root):

```bash
bench pip install -e apps/functional_demo
```

or use the bundled one-shot installer, which also handles the pip step, falls
back to a `.pth` entry when needed, installs the app and builds assets
(the site name is optional - it is auto-detected when omitted):

```bash
cd ~/frappe-bench-v15
bash apps/functional_demo/install.sh
```

### Clean re-install (recommended when the folder was cloned manually)

```bash
cd ~/frappe-bench-v15
rm -rf apps/functional_demo
bench get-app https://github.com/Sudhakar1110/functional_demo   # clones AND pip-installs
bench --site your-site install-app functional_demo
bench build
```

### `erpnext` must be installed first

`functional_demo` requires ERPNext on the same site (`required_apps = ["erpnext"]`).
Verify with `bench --site your-site list-apps`; if missing, run
`bench --site your-site install-app erpnext` first.

Project layout (Frappe v15 conventions — nested app package):

```
functional_demo/
├── functional_demo/     # the importable app package
│   ├── hooks.py         # app hooks (doctype_js, permissions, scheduler, fixtures)
│   ├── api.py           # whitelisted quick-action endpoints
│   ├── install.py       # install/migrate hooks + daily scheduler jobs
│   ├── portal.py        # shared portal helpers (roles, sidebar, notifications)
│   ├── roles.py         # custom role definitions
│   ├── setup_demo_data.py
│   ├── fixtures/        # Role + Workflow fixtures (synced on install/migrate)
│   ├── patches/         # version patches (workflow states, dashboard charts)
│   ├── sales_demo/
│   │   ├── doctype/     # DocTypes + controllers + tests
│   │   ├── report/      # 12 script reports
│   │   ├── notification/# 10 legacy notifications (shipped disabled)
│   │   ├── page/        # Demo Execution + Demo Feedback desk pages
│   │   ├── workspace/   # 2 workspaces
│   │   ├── dashboard_chart/  # charts
│   │   └── number_card/ # number cards
│   ├── templates/       # shared portal style + script includes
│   ├── www/             # role-based portal pages (sales / functional / manager / feedback)
│   ├── public/          # client scripts + css (form & list customizations)
│   └── modules.txt, patches.txt
├── pyproject.toml       # pip packaging (bench installs the app editable)
└── setup.py
```

## License

GNU General Public License (v3). See [LICENSE](LICENSE).
