/**
 * Chat flow builder API functions.
 */
import { request } from "./_client";

export function fetchChatFlows(tenantId, token) {
  return request(`/api/v1/chat-flows/${tenantId}`, { token });
}

export function fetchFlowTemplates(tenantId, token) {
  return request(`/api/v1/chat-flows/${tenantId}/templates`, { token });
}

export function createChatFlow(tenantId, token, data) {
  return request(`/api/v1/chat-flows/${tenantId}`, { method: "POST", token, body: data });
}

export function createFlowFromTemplate(tenantId, token, templateIndex) {
  return request(`/api/v1/chat-flows/${tenantId}/from-template/${templateIndex}`, { method: "POST", token });
}

export function updateChatFlow(tenantId, token, flowId, data) {
  return request(`/api/v1/chat-flows/${tenantId}/${flowId}`, { method: "PUT", token, body: data });
}

export function deleteChatFlow(tenantId, token, flowId) {
  return request(`/api/v1/chat-flows/${tenantId}/${flowId}`, { method: "DELETE", token });
}
