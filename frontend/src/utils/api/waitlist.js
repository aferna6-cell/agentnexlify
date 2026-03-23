/**
 * Waitlist API functions.
 */
import { request } from "./_client";

export function fetchWaitlistEntries(tenantId, token, { status, dateFrom, dateTo } = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  const qs = params.toString();
  return request(`/api/v1/waitlist/${tenantId}${qs ? `?${qs}` : ""}`, { token });
}

export function fetchWaitlistStats(tenantId, token) {
  return request(`/api/v1/waitlist/${tenantId}/stats`, { token });
}

export function updateWaitlistEntry(tenantId, token, entryId, data) {
  return request(`/api/v1/waitlist/${tenantId}/${entryId}`, { method: "PATCH", token, body: data });
}

export function deleteWaitlistEntry(tenantId, token, entryId) {
  return request(`/api/v1/waitlist/${tenantId}/${entryId}`, { method: "DELETE", token });
}
