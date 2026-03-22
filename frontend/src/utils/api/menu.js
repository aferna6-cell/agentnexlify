/**
 * Menu management API functions (restaurants).
 */
import { request } from "./_client";

export function fetchMenuItems(tenantId, token, category) {
  const params = category ? `?category=${encodeURIComponent(category)}` : "";
  return request(`/api/v1/menu/${tenantId}${params}`, { token });
}

export function createMenuItem(tenantId, token, data) {
  return request(`/api/v1/menu/${tenantId}`, { method: "POST", token, body: data });
}

export function updateMenuItem(tenantId, token, itemId, data) {
  return request(`/api/v1/menu/${tenantId}/${itemId}`, { method: "PUT", token, body: data });
}

export function deleteMenuItem(tenantId, token, itemId) {
  return request(`/api/v1/menu/${tenantId}/${itemId}`, { method: "DELETE", token });
}

export function toggleMenuItemAvailability(tenantId, token, itemId) {
  return request(`/api/v1/menu/${tenantId}/${itemId}/toggle`, { method: "PUT", token });
}

export function importMenuFromWebsite(tenantId, token) {
  return request(`/api/v1/menu/${tenantId}/import-from-website`, { method: "POST", token });
}

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
  return request(`/api/v1/orders/${tenantId}/${orderId}/status`, { method: "PUT", token, body: { status } });
}
