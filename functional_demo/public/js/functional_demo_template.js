frappe.ui.form.on("Functional Demo Template", {
	refresh(frm) {
		frm.set_query("functional_consultant", () => {
			return { filters: { status: "Active" } };
		});

		if (!frm.is_new()) {
			frm.dashboard.clear_headline();
			frm.dashboard.set_headline(
				__("This template is reusable. Sessions that already used it keep their own copy of the content - editing it here will not change past demos.")
			);
		}
	},
});
