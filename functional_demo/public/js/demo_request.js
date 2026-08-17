frappe.ui.form.on("Demo Request", {
	refresh(frm) {
		set_consultant_query(frm);
		show_consultant_info(frm);
		add_quick_actions(frm);
		hide_status_actions(frm);
	},

	customer(frm) {
		if (!frm.doc.customer) return;
		frappe.call({
			method: "functional_demo.api.get_customer_details",
			args: { customer: frm.doc.customer },
			callback(r) {
				if (!r.message) return;
				/* Sales Person Name (contact_person) is always entered manually.
				   Contact Number / Email are the customer's (lead's) own details
				   and are auto-filled only from the customer - the sales person's
				   own number/email must never land in the customer's fields. */
				["contact_number", "email"].forEach((fieldname) => {
					if (r.message[fieldname]) frm.set_value(fieldname, r.message[fieldname]);
				});
			},
		});
	},

	functional_consultant(frm) {
		show_consultant_info(frm);
	},
});

function set_consultant_query(frm) {
	frm.set_query("functional_consultant", () => {
		// No status filter: an unset status is stored as NULL and ANY SQL
		// status filter would hide those consultants. The doctype's own
		// validate() rejects explicit 'Inactive' picks with a clear message.
		return {};
	});
}

function show_consultant_info(frm) {
	if (!frm.doc.functional_consultant) return;
	frappe.call({
		method: "functional_demo.api.get_available_consultants",
		args: {},
		callback(r) {
			const consultant = (r.message || []).find((c) => c.name === frm.doc.functional_consultant);
			if (consultant) {
				frm.set_df_property(
					"functional_consultant",
					"description",
					`${consultant.consultant_name} — ${consultant.specialization || "Generalist"} · Availability: ${consultant.availability} · Active demos: ${consultant.active_demos}`
				);
			}
		},
	});
}

function add_quick_actions(frm) {
	const status = frm.doc.status;

	frm.page.remove_inner_button("Schedule Demo");
	frm.page.remove_inner_button("Create Follow-up");
	frm.page.remove_inner_button("Set Result");
	frm.page.remove_inner_button("Open Demo Session");

	if (["Requested", "Assigned", "Scheduled", "Follow-up Required"].includes(status) && frm.doc.functional_consultant) {
		frm.page.add_inner_button(__("Schedule Demo"), () => schedule_demo_dialog(frm), __("Actions"));
	}

	if (["Demo Completed", "Follow-up Required"].includes(status)) {
		// same rule as the portal: once a follow-up exists for this request,
		// the button disappears so duplicates can never be created
		frappe.db.get_value("Demo Follow Up", { demo_request: frm.doc.name }, "name", (r) => {
			if (!(r && r.name)) {
				frm.page.add_inner_button(__("Create Follow-up"), () => follow_up_dialog(frm, null), __("Actions"));
			}
		});
		frm.page.add_inner_button(__("Set Result"), () => result_dialog(frm), __("Actions"));
	}

	if (["Scheduled", "Demo In Progress", "Demo Completed", "Follow-up Required"].includes(status)) {
		frappe.db.get_value(
			"Demo Session",
			{ demo_request: frm.doc.name, demo_status: ["in", ["Scheduled", "In Progress"]] },
			"name",
			(r) => {
				if (r && r.name) {
					frm.page.add_inner_button(__("Open Demo Session"), () => {
						frappe.set_route("Form", "Demo Session", r.name);
					}, __("Actions"));
				}
			}
		);
	}
}

function hide_status_actions(frm) {
	// The status is driven by the workflow; never let users edit it directly.
	frm.set_df_property("status", "read_only", 1);
}

function schedule_demo_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Schedule Demo"),
		fields: [
			{ fieldname: "functional_consultant", label: __("Functional Consultant"), fieldtype: "Read Only", default: frm.doc.functional_consultant },
			{ fieldname: "interested_module", label: __("Interested Template"), fieldtype: "Select", default: frm.doc.interested_module, options: ["", "Law Management", "Hospitality", "Medical Store", "Retail & Supermarket", "Manufacturing", "Education", "Healthcare", "Real Estate", "Logistics & Transport", "Agriculture", "IT Services", "Banking & Finance", "Food & Beverage", "Construction", "Energy & Utilities", "Other"] },
			{ fieldname: "scheduled_date", label: __("Scheduled Date"), fieldtype: "Date", reqd: 1, default: frm.doc.preferred_demo_date },
			{ fieldname: "start_time", label: __("Start Time"), fieldtype: "Time", default: frm.doc.preferred_demo_time },
			{ fieldname: "end_time", label: __("End Time"), fieldtype: "Time" },
			{ fieldname: "meeting_link", label: __("Meeting Link"), fieldtype: "Data" },
		],
		primary_action_label: __("Schedule"),
		primary_action(values) {
			dialog.hide();
			frappe.call({
				method: "functional_demo.api.schedule_demo",
				args: {
					demo_request: frm.doc.name,
					scheduled_date: values.scheduled_date,
					start_time: values.start_time,
					end_time: values.end_time,
					meeting_link: values.meeting_link,
					interested_module: values.interested_module,
				},
				callback(r) {
					if (r.message) frm.reload_doc();
				},
			});
		},
	});
	dialog.show();
}

function follow_up_dialog(frm, session_name) {
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
				method: "functional_demo.api.create_demo_follow_up",
				args: {
					demo_request: frm.doc.name,
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

function result_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Set Final Result"),
		fields: [
			{ fieldname: "result", label: __("Result"), fieldtype: "Select", reqd: 1, options: ["Converted", "Not Interested", "Closed"] },
		],
		primary_action_label: __("Set Result"),
		primary_action(values) {
			frappe.confirm(
				__("Mark this Demo Request as {0}?", [values.result]),
				() => {
					dialog.hide();
					frappe.call({
						method: "functional_demo.api.set_demo_result",
						args: { demo_request: frm.doc.name, result: values.result },
						callback() {
							frm.reload_doc();
						},
					});
				}
			);
		},
	});
	dialog.show();
}
