frappe.listview_settings["Demo Session"] = {
	add_fields: ["demo_status", "scheduled_date", "customer", "functional_consultant"],
	get_indicator: function (doc) {
		const map = {
			Scheduled: [__("Scheduled"), "orange"],
			"In Progress": [__("In Progress"), "yellow"],
			Completed: [__("Completed"), "green"],
			Rescheduled: [__("Rescheduled"), "blue"],
			Cancelled: [__("Cancelled"), "red"],
			Closed: [__("Closed"), "grey"],
		};
		return map[doc.demo_status] || [__(doc.demo_status), "grey"];
	},
};
