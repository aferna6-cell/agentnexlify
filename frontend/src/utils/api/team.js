/**
 * Team management API functions.
 */
import { request } from "./_client";

export function inviteTeamMember(tenantId, token, { email, role, name }) {
  return request("/api/v1/team/invite", { method: "POST", token, body: { email, role, name } });
}

export function fetchTeamMembers(tenantId, token) {
  return request(`/api/v1/team/members/${tenantId}`, { token });
}

export function updateTeamMemberRole(tenantId, token, memberId, role) {
  return request(`/api/v1/team/members/${tenantId}/${memberId}`, { method: "PUT", token, body: { role } });
}

export function removeTeamMember(tenantId, token, memberId) {
  return request(`/api/v1/team/members/${tenantId}/${memberId}`, { method: "DELETE", token });
}

export function resendInvite(tenantId, token, memberId) {
  return request(`/api/v1/team/members/${tenantId}/${memberId}/resend`, { method: "POST", token });
}

export function validateInvite(inviteToken) {
  return request(`/api/v1/team/invite/${inviteToken}`);
}

export function acceptInvite(inviteToken, { name, password }) {
  return request("/api/v1/team/accept-invite", { method: "POST", body: { token: inviteToken, name, password } });
}

export function fetchTeamActivity(tenantId, token, { memberId, days } = {}) {
  const params = new URLSearchParams();
  if (memberId) params.set("member_id", memberId);
  if (days) params.set("days", days);
  const qs = params.toString();
  return request(`/api/v1/team/${tenantId}/activity${qs ? `?${qs}` : ""}`, { token });
}
