frappe.ui.form.on("Demo Follow Up", {
	refresh(frm) {
		frm.page.remove_inner_button("Add Note");
		frm.page.remove_inner_button("Mark Complete");
		frm.page.remove_inner_button("Set Outcome");
		frm.page.add_inner_button(__("Add Note"), () => add_note_dialog(frm), __("Actions"));
		frm.page.add_inner_button(__("Set Outcome"), () => outcome_dialog(frm), __("Actions"));

		if (["Open", "In Progress"].includes(frm.doc.status)) {
			frm.page.add_inner_button(__("Mark Complete"), () => {
				frm.set_value("status", "Completed");
				frm.save();
			}, __("Actions"));
		}
	},
});

function outcome_dialog(frm) {
	// Same outcome options as the portal's update_follow_up quick action.
	const dialog = new frappe.ui.Dialog({
		title: __("Set Follow-up Outcome"),
		fields: [
			{
				fieldname: "outcome",
				label: __("Outcome"),
				fieldtype: "Select",
				reqd: 1,
				options: ["Pending", "Additional Discussion", "Additional Demo Required", "Converted:Demo Completed", "Not Interested", "Closed"],
				default: frm.doc.outcome || "Pending",
			},
			{ fieldname: "remarks", label: __("Remarks"), fieldtype: "Small Text", default: frm.doc.remarks },
		],
		primary_action_label: __("Set Outcome"),
		primary_action(values) {
			dialog.hide();
			frm.set_value("outcome", values.outcome);
			if (values.remarks !== frm.doc.remarks) frm.set_value("remarks", values.remarks);
			frm.save();
		},
	});
	dialog.show();
}

function add_note_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Add Discussion Note"),
		fields: [{ fieldname: "note", label: __("Note"), fieldtype: "Small Text", reqd: 1 }],
		primary_action_label: __("Add"),
		primary_action(values) {
			dialog.hide();
			frm.doc.discussion_notes = frm.doc.discussion_notes || [];
			frm.doc.discussion_notes.push({
				note_date: frappe.datetime.now_datetime(),
				note_by: frappe.session.user,
				note: values.note,
			});
			frm.refresh_field("discussion_notes");
			frm.save();
		},
	});
	dialog.show();
}
