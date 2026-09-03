/**
 * Website / chatbot connect API.
 *
 *   GET  /api/v1/website-connect
 *   POST /api/v1/website-connect
 *   POST /api/v1/website-connect/verify
 *   GET  /api/v1/website-connect/wordpress-plugin
 */
import { request, BASE } from "./_client";

export function getWebsiteConnection(token) {
  return request("/api/v1/website-connect", { token });
}

export function connectWebsite(token, { website_url, platform }) {
  const body = { website_url };
  if (platform) body.platform = platform;
  return request("/api/v1/website-connect", { method: "POST", token, body });
}

export function verifyWebsiteConnection(token) {
  return request("/api/v1/website-connect/verify", { method: "POST", token });
}

export function wordpressPluginDownloadUrl() {
  return `${BASE}/api/v1/website-connect/wordpress-plugin`;
}
