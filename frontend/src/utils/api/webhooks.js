/**
 * Webhook management API functions.
 */
import { request } from "./_client";

export function fetchWebhooks(tenantId, token) {
  return request(`/api/v1/webhooks/${tenantId}`, { token });
}

export function createWebhook(tenantId, token, data) {
  return request(`/api/v1/webhooks/${tenantId}`, { method: "POST", token, body: data });
}

export function updateWebhook(tenantId, token, webhookId, data) {
  return request(`/api/v1/webhooks/${tenantId}/${webhookId}`, { method: "PUT", token, body: data });
}

export function deleteWebhook(tenantId, token, webhookId) {
  return request(`/api/v1/webhooks/${tenantId}/${webhookId}`, { method: "DELETE", token });
}

export function fetchWebhookDeliveries(tenantId, token, webhookId, limit = 20) {
  return request(`/api/v1/webhooks/${tenantId}/${webhookId}/deliveries?limit=${limit}`, { token });
}

export function fetchWebhookLogs(tenantId, token, limit = 20) {
  return request(`/api/v1/webhooks/${tenantId}/logs/recent?limit=${limit}`, { token });
}

export function toggleWebhook(tenantId, token, webhookId) {
  return request(`/api/v1/webhooks/${tenantId}/${webhookId}/toggle`, { method: "PATCH", token });
}

export function testWebhook(tenantId, token, webhookId) {
  return request(`/api/v1/webhooks/${tenantId}/${webhookId}/test`, { method: "POST", token });
}
