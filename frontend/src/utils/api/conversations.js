/**
 * Conversations API functions.
 */
import { request } from "./_client";

export function fetchConversations(tenantId, token, { channel } = {}) {
  const params = new URLSearchParams();
  if (channel) params.set("channel", channel);
  const qs = params.toString();
  return request(`/api/v1/auth/conversations/${tenantId}${qs ? `?${qs}` : ""}`, { token });
}

export function fetchConversationMessages(tenantId, sessionId, token) {
  return request(`/api/v1/auth/conversations/${tenantId}/${sessionId}`, { token });
}

export function updateConversationTags(tenantId, sessionId, token, tags) {
  return request(`/api/v1/auth/conversations/${tenantId}/${sessionId}/tags`, { method: "PUT", token, body: { tags } });
}
