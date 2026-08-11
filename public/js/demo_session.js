frappe.ui.form.on("Demo Session", {
	refresh(frm) {
		set_template_query(frm);
		render_template_preview(frm);
		add_session_actions(frm);
	},

	demo_template(frm) {
		if (frm.doc.demo_template) {
			frappe.msgprint({
				title: __("Template Snapshot"),
				message: __("On save, the template content will be copied into this session. Future changes to the master template will NOT affect this session."),
				indicator: "blue",
			});
		}
	},
});

function set_template_query(frm) {
	frm.set_query("demo_template", () => {
		const filters = { is_active: 1 };
		if (frm.doc.functional_consultant) {
			filters.functional_consultant = frm.doc.functional_consultant;
		}
		return { filters };
	});
}

function render_template_preview(frm) {
	if (!frm.fields_dict.template_preview) return;
	const $wrapper = frm.fields_dict.template_preview.$wrapper;
	const sections = (frm.doc.template_sections || []).filter((s) => s.content);
	if (!sections.length) {
		$wrapper.empty();
		return;
	}

	let html = sections
		.map((s) => {
			const content = frappe.utils.strip_html(frappe.utils.escape_html(s.content || ""));
			return `
				<div class="demo-preview-section">
					<h6 class="demo-preview-title">${frappe.utils.escape_html(s.section)}</h6>
					<div class="demo-preview-content">${content.replace(/\n/g, "<br>")}</div>
				</div>`;
		})
		.join("");

	$wrapper.empty().append(
		`<div class="demo-template-preview">${html}</div>`
	);
}

function add_session_actions(frm) {
	const status = frm.doc.demo_status;

	frm.page.remove_inner_button("Start Demo");
	frm.page.remove_inner_button("Complete Demo");
	frm.page.remove_inner_button("Cancel Demo");
	frm.page.remove_inner_button("Reschedule");
	frm.page.remove_inner_button("Create Follow-up");
	frm.page.remove_inner_button("Set Final Result");
	frm.page.remove_inner_button("Open Execution Screen");

	frm.page.add_inner_button(__("Open Execution Screen"), () => {
		frappe.set_route("demo-execution", { demo_session: frm.doc.name });
	}, __("Actions"));

	if (["Scheduled", "In Progress"].includes(status)) {
		if (status === "Scheduled") {
			frm.page.add_inner_button(__("Start Demo"), () => {
				frappe.call({
					method: "functional_demo.api.start_demo_session",
					args: { demo_session: frm.doc.name },
					callback() {
						frm.reload_doc();
					},
				});
			}, __("Actions"));
		}
		frm.page.add_inner_button(__("Cancel Demo"), () => {
			frappe.confirm(__("Cancel this demo session?"), () => {
				frappe.call({
					method: "functional_demo.api.cancel_demo_session",
					args: { demo_session: frm.doc.name, reason: "Cancelled from form" },
					callback() {
						frm.reload_doc();
					},
				});
			});
		}, __("Actions"));
	}

	if (status === "In Progress") {
		frm.page.add_inner_button(__("Complete Demo"), () => complete_demo_dialog(frm), __("Actions"));
	}

	if (status === "Scheduled") {
		frm.page.add_inner_button(__("Reschedule"), () => reschedule_dialog(frm), __("Actions"));
	}

	if (["Completed", "Follow-up Required"].includes(status)) {
		frm.page.add_inner_button(__("Create Follow-up"), () => follow_up_dialog(frm), __("Actions"));
		frm.page.add_inner_button(__("Set Final Result"), () => final_result_dialog(frm), __("Actions"));
	}
}

