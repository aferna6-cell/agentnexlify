import { request } from "./_client";

export async function fetchWaitlist(tenantId, token, { status, dateFrom, dateTo } = {}) {
  let path = `/api/v1/waitlist/${tenantId}?`;
  if (status) path += `status=${status}&`;
  if (dateFrom) path += `date_from=${dateFrom}&`;
  if (dateTo) path += `date_to=${dateTo}&`;
  return request(path, { token });
}

export async function fetchWaitlistStats(tenantId, token) {
  return request(`/api/v1/waitlist/${tenantId}/stats`, { token });
}

export async function updateWaitlistEntry(tenantId, entryId, data, token) {
  return request(`/api/v1/waitlist/${tenantId}/${entryId}`, { method: "PATCH", body: data, token });
}

export async function deleteWaitlistEntry(tenantId, entryId, token) {
  return request(`/api/v1/waitlist/${tenantId}/${entryId}`, { method: "DELETE", token });
}

export async function notifyWaitlistEntry(tenantId, entryId, message, token) {
  return request(`/api/v1/waitlist/${tenantId}/${entryId}/notify`, {
    method: "POST",
    body: message ? { message } : {},
    token,
  });
}

export async function checkWaitlistForDate(tenantId, date, token) {
  return request(`/api/v1/waitlist/${tenantId}/check-date/${date}`, { token });
}
