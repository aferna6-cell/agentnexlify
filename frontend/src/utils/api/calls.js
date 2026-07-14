/**
 * Calls API functions - AI phone answering call log (backend/routers/calls.py).
 */
import { request } from "./_client";

export function getCalls(tenantId, token, { status, page = 1, perPage = 50 } = {}) {
  const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
  if (status) params.set("status", status);
  return request(`/api/v1/calls/${tenantId}?${params.toString()}`, { token });
}

export function getCallStats(tenantId, token) {
  return request(`/api/v1/calls/${tenantId}/stats`, { token });
}

export function getCall(tenantId, callId, token) {
  return request(`/api/v1/calls/${tenantId}/${callId}`, { token });
}