function complete_demo_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Complete Demo & Feedback"),
		fields: [
			{ fieldname: "overall_feedback", label: __("Overall Feedback"), fieldtype: "Small Text" },
			{ fieldname: "interested", label: __("Interested?"), fieldtype: "Select", options: ["", "Interested", "Not Interested", "Undecided"] },
			{ fieldname: "requirements_met", label: __("Requirements Met"), fieldtype: "Select", options: ["", "Fully Met", "Partially Met", "Not Met"] },
			{ fieldname: "additional_requirements", label: __("Additional Requirements"), fieldtype: "Small Text" },
			{ fieldname: "requested_changes", label: __("Requested Changes"), fieldtype: "Small Text" },
			{ fieldname: "demo_feedback_items", label: __("Customer Questions & Requests"), fieldtype: "Table", cannot_add_rows: false, in_place_view: true, fields: [
				{ fieldname: "item_type", label: __("Type"), fieldtype: "Select", options: ["Question", "Change Request", "Additional Requirement"], in_list_view: 1 },
				{ fieldname: "description", label: __("Description"), fieldtype: "Small Text", in_list_view: 1, reqd: 1 },
			], data: [] },
			{ fieldname: "sb1", fieldtype: "Section Break", label: __("Follow-up") },
			{ fieldname: "follow_up_required", label: __("Follow-up Required"), fieldtype: "Check" },
			{ fieldname: "follow_up_date", label: __("Follow-up Date"), fieldtype: "Date", depends_on: "follow_up_required", default: frappe.datetime.add_days(frappe.datetime.get_today(), 7) },
			{ fieldname: "next_action", label: __("Next Action"), fieldtype: "Small Text", depends_on: "follow_up_required" },
			{ fieldname: "consultant_remarks", label: __("Consultant Remarks"), fieldtype: "Small Text" },
		],
		primary_action_label: __("Complete Demo"),
		primary_action(values) {
			dialog.hide();
			frappe.call({
				method: "functional_demo.api.complete_demo_session",
				args: { demo_session: frm.doc.name, feedback: values },
				callback(r) {
					if (r.message) frm.reload_doc();
				},
			});
		},
	});
	dialog.show();
}

function reschedule_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Reschedule Demo"),
		fields: [
			{ fieldname: "scheduled_date", label: __("New Date"), fieldtype: "Date", reqd: 1, default: frm.doc.scheduled_date },
			{ fieldname: "start_time", label: __("Start Time"), fieldtype: "Time", default: frm.doc.start_time },
			{ fieldname: "end_time", label: __("End Time"), fieldtype: "Time", default: frm.doc.end_time },
			{ fieldname: "meeting_link", label: __("Meeting Link"), fieldtype: "Data", default: frm.doc.meeting_link },
		],
		primary_action_label: __("Reschedule"),
		primary_action(values) {
			dialog.hide();
			frappe.call({
				method: "functional_demo.api.reschedule_demo_session",
				args: {
					demo_session: frm.doc.name,
					scheduled_date: values.scheduled_date,
					start_time: values.start_time,
					end_time: values.end_time,
					meeting_link: values.meeting_link,
				},
				callback(r) {
					if (r.message) frm.reload_doc();
				},
			});
		},
	});
	dialog.show();
}

function follow_up_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Create Follow-up"),
		fields: [
			{ fieldname: "follow_up_date", label: __("Follow-up Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.add_days(frappe.datetime.get_today(), 7) },
			{ fieldname: "next_action", label: __("Next Action"), fieldtype: "Small Text" },
			{ fieldname: "assigned_to", label: __("Assigned To"), fieldtype: "Link", options: "User", default: frm.doc.sales_person },
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			dialog.hide();
			frappe.call({
				method: "functional_demo.api.create_follow_up_from_session",
				args: {
					demo_session: frm.doc.name,
					follow_up_date: values.follow_up_date,
					next_action: values.next_action,
					assigned_to: values.assigned_to,
				},
				callback(r) {
					if (r.message) frm.reload_doc();
				},
			});
		},
	});
	dialog.show();
}

function final_result_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Set Final Result"),
		fields: [
			{ fieldname: "result", label: __("Final Result"), fieldtype: "Select", reqd: 1, options: ["Converted", "Not Interested", "Closed"] },
		],
		primary_action_label: __("Set Result"),
		primary_action(values) {
			frappe.confirm(__("Close this demo with result '{0}'? The Demo Request will also be updated.", [values.result]), () => {
				dialog.hide();
				frappe.call({
					method: "functional_demo.api.set_session_final_result",
					args: { demo_session: frm.doc.name, result: values.result },
					callback() {
						frm.reload_doc();
					},
				});
			});
		},
	});
	dialog.show();
}
