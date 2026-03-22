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
