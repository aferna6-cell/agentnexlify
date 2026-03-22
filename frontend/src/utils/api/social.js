/**
 * Social media post management API functions.
 */
import { request } from "./_client";

export function fetchSocialPosts(tenantId, token, filters = {}) {
  const params = new URLSearchParams();
  if (filters.platform) params.set("platform", filters.platform);
  if (filters.status) params.set("status", filters.status);
  const qs = params.toString();
  return request(`/api/v1/social/${tenantId}/posts${qs ? "?" + qs : ""}`, { token });
}

export function createSocialPost(tenantId, token, data) {
  return request(`/api/v1/social/${tenantId}/posts`, { method: "POST", token, body: data });
}

export function updateSocialPost(tenantId, token, postId, data) {
  return request(`/api/v1/social/${tenantId}/posts/${postId}`, { method: "PUT", token, body: data });
}

export function deleteSocialPost(tenantId, token, postId) {
  return request(`/api/v1/social/${tenantId}/posts/${postId}`, { method: "DELETE", token });
}

export function generateSocialContent(tenantId, token, data) {
  return request(`/api/v1/social/${tenantId}/generate`, { method: "POST", token, body: data });
}

export function generateSocialCampaign(tenantId, token, data) {
  return request(`/api/v1/social/${tenantId}/generate-campaign`, { method: "POST", token, body: data });
}

export function fetchSocialCalendar(tenantId, token, month, year) {
  return request(`/api/v1/social/${tenantId}/calendar?month=${month}&year=${year}`, { token });
}

export function fetchSocialAnalytics(tenantId, token) {
  return request(`/api/v1/social/${tenantId}/analytics`, { token });
}
