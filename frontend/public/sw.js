/**
 * AgentNexLiFy dashboard service worker.
 *
 * Sole purpose: Web Push for pending-approval notifications. No caching, no
 * offline behavior — keep deploys boring.
 */

const DASHBOARD_URL = "/dashboard/agent-os";

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch {
    payload = { body: event.data ? event.data.text() : "" };
  }

  const title = payload.title || "AgentNexLiFy";
  const options = {
    body: payload.body || "Your AI staff needs your attention.",
    icon: "/logo.png",
    badge: "/logo.png",
    data: { url: payload.url || DASHBOARD_URL },
    tag: "anx-pending-approval",
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl =
    (event.notification.data && event.notification.data.url) || DASHBOARD_URL;
  const targetPath = targetUrl.replace(/^https?:\/\/[^/]+/, "") || DASHBOARD_URL;

  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((windowClients) => {
        for (const client of windowClients) {
          const clientPath = new URL(client.url).pathname;
          if (clientPath.startsWith("/dashboard") && "focus" in client) {
            client.navigate(targetPath);
            return client.focus();
          }
        }
        return self.clients.openWindow(targetPath);
      }),
  );
});
