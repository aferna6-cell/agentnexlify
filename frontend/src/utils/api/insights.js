// Insights API - daily focus, Nexlify Score, appointment briefs.
import { request } from "./_client";

// GET /api/v1/insights/:tenantId/daily-focus -> { picks: [{kind,title,reason,count}] }
export function fetchDailyFocus(tenantId, token) {
  return request(`/api/v1/insights/${tenantId}/daily-focus`, { token });
}

// GET /api/v1/insights/:tenantId/response-score
// -> { score, grade, components, weights, window_days }
export function fetchResponseScore(tenantId, token) {
  return request(`/api/v1/insights/${tenantId}/response-score`, { token });
}

// POST /api/v1/appointments/:tenantId/:appointmentId/brief
// -> { brief, has_history } (markdown brief for the owner)
export function fetchAppointmentBrief(tenantId, appointmentId, token) {
  return request(`/api/v1/appointments/${tenantId}/${appointmentId}/brief`, {
    method: "POST",
    token,
  });
}

// POST /api/v1/appointments/:tenantId/:appointmentId/follow-up-draft
// -> { subject, body, customer_email } - a draft to review, never auto-sent
export function fetchFollowupDraft(tenantId, appointmentId, token) {
  return request(`/api/v1/appointments/${tenantId}/${appointmentId}/follow-up-draft`, {
    method: "POST",
    token,
  });
}
