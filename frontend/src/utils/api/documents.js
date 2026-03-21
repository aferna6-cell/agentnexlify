/**
 * Documents & E-Signatures API functions.
 */
import { request } from "./_client";

export function fetchDocuments(tenantId, token, params = {}) {
  const qs = new URLSearchParams(params).toString();
  return request(`/api/v1/documents/${tenantId}${qs ? `?${qs}` : ""}`, { token });
}
export function createDocument(tenantId, token, data) {
  return request(`/api/v1/documents/${tenantId}`, { method: "POST", token, body: data });
}
export function createDocumentFromTemplate(tenantId, token, data) {
  return request(`/api/v1/documents/${tenantId}/from-template`, { method: "POST", token, body: data });
}
export function sendDocument(tenantId, token, docId, data) {
  return request(`/api/v1/documents/${tenantId}/${docId}/send`, { method: "POST", token, body: data });
}
export function deleteDocument(tenantId, token, docId) {
  return request(`/api/v1/documents/${tenantId}/${docId}`, { method: "DELETE", token });
}
export function fetchDocTemplates(tenantId, token) {
  return request(`/api/v1/documents/${tenantId}/templates`, { token });
}
export function createDocTemplate(tenantId, token, data) {
  return request(`/api/v1/documents/${tenantId}/templates`, { method: "POST", token, body: data });
}
export function deleteDocTemplate(tenantId, token, templateId) {
  return request(`/api/v1/documents/${tenantId}/templates/${templateId}`, { method: "DELETE", token });
}
