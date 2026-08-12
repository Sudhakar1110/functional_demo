/* Portal pages: tiny vanilla-JS helpers (AJAX to whitelisted APIs + sidebar toggle).
   Loaded on website pages via hooks.web_include_js. */

(function () {
	"use strict";

	function csrf() {
		var m = document.querySelector('meta[name="csrf-token"]');
		if (m) return m.getAttribute("content") || "";
		return window.csrf_token || (window.frappe && frappe.csrf_token) || "";
	}

	/* Show a centered modal popup (used for errors / attention messages). */
	window.portalModal = function (title, message, type) {
		type = type || "err";
		var old = document.getElementById("portal-modal");
		if (old) old.remove();
		var overlay = document.createElement("div");
		overlay.id = "portal-modal";
		overlay.className = "portal-modal show";
		var card = document.createElement("div");
		card.className = "pm-card pm-" + type;
		var icon = document.createElement("div");
		icon.className = "pm-icon";
		icon.textContent = type === "ok" ? "\u2713" : "!";
		var h = document.createElement("h3");
		h.className = "pm-title";
		h.textContent = title || (type === "ok" ? "Done" : "Something went wrong");
		var p = document.createElement("p");
		p.className = "pm-msg";
		p.textContent = message || "";
		var btn = document.createElement("button");
		btn.type = "button";
		btn.className = "btn-portal pm-btn";
		btn.textContent = "Got it";
		card.appendChild(icon);
		card.appendChild(h);
		card.appendChild(p);
		card.appendChild(btn);
		overlay.appendChild(card);
		document.body.appendChild(overlay);
		function close() {
			overlay.remove();
			document.removeEventListener("keydown", onKey, true);
		}
		function onKey(e) { if (e.key === "Escape") close(); }
		overlay.addEventListener("click", function (e) { if (e.target === overlay) close(); });
		btn.addEventListener("click", close);
		document.addEventListener("keydown", onKey, true);
	};

	/* Show a toast-style alert (auto-hides after 6s); errors open the modal popup. */
	window.portalAlert = function (msg, type) {
		if (type === "err") {
			window.portalModal("Please check your input", msg, "err");
			return;
		}
		var el = document.getElementById("portal-alert");
		if (!el) {
			el = document.createElement("div");
			el.id = "portal-alert";
			el.className = "portal-alert";
			document.body.appendChild(el);
		}
		el.textContent = msg;
		el.className = "portal-alert show " + (type || "ok");
		clearTimeout(el._t);
		el._t = setTimeout(function () { el.classList.remove("show"); }, 6000);
	};

	/* Call a whitelisted API method: window.portalCall("functional_demo.api.x", {..}) */
	window.portalCall = function (method, args) {
		return fetch("/api/method/" + method, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": csrf(),
			},
			body: JSON.stringify({ args: args || {} }),
			credentials: "same-origin",
		})
		.then(function (r) {
			return r.text().then(function (txt) {
				var data = {};
				try {
					data = JSON.parse(txt) || {};
				} catch (e) {
					// not JSON (e.g. an HTML 500 page) - keep the raw text for diagnosis
					data = { __raw: txt || "" };
				}
				return { ok: r.ok, data: data };
			});
		})
		.then(function (res) {
			var data = res.data;
			var serverMsgs = [];
			try {
				serverMsgs = JSON.parse(data._server_messages || "[]");
			} catch (e) { serverMsgs = []; }
			var plain = function (html) {
				var d = document.createElement("div");
				d.innerHTML = html || "";
				return d.textContent || d.innerText || "";
			};
			/* Frappe puts the real traceback in data.exc on unhandled exceptions.
			   Pull the last meaningful line ("ErrorType: message") so the popup
			   shows the actual cause instead of a generic message. */
			var realError = function () {
				if (data.message) return "";
				var exc = String(data.exc || "").split("\n").filter(Boolean);
				for (var i = exc.length - 1; i >= 0; i--) {
					var line = exc[i].trim();
					if (!/^(File |Traceback|During handling|The above|\s*\^)/.test(line) && line.length > 2) {
						return line;
					}
				}
				return "";
			};
			/* For non-JSON error pages (HTML 500s) grab the first readable line
			   so the real failure is never hidden behind a generic message. */
			var rawHint = function () {
				if (!data.__raw) return "";
				var txt = String(data.__raw);
				var lines = txt.split("\n").map(function (l) { return l.trim(); }).filter(Boolean);
				for (var i = 0; i < lines.length; i++) {
					var line = lines[i].replace(/<[^>]+>/g, "").trim();
					if (line && line.length > 3 && !/^(<!|DOCTYPE|html|head|body|meta|script)/i.test(line)) {
						return line.slice(0, 300);
					}
				}
				return txt.slice(0, 300);
			};
			var isError = !res.ok || data.exc_type || data.raise_exception;
			if (isError) {
				var errMsg =
					data.message ||
					(serverMsgs.length ? plain(serverMsgs[0]) : "") ||
					realError() ||
					rawHint() ||
					"Something went wrong. Please try again.";
				window.portalModal(data.title || "Something went wrong", errMsg, "err");
				var err = new Error(errMsg);
				err.exc_type = data.exc_type;
				throw err;
			}
				serverMsgs.forEach(function (s) {
					var t = plain(s);
					if (t) window.portalAlert(t, "ok");
				});
				return data.message;
			})
			.catch(function (err) {
				if (err instanceof TypeError) {
					window.portalModal("Network error", "Please check your connection and try again.", "err");
				}
				throw err;
			});
	};

	/* Mobile sidebar toggle */
	document.addEventListener("DOMContentLoaded", function () {
		var toggle = document.getElementById("sidebar-toggle");
		var sidebar = document.getElementById("portal-sidebar");
		var overlay = document.querySelector(".sidebar-overlay");
		if (toggle && sidebar) {
			toggle.addEventListener("click", function () {
				sidebar.classList.toggle("open");
				if (overlay) overlay.classList.toggle("show");
			});
		}
		if (overlay) {
			overlay.addEventListener("click", function () {
				sidebar.classList.remove("open");
				overlay.classList.remove("show");
			});
		}
	});

	/* Set the browser-tab favicon to the brand logo.
	   Replace any favicon link the base template already emitted so the
	   brand logo is the single deterministic tab icon. */
	(function () {
		var logo = "/images/favicon.jpg";
		var existing = document.querySelectorAll('link[rel*="icon"]');
		for (var i = 0; i < existing.length; i++) existing[i].remove();
		var link = document.createElement("link");
		link.rel = "icon";
		link.type = "image/jpeg";
		link.href = logo;
		document.head.appendChild(link);
		var apple = document.createElement("link");
		apple.rel = "apple-touch-icon";
		apple.href = "/images/brand_logo.jpg";
		document.head.appendChild(apple);
	})();
})();
