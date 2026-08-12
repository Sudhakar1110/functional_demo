
(function () {
	"use strict";
	{
	/* One-click: create a consultant profile linked to the current user. */
	var linkBtn = document.getElementById("btn-link-my-user");
	if (linkBtn) {
		linkBtn.addEventListener("click", function () {
			var btn = this;
			var name = (document.getElementById("link-consultant-name").value || "").trim();
			var spec = document.getElementById("link-specialization").value;
			btn.disabled = true;
			btn.textContent = "Linking...";
			portalCall("functional_demo.api.create_consultant_profile", {
				user: "u@x.com",
				consultant_name: name || null,
				specialization: spec || null,
			}).then(function () {
				portalAlert("Consultant profile created. Loading your templates...", "ok");
				setTimeout(function () { window.location.reload(); }, 900);
			}).catch(function () {
				btn.disabled = false;
				btn.textContent = "⚡ Link my user";
			});
		});
	}
	}
	{

	function initRepeaters() {
		document.querySelectorAll(".btn-add-row").forEach(function (btn) {
			btn.addEventListener("click", function () {
				var container = document.getElementById(btn.getAttribute("data-rep"));
				if (!container) return;
				var first = container.querySelector(".rep-row");
				var clone = first.cloneNode(true);
				clone.querySelectorAll("[data-f]").forEach(function (el) { el.value = ""; });
				container.appendChild(clone);
			});
		});
		document.querySelectorAll(".repeater").forEach(function (container) {
			container.addEventListener("click", function (e) {
				if (!e.target.classList.contains("rep-del")) return;
				var rows = container.querySelectorAll(".rep-row");
				if (rows.length > 1) {
					e.target.closest(".rep-row").remove();
				} else {
					rows[0].querySelectorAll("[data-f]").forEach(function (el) { el.value = ""; });
				}
			});
		});
	}

	function collectRows(containerId, childDoctype) {
		var rows = [];
		document.querySelectorAll("#" + containerId + " .rep-row").forEach(function (row) {
			var obj = { doctype: childDoctype };
			var hasValue = false;
			row.querySelectorAll("[data-f]").forEach(function (el) {
				var f = el.getAttribute("data-f");
				var v = el.value.trim();
				if (f === "step_no" || f === "duration_min") v = v ? parseInt(v, 10) : "";
				obj[f] = v;
				if (v !== "" && v !== null && v !== undefined) hasValue = true;
			});
			if (hasValue) rows.push(obj);
		});
		return rows;
	}

	function val(id) { var el = document.getElementById(id); return el ? el.value.trim() : ""; }

	document.getElementById("template-form").addEventListener("submit", function (e) {
		e.preventDefault();
		if (!val("template_name")) { portalAlert("Template Name is required.", "err"); return; }
		var doc = {
			doctype: "Functional Demo Template",
			{
			functional_consultant: ""CONS-1"",
			}else{
			name: ""T-1"",
			}
			template_name: val("template_name"),
			erpnext_module: val("erpnext_module"),
			business_area: val("business_area"),
			demo_objective: val("demo_objective"),
			introduction: val("introduction"),
			customer_business_scenario: val("customer_business_scenario"),
			demo_agenda: val("demo_agenda"),
			demo_notes: val("demo_notes"),
			is_active: document.getElementById("is_active").checked ? 1 : 0,
			demo_steps: collectRows("steps-rep", "Template Step"),
			key_features: collectRows("features-rep", "Template Item"),
			configuration_points: collectRows("config-rep", "Template Item"),
			business_benefits: collectRows("benefits-rep", "Template Item"),
			questions_to_ask: collectRows("ask-rep", "Template Question"),
			customer_questions: collectRows("cq-rep", "Template Question"),
			faqs: collectRows("faqs-rep", "Template Question"),
			follow_up_points: collectRows("followup-rep", "Template Item"),
		};
		var btn = document.getElementById("btn-save");
		btn.disabled = true; btn.textContent = "Saving...";
		var method = "frappe.client.insert";
		portalCall(method, { doc: doc })
			.then(function (res) {
				var saved = res && res.name;
				if (!saved && res && res.docs && res.docs.length) saved = res.docs[0].name;
				window.location.href = "/functional_portal/my_templates" + (saved ? "?saved=" + saved : "");
			})
			.catch(function () { btn.disabled = false; btn.textContent = "Save"; });
	});

	initRepeaters();
	}
})();
