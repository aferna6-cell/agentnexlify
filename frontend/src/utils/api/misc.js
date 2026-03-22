/**
 * Miscellaneous API functions (CSAT, SMS, custom fields, orders).
 */
import { request } from "./_client";

// --- CSAT ---

export function fetchCSATStats(tenantId, token, period = "30d") {
  return request(`/api/v1/csat/${tenantId}/stats?period=${period}`, { token });
}

export function fetchCSATResponses(tenantId, token) {
  return request(`/api/v1/csat/${tenantId}/responses`, { token });
}

// --- SMS ---

export function sendSms(token, { lead_id, phone, message }) {
  return request("/api/v1/sms/send", { method: "POST", token, body: { lead_id, phone, message } });
}

// --- Custom Fields ---

export function fetchFieldDefinitions(tenantId, token) {
  return request(`/api/v1/custom-fields/${tenantId}/definitions`, { token });
}

export function createFieldDefinition(tenantId, token, data) {
  return request(`/api/v1/custom-fields/${tenantId}/definitions`, { method: "POST", token, body: data });
}

export function deleteFieldDefinition(tenantId, token, fieldId) {
  return request(`/api/v1/custom-fields/${tenantId}/definitions/${fieldId}`, { method: "DELETE", token });
}

export function fetchLeadFieldValues(tenantId, token, leadId) {
  return request(`/api/v1/custom-fields/${tenantId}/values/${leadId}`, { token });
}

export function updateLeadFieldValues(tenantId, token, leadId, values) {
  return request(`/api/v1/custom-fields/${tenantId}/values/${leadId}`, { method: "PUT", token, body: values });
}

// --- Orders ---

export function fetchOrders(tenantId, token, { status } = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString() ? `?${params}` : "";
  return request(`/api/v1/orders/${tenantId}${qs}`, { token });
}

export function fetchOrderStats(tenantId, token) {
  return request(`/api/v1/orders/${tenantId}/stats`, { token });
}

export function updateOrderStatus(tenantId, token, orderId, status) {
  return request(`/api/v1/orders/${tenantId}/${orderId}/status`, {
    method: "PUT",
    token,
    body: { status },
  });
}
