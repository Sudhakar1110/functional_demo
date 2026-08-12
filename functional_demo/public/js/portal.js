/* Portal pages: tiny vanilla-JS helpers (AJAX to whitelisted APIs + sidebar toggle).
   Loaded on website pages via hooks.web_include_js. */

(function () {
	"use strict";

	function csrf() {
		var m = document.querySelector('meta[name="csrf-token"]');
		if (m) return m.getAttribute("content") || "";
		return window.csrf_token || (window.frappe && frappe.csrf_token) || "";
	}

	/* Show a toast-style alert (auto-hides after 6s). */
	window.portalAlert = function (msg, type) {
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
			.then(function (r) { return r.json(); })
			.then(function (data) {
				var serverMsgs = [];
				try {
					serverMsgs = JSON.parse(data._server_messages || "[]");
				} catch (e) { serverMsgs = []; }
				serverMsgs.forEach(function (s) {
					var d = document.createElement("div");
					d.innerHTML = s;
					window.portalAlert(d.textContent || d.innerText || "", "ok");
				});
				if (data.exc_type) {
					var errMsg = "Something went wrong. Please try again.";
					if (serverMsgs.length) {
						var d = document.createElement("div");
						d.innerHTML = serverMsgs[0];
						errMsg = d.textContent || d.innerText || errMsg;
					}
					window.portalAlert(errMsg, "err");
					var err = new Error(errMsg);
					err.exc_type = data.exc_type;
					throw err;
				}
				return data.message;
			})
			.catch(function (err) {
				if (err instanceof TypeError) {
					window.portalAlert("Network error. Please check your connection and try again.", "err");
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
		var logo = "/assets/functional_demo/images/favicon.jpg";
		var existing = document.querySelectorAll('link[rel*="icon"]');
		for (var i = 0; i < existing.length; i++) existing[i].remove();
		var link = document.createElement("link");
		link.rel = "icon";
		link.type = "image/jpeg";
		link.href = logo;
		document.head.appendChild(link);
		var apple = document.createElement("link");
		apple.rel = "apple-touch-icon";
		apple.href = "/assets/functional_demo/images/brand_logo.jpg";
		document.head.appendChild(apple);
	})();
})();
