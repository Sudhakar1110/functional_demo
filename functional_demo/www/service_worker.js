/* Web Push service worker - shows OS-level popups (with sound) even when the
   user is on another page or site entirely, as long as the browser is running.
   Served from the site root (/service_worker.js) so its scope covers every
   page of the site. The push payload is {title, body, url, sound, name}. */
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
	var name = data.name || "";
	var options = {
		body: data.body || "Sales & Functional Demo Management",
		icon: "/assets/functional_demo/images/brand_logo.jpg",
		badge: "/assets/functional_demo/images/brand_logo.jpg",
		sound: data.sound || "/chime.wav",
		/* deterministic tag: the same notification replaces any duplicate OS
		   popup instead of stacking a second one */
		tag: "demo-portal-" + (name || Date.now()),
		data: { url: data.url || "/demo_portal", name: name, subject: title },
	};
	event.waitUntil(
		self.registration.showNotification(title, options).then(function () {
			/* the notification 'sound' option is ignored on many desktop
			   platforms - poke every open portal page to play the chime so
			   the sound is guaranteed (the page dedupes against the websocket
			   path, so it never rings twice) */
			return self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (clients) {
				for (var i = 0; i < clients.length; i++) {
					clients[i].postMessage({ type: "demo-portal-chime", name: name, subject: title });
				}
			});
		})
	);
});

self.addEventListener("notificationclick", function (event) {
	/* read-only notifications: clicking an OS popup only dismisses it and
	   never navigates the user away from what they are doing */
	event.notification.close();
});
