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

	// clicking a template chip opens that template's own section (same as the
	// dropdown) - the chip carries the template name in a data attribute; the
	// "View all templates" clear link uses an empty data-template
	function bindChipClicks() {
		page.main.off("click.demo-fb-chip").on("click.demo-fb-chip", ".demo-fb-chip, .demo-fb-clear", (e) => {
			e.preventDefault();
			const t = $(e.currentTarget).data("template") || "";
			activeTemplate = t;
			page.fields_dict.template_filter.set_value(t);
			render(currentEntries());
		});
	}

	function row_cells(f) {
		const items = (f.feedback_items || [])
			.map((it) => `<li><strong>${esc(it.item_type)}:</strong> ${esc(it.description)}</li>`)
			.join("");
		return `
			<td><a href="/app/demo-session/${esc(f.name)}" target="_blank">${esc(f.name)}</a></td>
			<td><strong>${esc(f.customer || "-")}</strong><div class="demo-fb-muted">${esc(f.consultant || "-")}</div></td>
			<td><a class="demo-fb-chip" href="#" data-template="${esc(f.template || "No Template")}" title="${__("Show {0} feedback", [esc(f.template || "No Template")])}"><span class="chip">${esc(f.template || "No Template")}</span></a></td>
			<td class="demo-fb-muted">${esc(f.date || "-")}</td>
			<td class="demo-fb-wrap" style="max-width: 320px;">${esc(f.overall_feedback || "-")}</td>
			<td>${esc(f.interested || "-")}</td>
			<td>${esc(f.requirements_met || "-")}</td>
			<td>${items ? `<ul class="demo-fb-items">${items}</ul>` : '<span class="demo-fb-muted">-</span>'}</td>
			<td>${esc(f.final_result || "-")}</td>`;
	}

	function count(entries, field, value) {
		return entries.filter((f) => (f[field] || "") === value).length;
	}

	// when a template is selected, show its overall picture in a separate
	// section above the list (entries + interested / requirements-met split)
	function summaryHTML(entries) {
		if (!activeTemplate) return "";
		return `
			<div class="demo-fb-section">
				<div class="demo-fb-section-head">
					<div>
						<h3 class="demo-fb-section-title">${esc(activeTemplate)} — ${__("Overall Feedback")}</h3>
						<p class="demo-fb-section-sub">${__("Everything recorded for this template, newest first.")}</p>
					</div>
					<a class="demo-fb-clear" href="#" data-template="">${__("View all templates")}</a>
				</div>
				<div class="demo-fb-summary-grid">
					<div class="demo-fb-summary-card"><div class="s-label">${__("Feedback Entries")}</div><div class="s-value">${entries.length}</div></div>
					<div class="demo-fb-summary-card s-green"><div class="s-label">${__("Interested")}</div><div class="s-value">${count(entries, "interested", "Interested")}</div></div>
					<div class="demo-fb-summary-card s-red"><div class="s-label">${__("Not Interested")}</div><div class="s-value">${count(entries, "interested", "Not Interested")}</div></div>
					<div class="demo-fb-summary-card s-blue"><div class="s-label">${__("Requirements Fully Met")}</div><div class="s-value">${count(entries, "requirements_met", "Fully Met")}</div></div>
					<div class="demo-fb-summary-card s-amber"><div class="s-label">${__("Partially Met")}</div><div class="s-value">${count(entries, "requirements_met", "Partially Met")}</div></div>
					<div class="demo-fb-summary-card s-red"><div class="s-label">${__("Not Met")}</div><div class="s-value">${count(entries, "requirements_met", "Not Met")}</div></div>
					<div class="demo-fb-summary-card s-teal"><div class="s-label">${__("Demo Completed")}</div><div class="s-value">${count(entries, "final_result", "Converted")}</div></div>
				</div>
			</div>`;
	}

	function render(entries) {
		const rows = entries.map((f) => `<tr>${row_cells(f)}</tr>`).join("");
		page.main.empty().append(`
			<div class="demo-fb-page">
				<div class="demo-fb-summary">${__("Demo Feedback ({0} entries){1}", [
					entries.length,
					activeTemplate ? ` — ${__("filtered by template: {0}", [esc(activeTemplate)])}` : "",
				])} — ${__("the same view is available in the portal at /feedback")}.</div>
				${summaryHTML(entries)}
				<div class="demo-fb-card">
					${entries.length ? `
					<table class="demo-fb-table">
						<thead><tr><th>${__("Session")}</th><th>${__("Leads")}</th><th>${__("Template")}</th><th>${__("Date")}</th><th>${__("Overall Feedback")}</th><th>${__("Interested")}</th><th>${__("Requirements Met")}</th><th>${__("Questions / Changes")}</th><th>${__("Result")}</th></tr></thead>
						<tbody>${rows}</tbody>
					</table>` : `<p class="demo-fb-empty">${__("No feedback recorded yet. Feedback captured when demos are completed will appear here.")}</p>`}
				</div>
			</div>`);
		bindChipClicks();
	}

	function load() {
		page.main.empty().append(`<div class="demo-fb-page"><p class="demo-fb-empty">${__("Loading demo feedback…")}</p></div>`);
		frappe.call({
			method: "functional_demo.api.get_demo_feedback",
			callback(r) {
				allEntries = r.message || [];
				// populate the template filter from the loaded data (Law Management, Hospitality, ...)
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
