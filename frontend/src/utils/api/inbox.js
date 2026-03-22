/**
 * Shared team inbox API functions (conversation assignment, notes, replies, presence).
 */
import { request } from "./_client";

export function assignConversation(tenantId, token, conversationId, assignedTo) {
  return request(`/api/v1/inbox/${tenantId}/conversations/${conversationId}/assign`, {
    method: "PUT", token, body: { assigned_to: assignedTo },
  });
}

export function fetchConversationNotes(tenantId, token, conversationId) {
  return request(`/api/v1/inbox/${tenantId}/conversations/${conversationId}/notes`, { token });
}

export function createConversationNote(tenantId, token, conversationId, content) {
  return request(`/api/v1/inbox/${tenantId}/conversations/${conversationId}/notes`, {
    method: "POST", token, body: { content },
  });
}

export function deleteConversationNote(tenantId, token, noteId) {
  return request(`/api/v1/inbox/${tenantId}/notes/${noteId}`, { method: "DELETE", token });
}

export function replyToConversation(tenantId, token, conversationId, content) {
  return request(`/api/v1/inbox/${tenantId}/conversations/${conversationId}/reply`, {
    method: "POST", token, body: { content },
  });
}

export function updatePresence(tenantId, token, conversationId) {
  return request(`/api/v1/inbox/${tenantId}/presence${conversationId ? `?conversation_id=${conversationId}` : ""}`, {
    method: "PUT", token,
  });
}

export function getPresence(tenantId, token) {
  return request(`/api/v1/inbox/${tenantId}/presence`, { token });
}
