/* Web Push service worker - shows OS-level popups (with sound) even when the
   user is on another page or site entirely, as long as the browser is running.
   Served from the site root (/service_worker.js) so its scope covers every
   page of the site. The push payload is {title, body, url, sound}. */
self.addEventListener("install", function () {
	self.skipWaiting();
});

self.addEventListener("activate", function (event) {
	event.waitUntil(self.clients.claim());
});

self.addEventListener("push", function (event) {
	var data = {};
	try {
		data = event.data ? event.data.json() : {};
	} catch (e) { /* non-JSON payload - use defaults */ }
	var title = data.title || "New notification";
	var options = {
		body: data.body || "Sales & Functional Demo Management",
		icon: "/assets/functional_demo/images/brand_logo.jpg",
		badge: "/assets/functional_demo/images/brand_logo.jpg",
		sound: data.sound || "/chime.wav",
		data: { url: data.url || "/demo_portal" },
	};
	event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", function (event) {
	event.notification.close();
	var url = (event.notification.data && event.notification.data.url) || "/demo_portal";
	event.waitUntil(
		self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (clientList) {
			for (var i = 0; i < clientList.length; i++) {
				var client = clientList[i];
				if ("focus" in client) {
					client.focus();
					if ("navigate" in client && client.url.indexOf(location.origin) === 0) {
						client.navigate(url);
					}
					return;
				}
			}
			return self.clients.openWindow(url);
		})
	);
});
