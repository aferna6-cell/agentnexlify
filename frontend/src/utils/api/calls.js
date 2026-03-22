/**
 * AI Answering Service / Calls API functions.
 */
import { request } from "./_client";

export function fetchCalls(tenantId, token, { status } = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString() ? `?${params}` : "";
  return request(`/api/v1/calls/${tenantId}${qs}`, { token });
}

export function fetchCallDetail(tenantId, token, callId) {
  return request(`/api/v1/calls/${tenantId}/${callId}`, { token });
}

export function fetchCallStats(tenantId, token) {
  return request(`/api/v1/calls/${tenantId}/stats`, { token });
}
