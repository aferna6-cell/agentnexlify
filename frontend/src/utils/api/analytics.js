/**
 * Analytics API functions.
 */
import { request } from "./_client";

export function fetchAnalyticsOverview(tenantId, token, period = "30d") {
  return request(`/api/v1/analytics/${tenantId}/overview?period=${period}`, { token });
}

export function fetchAnalyticsConversations(tenantId, token, period = "30d") {
  return request(`/api/v1/analytics/${tenantId}/conversations?period=${period}`, { token });
}

export function fetchAnalyticsLeads(tenantId, token, period = "30d") {
  return request(`/api/v1/analytics/${tenantId}/leads?period=${period}`, { token });
}

export function fetchAnalyticsResponseTimes(tenantId, token, period = "30d") {
  return request(`/api/v1/analytics/${tenantId}/response-times?period=${period}`, { token });
}

export function fetchAnalyticsWidget(tenantId, token, period = "30d") {
  return request(`/api/v1/analytics/${tenantId}/widget?period=${period}`, { token });
}

export function fetchLeadSources(tenantId, token) {
  return request(`/api/v1/analytics/${tenantId}/lead-sources`, { token });
}

export function fetchMissedCallAnalytics(tenantId, token, period = "30d") {
  return request(`/api/v1/analytics/${tenantId}/missed-calls?period=${period}`, { token });
}

export function fetchTeamPerformance(tenantId, token, days = 30) {
  return request(`/api/v1/analytics/${tenantId}/team-performance?days=${days}`, { token });
}

export function fetchLeadSourcesUtm(tenantId, token, period = "30d") {
  return request(`/api/v1/analytics/${tenantId}/lead-sources-utm?period=${period}`, { token });
}

export function fetchConversationSentiment(tenantId, token, period = "30d") {
  return request(`/api/v1/analytics/${tenantId}/conversation-sentiment?period=${period}`, { token });
}
