/**
 * Widget configuration, AI feedback, and website crawl API functions.
 */
import { request } from "./_client";

// --- Widget Config ---

export function fetchWidgetConfig(tenantId, token) {
  return request(`/api/v1/widget-config/${tenantId}`, { token });
}

export function updateWidgetConfig(tenantId, token, data) {
  return request(`/api/v1/auth/widget-config/${tenantId}`, {
    method: "PUT",
    token,
    body: data,
  });
}

export function toggleWidgetOnlineStatus(tenantId, token, isOnline) {
  return request(`/api/v1/widget/config/${tenantId}/online-status`, {
    method: "PUT",
    token,
    body: { is_online: isOnline },
  });
}

// --- AI Feedback ---

export function fetchAiFeedback(tenantId, token) {
  return request(`/api/v1/widget/feedback/${tenantId}`, { token });
}

export function deleteAiFeedback(tenantId, token, feedbackId) {
  return request(`/api/v1/widget/feedback/${tenantId}/${feedbackId}`, { method: "DELETE", token });
}

// --- Website Crawl ---

export function startWebsiteCrawl(tenantId, token) {
  return request(`/api/v1/crawl/${tenantId}/start`, { method: "POST", token });
}

export function getCrawlStatus(tenantId, token) {
  return request(`/api/v1/crawl/${tenantId}/status`, { token });
}
