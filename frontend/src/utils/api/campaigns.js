/**
 * Marketing campaigns API functions.
 */
import { request } from "./_client";

export function fetchMarketingCampaigns(tenantId, token, filters = {}) {
  const params = new URLSearchParams();
  if (filters.type) params.set("type", filters.type);
  if (filters.status) params.set("status", filters.status);
  const qs = params.toString();
  return request(`/api/v1/campaigns/${tenantId}${qs ? "?" + qs : ""}`, { token });
}

export function createMarketingCampaign(tenantId, token, data) {
  return request(`/api/v1/campaigns/${tenantId}`, { method: "POST", token, body: data });
}

export function sendMarketingCampaign(tenantId, token, campaignId) {
  return request(`/api/v1/campaigns/${tenantId}/${campaignId}/send`, { method: "POST", token });
}

export function fetchCampaignDetail(tenantId, token, campaignId) {
  return request(`/api/v1/campaigns/${tenantId}/${campaignId}`, { token });
}

export function fetchCampaignAnalytics(tenantId, token, campaignId) {
  return request(`/api/v1/campaigns/${tenantId}/${campaignId}/analytics`, { token });
}

export function generateCampaignContent(tenantId, token, data) {
  return request(`/api/v1/campaigns/${tenantId}/generate-email`, { method: "POST", token, body: data });
}

export function estimateCampaignRecipients(tenantId, token, filters) {
  return request(`/api/v1/campaigns/${tenantId}/estimate`, { method: "POST", token, body: filters });
}
