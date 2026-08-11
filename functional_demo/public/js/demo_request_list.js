frappe.listview_settings["Demo Request"] = {
	add_fields: ["status", "priority", "customer", "sales_person", "functional_consultant"],
	get_indicator: function (doc) {
		const map = {
			Draft: [__("Draft"), "grey"],
			Requested: [__("Requested"), "blue"],
			Assigned: [__("Assigned"), "purple"],
			Scheduled: [__("Scheduled"), "orange"],
			"Demo In Progress": [__("In Progress"), "yellow"],
			"Demo Completed": [__("Completed"), "green"],
			"Follow-up Required": [__("Follow-up Required"), "blue"],
			Converted: [__("Converted"), "green"],
			"Not Interested": [__("Not Interested"), "red"],
			Cancelled: [__("Cancelled"), "red"],
			Closed: [__("Closed"), "grey"],
		};
		return map[doc.status] || [__(doc.status), "grey"];
	},
};
