/**
 * Bids & estimates API functions.
 */
import { request } from "./_client";

export function fetchBids(tenantId, token, { status } = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString() ? `?${params}` : "";
  return request(`/api/v1/bids/${tenantId}${qs}`, { token });
}

export function createBid(tenantId, token, data) {
  return request(`/api/v1/bids/${tenantId}`, { method: "POST", token, body: data });
}

export function updateBid(tenantId, token, bidId, data) {
  return request(`/api/v1/bids/${tenantId}/${bidId}`, { method: "PUT", token, body: data });
}

export function deleteBid(tenantId, token, bidId) {
  return request(`/api/v1/bids/${tenantId}/${bidId}`, { method: "DELETE", token });
}

export function updateBidStatus(tenantId, token, bidId, status) {
  return request(`/api/v1/bids/${tenantId}/${bidId}/status`, { method: "PUT", token, body: { status } });
}

export function fetchBidStats(tenantId, token) {
  return request(`/api/v1/bids/${tenantId}/stats`, { token });
}

export function fetchBidTemplates(tenantId, token) {
  return request(`/api/v1/bids/${tenantId}/templates`, { token });
}

export function createBidTemplate(tenantId, token, data) {
  return request(`/api/v1/bids/${tenantId}/templates`, { method: "POST", token, body: data });
}

export function deleteBidTemplate(tenantId, token, templateId) {
  return request(`/api/v1/bids/${tenantId}/templates/${templateId}`, { method: "DELETE", token });
}

export function aiGenerateBid(tenantId, token, jobDescription) {
  return request(`/api/v1/bids/${tenantId}/ai-generate`, { method: "POST", token, body: { job_description: jobDescription } });
}
