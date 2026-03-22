/**
 * Client Portal API functions.
 */
import { request } from "./_client";

export function fetchServiceRecords(tenantId, token) {
  return request(`/api/v1/portal/${tenantId}/service-records`, { token });
}

export function createServiceRecord(tenantId, token, data) {
  return request(`/api/v1/portal/${tenantId}/service-records`, { method: "POST", token, body: data });
}

export function updateServiceRecord(tenantId, token, recordId, data) {
  return request(`/api/v1/portal/${tenantId}/service-records/${recordId}`, { method: "PUT", token, body: data });
}

export function deleteServiceRecord(tenantId, token, recordId) {
  return request(`/api/v1/portal/${tenantId}/service-records/${recordId}`, { method: "DELETE", token });
}

export function generatePortalLink(tenantId, token, leadId) {
  return request(`/api/v1/portal/${tenantId}/portal-link/${leadId}`, { method: "POST", token });
}

export function fetchClientPortalPublic(portalToken) {
  return request(`/api/v1/portal/portal/${portalToken}`);
}

// --- Client Login ---

export function clientRegister(portalToken, email, password) {
  return request("/api/v1/portal/client/register", {
    method: "POST",
    body: { portal_token: portalToken, email, password },
  });
}

export function clientLogin(email, password, businessSlug) {
  return request("/api/v1/portal/client/login", {
    method: "POST",
    body: { email, password, business_slug: businessSlug },
  });
}

export function fetchClientPortalAuth(clientToken) {
  return request("/api/v1/portal/client/me", {
    headers: { Authorization: `Bearer ${clientToken}` },
  });
}

export function toggleClientLogin(tenantId, token) {
  return request(`/api/v1/portal/${tenantId}/client-login`, { method: "PUT", token });
}
