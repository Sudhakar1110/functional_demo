frappe.pages["demo-feedback"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Demo Feedback"),
		single_column: true,
	});

	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

	// every feedback entry (loaded once), plus the active template filter
	let allEntries = [];
	let activeTemplate = "";

	page.add_field({
		fieldtype: "Select",
		label: __("Template"),
		fieldname: "template_filter",
		options: [{ label: __("All Templates"), value: "" }],
		change() {
			activeTemplate = this.value || "";
			render(currentEntries());
		},
	});

	function currentEntries() {
		if (!activeTemplate) return allEntries;
		return allEntries.filter((f) => (f.template || "No Template") === activeTemplate);
	}

	function row_cells(f) {
		const items = (f.feedback_items || [])
			.map((it) => `<li><strong>${esc(it.item_type)}:</strong> ${esc(it.description)}</li>`)
			.join("");
		return `
			<td><a href="/app/demo-session/${esc(f.name)}" target="_blank">${esc(f.name)}</a></td>
			<td><strong>${esc(f.customer || "-")}</strong><div class="demo-fb-muted">${esc(f.consultant || "-")}</div></td>
			<td><span class="chip">${esc(f.template || "No Template")}</span></td>
			<td class="demo-fb-muted">${esc(f.date || "-")}</td>
			<td class="demo-fb-wrap" style="max-width: 320px;">${esc(f.overall_feedback || "-")}</td>
			<td>${esc(f.interested || "-")}</td>
			<td>${esc(f.requirements_met || "-")}</td>
			<td>${items ? `<ul class="demo-fb-items">${items}</ul>` : '<span class="demo-fb-muted">-</span>'}</td>
			<td>${esc(f.final_result || "-")}</td>`;
	}

	function render(entries) {
		const rows = entries.map((f) => `<tr>${row_cells(f)}</tr>`).join("");
		page.main.empty().append(`
			<div class="demo-fb-page">
				<div class="demo-fb-summary">${__("Demo Feedback ({0} entries){1}", [
					entries.length,
					activeTemplate ? ` — ${__("filtered by template: {0}", [esc(activeTemplate)])}` : "",
				])} — ${__("the same view is available in the portal at /feedback")}.</div>
				<div class="demo-fb-card">
					${entries.length ? `
					<table class="demo-fb-table">
						<thead><tr><th>${__("Session")}</th><th>${__("Leads")}</th><th>${__("Template")}</th><th>${__("Date")}</th><th>${__("Overall Feedback")}</th><th>${__("Interested")}</th><th>${__("Requirements Met")}</th><th>${__("Questions / Changes")}</th><th>${__("Result")}</th></tr></thead>
						<tbody>${rows}</tbody>
					</table>` : `<p class="demo-fb-empty">${__("No feedback recorded yet. Feedback captured when demos are completed will appear here.")}</p>`}
				</div>
			</div>`);
	}

	function load() {
		page.main.empty().append(`<div class="demo-fb-page"><p class="demo-fb-empty">${__("Loading demo feedback…")}</p></div>`);
		frappe.call({
			method: "functional_demo.api.get_demo_feedback",
			callback(r) {
				allEntries = r.message || [];
				// populate the template filter from the loaded data (Law, Hospitality, ...)
				const templates = [
					...new Set(allEntries.map((f) => f.template || "No Template").filter(Boolean)),
				].sort((a, b) => a.localeCompare(b));
				page.fields_dict.template_filter.set_options(
					[{ label: __("All Templates"), value: "" }].concat(
						templates.map((t) => ({ label: t, value: t }))
					)
				);
				render(currentEntries());
			},
			error() {
				page.main.empty().append(`<div class="demo-fb-page"><p class="demo-fb-empty">${__("Could not load demo feedback. Please check your permissions and try again.")}</p></div>`);
			},
		});
	}

	page.set_primary_action(__("Refresh"), () => load(), "octicon octicon-sync");
	load();
};
