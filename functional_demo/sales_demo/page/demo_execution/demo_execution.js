frappe.pages["demo-execution"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Demo Execution"),
		single_column: true,
	});

	let session_field = null;
	let current = null;
	const esc = (v) => frappe.utils.escape_html(v || "");

	function read_session_from_url() {
		const hash = window.location.hash || "";
		const match = hash.match(/demo_session=([^&]+)/);
		if (match) return decodeURIComponent(match[1]);
		if (frappe.route_options && frappe.route_options.demo_session) {
			return frappe.route_options.demo_session;
		}
		return null;
	}

	session_field = page.add_field({
		label: __("Demo Session"),
		fieldtype: "Link",
		options: "Demo Session",
		placeholder: __("Select a demo session"),
		change() {
			const name = session_field.get_value();
			if (name) load_session(name);
		},
	});

	const my_sessions_field = page.add_field({
		label: __("My Sessions"),
		fieldtype: "Select",
		options: [""],
		change() {
			const name = my_sessions_field.get_value();
			if (name) load_session(name);
		},
	});

	function load_session(name) {
		if (!name) {
			render_empty();
			return;
		}
		session_field.set_value(name);
		page.set_title(`${__("Demo Execution")} — ${name}`);
		frappe.call({
			method: "functional_demo.api.get_demo_execution_data",
			args: { demo_session: name },
			callback(r) {
				if (r.message) {
					current = r.message;
					render(r.message);
				}
			},
			error() {
				render_empty(__("Could not load the demo session. Please check the session name and your permissions."));
			},
		});
	}

	function render_empty(message) {
		page.main.empty().append(`
			<div class="demo-exec-empty">
				<h3>${frappe.utils.escape_html(message || __("No demo session selected"))}</h3>
				<p>${__("Pick a session from 'My Sessions' or search the Demo Session field above. If you have no sessions yet, create a Demo Request, assign a consultant and schedule a demo - it will appear here automatically.")}</p>
			</div>`);
	}

	function populate_my_sessions(selected) {
		frappe.call({
			method: "functional_demo.api.get_my_demo_sessions",
			args: {},
			callback(r) {
				const sessions = r.message || [];
				my_sessions_field.set_options([""].concat(sessions.map((s) => s.name)));
				if (selected) return; // already loading the session passed via URL
				const active = sessions.find((s) => ["Scheduled", "In Progress"].includes(s.demo_status));
				if (active) {
					load_session(active.name);
				} else {
					render_empty(
						sessions.length
							? __("No active demo session. Pick one from 'My Sessions' above.")
							: __("No demo sessions found for you yet.")
					);
				}
			},
		});
	}

	function render(data) {
		const session = data.session || {};
		const customer = data.customer || {};
		const team = data.team || {};
		const request = data.request || {};
		const template = data.template || {};

		const badge_class = {
			"Scheduled": "scheduled",
			"In Progress": "in-progress",
			"Completed": "completed",
			"Cancelled": "cancelled",
			"Closed": "closed",
		}[session.demo_status] || "scheduled";

		const sections_html = (template.sections || [])
			.map(
				(s) => `
				<details class="demo-template-section" open>
					<summary>${esc(s.section)}</summary>
					<div class="demo-template-body">${esc(s.content)}</div>
				</details>`
			)
			.join("");

		page.main.empty().append(`
			<div class="demo-exec-page">
				<div class="demo-exec-header">
					<h2 class="demo-exec-title">${esc(customer.customer || customer.lead || session.name)}</h2>
					<span class="demo-exec-badge ${badge_class}">${esc(session.demo_status)}</span>
				</div>

				<div class="demo-exec-grid">
					<div class="demo-exec-card">
						<h5>${__("Leads Information")}</h5>
						<div class="demo-exec-row"><span class="label">${__("Leads")}</span><span class="value">${esc(customer.customer || "-")}</span></div>
						<div class="demo-exec-row"><span class="label">${__("Sales Person")}</span><span class="value">${esc(customer.lead || "-")}</span></div>
						<div class="demo-exec-row"><span class="label">${__("Contact Person")}</span><span class="value">${esc(customer.contact_person || "-")}</span></div>
						<div class="demo-exec-row"><span class="label">${__("Contact Number")}</span><span class="value">${esc(customer.contact_number || "-")}</span></div>
						<div class="demo-exec-row"><span class="label">${__("Email")}</span><span class="value">${esc(customer.email || "-")}</span></div>
						<div class="demo-exec-row"><span class="label">${__("Company")}</span><span class="value">${esc(customer.company || "-")}</span></div>
					</div>

					<div class="demo-exec-card">
						<h5>${__("Demo Information")}</h5>
						<div class="demo-exec-row"><span class="label">${__("Demo Request")}</span><span class="value">${esc(request.name || "-")} (${esc(request.status || "")})</span></div>
						<div class="demo-exec-row"><span class="label">${__("Sales Person")}</span><span class="value">${esc(team.sales_person || "-")}</span></div>
						<div class="demo-exec-row"><span class="label">${__("Functional Consultant")}</span><span class="value">${esc(team.consultant_name || team.functional_consultant || "-")}</span></div>
						<div class="demo-exec-row"><span class="label">${__("Demo Type")}</span><span class="value">${esc(session.demo_type || "-")}</span></div>
						<div class="demo-exec-row"><span class="label">${__("Date & Time")}</span><span class="value">${esc(session.scheduled_date || "-")} ${esc(session.start_time || "")}${session.end_time ? " - " + esc(session.end_time) : ""}</span></div>
						<div class="demo-exec-row">
							<span class="label">${__("Meeting Link")}</span>
							<span class="value">${session.meeting_link ? `<a class="demo-exec-meeting" href="${esc(session.meeting_link)}" target="_blank">${esc(session.meeting_link)}</a>` : "-"}</span>
						</div>
						<div class="demo-exec-row"><span class="label">${__("Priority")}</span><span class="value">${esc(request.priority || "-")}</span></div>
					</div>
				</div>

				${request.customer_requirements ? `
				<div class="demo-exec-card" style="margin-bottom: 1.25rem;">
					<h5>${__("Leads Requirements")}</h5>
					<div style="white-space: pre-wrap; font-size: 0.9rem;">${esc(request.customer_requirements)}</div>
					${request.business_process_requirements ? `<div style="white-space: pre-wrap; font-size: 0.9rem; margin-top: 0.5rem; color: var(--text-muted);">${esc(request.business_process_requirements)}</div>` : ""}
				</div>` : ""}

				<div class="demo-exec-card" style="margin-bottom: 1.25rem;">
					<h5>${__("Demo Template")} ${template.template_name ? `— ${esc(template.template_name)}` : ""}</h5>
					${sections_html || `<p style="color: var(--text-muted);">${__("No template selected for this session yet.")}</p>`}
				</div>

				<div class="demo-exec-actions">${actions_html(data)}</div>

				${render_feedback(session)}
			</div>`);
		bind_action_buttons();
	}

	function render_feedback(session) {
		if (!["Completed", "Follow-up Required", "Closed"].includes(session.demo_status)) return "";
		return `
			<div class="demo-feedback-grid">
				<div class="demo-exec-card">
					<h5>${__("Leads Feedback")}</h5>
					<div class="demo-exec-row"><span class="label">${__("Overall Feedback")}</span><span class="value">${esc(session.overall_feedback || "-")}</span></div>
					<div class="demo-exec-row"><span class="label">${__("Interested?")}</span><span class="value">${esc(session.interested || "-")}</span></div>
					<div class="demo-exec-row"><span class="label">${__("Requirements Met")}</span><span class="value">${esc(session.requirements_met || "-")}</span></div>
					<div class="demo-exec-row"><span class="label">${__("Follow-up Required")}</span><span class="value">${session.follow_up_required ? __("Yes") : __("No")}</span></div>
					<div class="demo-exec-row"><span class="label">${__("Follow-up Date")}</span><span class="value">${esc(session.follow_up_date || "-")}</span></div>
					<div class="demo-exec-row"><span class="label">${__("Next Action")}</span><span class="value">${esc(session.next_action || "-")}</span></div>
					<div class="demo-exec-row"><span class="label">${__("Final Result")}</span><span class="value">${esc(session.final_result || "-")}</span></div>
				</div>
				<div class="demo-exec-card">
					<h5>${__("Demo Notes")}</h5>
					<div style="white-space: pre-wrap; font-size: 0.9rem;">${esc(session.demo_notes || __("No notes recorded."))}</div>
				</div>
			</div>`;
	}

	function actions_html(data) {
		const session = data.session || {};
		const status = session.demo_status;
		const can_write = data.can_write;
		const can_execute = data.can_execute;
		const can_cancel = data.can_cancel;
		if (!can_write) return "";

		const buttons = [];
		const push = (label, cls, action) => buttons.push(`<button class="btn ${cls}" data-action="${action}">${label}</button>`);

		// a Rescheduled session is still active and startable
		if (["Scheduled", "Rescheduled"].includes(status)) {
			if (can_execute) push(__("Start Demo"), "btn-primary", "start");
			push(__("Reschedule"), "btn-default", "reschedule");
			if (can_cancel) push(__("Cancel Demo"), "btn-danger", "cancel");
		}
		if (status === "In Progress") {
			if (can_execute) push(__("Complete Demo"), "btn-primary", "complete");
			if (can_cancel) push(__("Cancel Demo"), "btn-danger", "cancel");
		}
		if (["Completed", "Follow-up Required"].includes(status)) {
			push(__("Create Follow-up"), "btn-primary", "follow_up");
			if (can_execute) push(__("Set Final Result"), "btn-secondary", "result");
		}
		push(__("Open Session Form"), "btn-default", "open_form");
		push(__("Refresh"), "btn-default", "refresh");

		return buttons.join("");
	}

	/* Wire the action buttons with NATIVE event listeners attached at render
	   time - the previous delegated handler depended on jQuery's global `$`
	   (and its .on() on page.main), and when that is unavailable in the desk
	   bundle every button silently does nothing. Native addEventListener works
	   regardless of how the desk loads jQuery, and is re-attached on each
	   render so it can never go stale. */
	function handle_action(action) {
		const name = current && current.session ? current.session.name : session_field.get_value();
		if (!name) return;
		if (action === "start")
			call("functional_demo.api.start_demo_session", { demo_session: name }, __("Demo started. Good luck!"), () => load_session(name));
		if (action === "cancel") cancel_demo(name);
		if (action === "complete") complete_demo(name);
		if (action === "reschedule") reschedule_demo(name);
		if (action === "follow_up") follow_up_dialog(name);
		if (action === "result") result_dialog(name);
		if (action === "open_form") frappe.set_route("Form", "Demo Session", name);
		if (action === "refresh") load_session(name);
	}

	function bind_action_buttons() {
		const container = page.main && page.main.get ? page.main.get(0) : page.main;
		if (!container || !container.querySelectorAll) return;
		container.querySelectorAll(".demo-exec-actions button").forEach((btn) => {
			btn.addEventListener("click", function () {
				handle_action(this.getAttribute("data-action"));
			});
		});
	}

	function call(method, args, success_message, on_success) {
		frappe.call({
			method,
			args,
			callback(r) {
				if (r.message && success_message) frappe.show_alert({ message: success_message, indicator: "green" });
				if (on_success) on_success(r.message);
			},
		});
	}

	function cancel_demo(name) {
		frappe.confirm(__("Cancel this demo session?"), () => {
			call("functional_demo.api.cancel_demo_session", { demo_session: name, reason: "Cancelled from execution screen" }, __("Demo cancelled."), () => load_session(name));
		});
	}

	function complete_demo(name) {
		const dialog = new frappe.ui.Dialog({
			title: __("Complete Demo & Feedback"),
			fields: [
				{ fieldname: "overall_feedback", label: __("Overall Feedback"), fieldtype: "Small Text", reqd: 1 },
				{ fieldname: "interested", label: __("Interested?"), fieldtype: "Select", options: ["", "Interested", "Not Interested", "Undecided"] },
				{ fieldname: "requirements_met", label: __("Requirements Met"), fieldtype: "Select", options: ["", "Fully Met", "Partially Met", "Not Met"] },
				{ fieldname: "additional_requirements", label: __("Additional Requirements"), fieldtype: "Small Text" },
				{ fieldname: "requested_changes", label: __("Requested Changes"), fieldtype: "Small Text" },
				{ fieldname: "demo_notes", label: __("Demo Notes"), fieldtype: "Small Text" },
				{ fieldname: "sb1", fieldtype: "Section Break", label: __("Follow-up") },
				{ fieldname: "follow_up_required", label: __("Follow-up Required"), fieldtype: "Check" },
				{ fieldname: "follow_up_date", label: __("Follow-up Date"), fieldtype: "Date", depends_on: "follow_up_required", default: frappe.datetime.add_days(frappe.datetime.get_today(), 7) },
				{ fieldname: "next_action", label: __("Next Action"), fieldtype: "Small Text", depends_on: "follow_up_required" },
				{ fieldname: "consultant_remarks", label: __("Consultant Remarks"), fieldtype: "Small Text" },
			],
			primary_action_label: __("Complete Demo"),
			primary_action(values) {
				dialog.hide();
				call("functional_demo.api.complete_demo_session", { demo_session: name, feedback: values }, __("Demo completed and feedback recorded."), () => load_session(name));
			},
		});
		dialog.show();
	}

	function reschedule_demo(name) {
		const dialog = new frappe.ui.Dialog({
			title: __("Reschedule Demo"),
			fields: [
				{ fieldname: "scheduled_date", label: __("New Date"), fieldtype: "Date", reqd: 1, default: current.session.scheduled_date },
				{ fieldname: "start_time", label: __("Start Time"), fieldtype: "Time", default: current.session.start_time },
				{ fieldname: "end_time", label: __("End Time"), fieldtype: "Time", default: current.session.end_time },
				{ fieldname: "meeting_link", label: __("Meeting Link"), fieldtype: "Data", default: current.session.meeting_link },
			],
			primary_action_label: __("Reschedule"),
			primary_action(values) {
				dialog.hide();
				call("functional_demo.api.reschedule_demo_session", { demo_session: name, ...values }, __("Demo rescheduled."), () => load_session(name));
			},
		});
		dialog.show();
	}

	function follow_up_dialog(name) {
		const dialog = new frappe.ui.Dialog({
			title: __("Create Follow-up"),
			fields: [
				{ fieldname: "follow_up_date", label: __("Follow-up Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.add_days(frappe.datetime.get_today(), 7) },
				{ fieldname: "next_action", label: __("Next Action"), fieldtype: "Small Text" },
				{ fieldname: "assigned_to", label: __("Assigned To"), fieldtype: "Link", options: "User" },
			],
			primary_action_label: __("Create"),
			primary_action(values) {
				dialog.hide();
				call("functional_demo.api.create_follow_up_from_session", { demo_session: name, ...values }, __("Follow-up created."), () => load_session(name));
			},
		});
		dialog.show();
	}

	function result_dialog(name) {
		const dialog = new frappe.ui.Dialog({
			title: __("Set Final Result"),
			fields: [{ fieldname: "result", label: __("Final Result"), fieldtype: "Select", reqd: 1, options: ["Converted", "Not Interested", "Closed"] }],
			primary_action_label: __("Set Result"),
			primary_action(values) {
				frappe.confirm(__("Close this demo with result '{0}'? The Demo Request will also be updated.", [values.result]), () => {
					dialog.hide();
					call("functional_demo.api.set_session_final_result", { demo_session: name, result: values.result }, __("Final result set."), () => load_session(name));
				});
			},
		});
		dialog.show();
	}

	// initial load
	const initial = read_session_from_url();
	if (initial) {
		load_session(initial);
	}
	populate_my_sessions(initial);
};
