frappe.pages["demo-feedback"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Template Feedback"),
		single_column: true,
	});

	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

	function row_cells(s) {
		const items = (s.feedback_items || [])
			.map((it) => `<li><strong>${esc(it.item_type)}:</strong> ${esc(it.description)}</li>`)
			.join("");
		return `
			<td><strong>${esc(s.customer_display || s.customer || s.lead || "-")}</strong><div class="demo-fb-muted">${esc(s.consultant_display || "-")}</div></td>
			<td class="demo-fb-muted">${esc(s.date_display || "-")}</td>
			<td class="demo-fb-wrap" style="max-width: 320px;">${esc(s.overall_feedback || "-")}</td>
			<td>${esc(s.interested || "-")}</td>
			<td>${esc(s.requirements_met || "-")}</td>
			<td>${items ? `<ul class="demo-fb-items">${items}</ul>` : '<span class="demo-fb-muted">-</span>'}</td>
			<td>${esc(s.final_result || "-")}</td>`;
	}

	function template_card(t) {
		const chips = [t.erpnext_module, t.business_area].filter(Boolean)
			.map((c) => `<span class="demo-fb-chip">${esc(c)}</span>`)
			.join("");
		const rows = (t.sessions || [])
			.map((s) => `<tr>${row_cells(s)}</tr>`)
			.join("");
		return `
			<div class="demo-fb-card">
				<div class="demo-fb-card-head">
					<div>
						<h3>${esc(t.template_name)}</h3>
						<div class="demo-fb-meta">${chips}<span>Owner: ${esc(t.owner_display || "-")}</span><span>Feedback: ${(t.sessions || []).length}</span></div>
					</div>
					<span class="demo-fb-badge ${t.is_active ? "active" : "inactive"}">${t.is_active ? __("Active") : __("Inactive")}</span>
				</div>
				${t.demo_objective ? `<p class="demo-fb-objective">${esc(t.demo_objective)}</p>` : ""}
				${(t.sessions || []).length ? `
				<table class="demo-fb-table">
					<thead><tr><th>${__("Customer")}</th><th>${__("Date")}</th><th>${__("Overall Feedback")}</th><th>${__("Interested")}</th><th>${__("Requirements Met")}</th><th>${__("Questions / Changes")}</th><th>${__("Result")}</th></tr></thead>
					<tbody>${rows}</tbody>
				</table>` : `<p class="demo-fb-empty">${__("No feedback recorded for this template yet.")}</p>`}
			</div>`;
	}

	function render(templates) {
		const total = templates.length;
		const count = templates.reduce((n, t) => n + (t.sessions || []).length, 0);
		page.main.empty().append(`
			<div class="demo-fb-page">
				<div class="demo-fb-summary">${__("Template Feedback ({0} templates, {1} feedback entries)", [total, count])} — ${__("the same view is available in the portal at /feedback")}.</div>
				${templates.map(template_card).join("")}
				${templates.length ? "" : `<div class="demo-fb-card"><p class="demo-fb-empty">${__("No demo templates found yet. Create templates and run demos - feedback recorded against them will appear here.")}</p></div>`}
			</div>`);
	}

	function load() {
		page.main.empty().append(`<div class="demo-fb-page"><p class="demo-fb-empty">${__("Loading template feedback…")}</p></div>`);
		frappe.call({
			method: "functional_demo.api.get_template_feedback",
			callback(r) {
				render(r.message || []);
			},
			error() {
				page.main.empty().append(`<div class="demo-fb-page"><p class="demo-fb-empty">${__("Could not load template feedback. Please check your permissions and try again.")}</p></div>`);
			},
		});
	}

	page.set_primary_action(__("Refresh"), () => load(), "octicon octicon-sync");
	load();
};
