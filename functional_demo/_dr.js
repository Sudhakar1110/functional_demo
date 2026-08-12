
(function () {
	"use strict";
	{
	function fillContact(kind, value) {
		if (!value) return;
		portalCall(kind === "customer" ? "functional_demo.api.get_customer_details" : "functional_demo.api.get_lead_details",
			kind === "customer" ? { customer: value } : { lead: value })
			.then(function (data) {
				if (!data) return;
				if (data.contact_person && !document.getElementById("contact_person").value) {
					document.getElementById("contact_person").value = data.contact_person;
				}
				if (data.contact_number && !document.getElementById("contact_number").value) {
					document.getElementById("contact_number").value = data.contact_number;
				}
				if (data.email && !document.getElementById("email").value) {
					document.getElementById("email").value = data.email;
				}
			});
	}

	document.getElementById("customer").addEventListener("change", function () {
		fillContact("customer", this.value);
	});
	document.getElementById("lead").addEventListener("change", function () {
		fillContact("lead", this.value);
	});

	/* Arrived from My Leads with a lead pre-selected (?lead=...) - auto-fill
	   the contact details right away instead of waiting for a change event. */
	var preLead = document.getElementById("lead").value.trim();
	if (preLead) fillContact("lead", preLead);

	document.getElementById("dr-form").addEventListener("submit", function (e) {
		e.preventDefault();
		var customer = document.getElementById("customer").value.trim();
		var lead = document.getElementById("lead").value.trim();
		var consultant = document.getElementById("functional_consultant").value;
		if (!customer && !lead) {
			portalAlert("Please select a Customer or a Lead.", "err");
			return;
		}
		if (!consultant) {
			portalAlert("Please select a Functional Consultant to run this demo.", "err");
			return;
		}
		var btn = document.getElementById("btn-create");
		btn.disabled = true; btn.textContent = "Creating...";
		portalCall("functional_demo.api.create_demo_request", {
			customer: customer || null,
			lead: lead || null,
			functional_consultant: consultant,
			contact_person: document.getElementById("contact_person").value,
			contact_number: document.getElementById("contact_number").value,
			email: document.getElementById("email").value,
			interested_module: document.getElementById("interested_module").value,
			priority: document.getElementById("priority").value,
			demo_type: document.getElementById("demo_type").value,
			preferred_demo_date: document.getElementById("preferred_demo_date").value,
			preferred_demo_time: document.getElementById("preferred_demo_time").value,
			customer_requirements: document.getElementById("customer_requirements").value,
			business_process_requirements: document.getElementById("business_process_requirements").value,
			sales_remarks: document.getElementById("sales_remarks").value,
		}).then(function (res) {
			if (res && res.name) {
				window.location.href = "/sales_portal/demo_request?name=" + res.name;
			} else {
				btn.disabled = false; btn.textContent = "Create Demo Request";
			}
		}).catch(function () {
			btn.disabled = false; btn.textContent = "Create Demo Request";
		});
	});
	}else{
	var DOC_NAME = ""DEMO-1"";

	function toggle(id) {
		var el = document.getElementById(id);
		if (el) el.style.display = el.style.display === "none" ? "block" : "none";
	}

	{
	document.getElementById("btn-assign").addEventListener("click", function () {
		var consultant = document.getElementById("assign-consultant").value;
		if (!consultant) { portalAlert("Please select a consultant.", "err"); return; }
		var btn = this; btn.disabled = true;
		portalCall("functional_demo.api.assign_consultant", { demo_request: DOC_NAME, consultant: consultant })
			.then(function () { window.location.reload(); })
			.catch(function () { btn.disabled = false; });
	});
	}

	{
	var btnScheduleToggle = document.getElementById("btn-toggle-schedule");
	var btnSchedule = document.getElementById("btn-schedule");
	if (btnScheduleToggle) btnScheduleToggle.addEventListener("click", function () { toggle("form-schedule"); });
	if (btnSchedule) btnSchedule.addEventListener("click", function () {
		var date = document.getElementById("sch-date").value;
		if (!date) { portalAlert("Please pick a scheduled date.", "err"); return; }
		var btn = this; btn.disabled = true;
		portalCall("functional_demo.api.schedule_demo", {
			demo_request: DOC_NAME,
			scheduled_date: date,
			start_time: document.getElementById("sch-start").value,
			end_time: document.getElementById("sch-end").value,
			meeting_link: document.getElementById("sch-link").value,
		}).then(function () { window.location.reload(); }).catch(function () { btn.disabled = false; });
	});
	}

	{
	document.getElementById("btn-toggle-followup").addEventListener("click", function () { toggle("form-followup"); });
	document.getElementById("btn-followup").addEventListener("click", function () {
		var date = document.getElementById("fu-date").value;
		if (!date) { portalAlert("Please pick a follow-up date.", "err"); return; }
		var btn = this; btn.disabled = true;
		portalCall("functional_demo.api.create_demo_follow_up", {
			demo_request: DOC_NAME,
			follow_up_date: date,
			next_action: document.getElementById("fu-next").value,
			assigned_to: document.getElementById("fu-assignee").value,
		}).then(function () { window.location.reload(); }).catch(function () { btn.disabled = false; });
	});

	document.getElementById("btn-toggle-result").addEventListener("click", function () { toggle("form-result"); });
	document.getElementById("btn-result").addEventListener("click", function () {
		var result = document.getElementById("result-value").value;
		var btn = this; btn.disabled = true;
		portalCall("functional_demo.api.set_demo_result", { demo_request: DOC_NAME, result: result })
			.then(function () { window.location.reload(); }).catch(function () { btn.disabled = false; });
	});
	}
	}
})();
