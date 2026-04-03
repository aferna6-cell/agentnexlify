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

export function fetchRevenue(tenantId, token) {
  return request(`/api/v1/analytics/${tenantId}/revenue`, { token });
}

export function fetchAnalyticsHealth(tenantId, token) {
  return request(`/api/v1/analytics/${tenantId}/health`, { token });
}

export function fetchAnalyticsSnapshot(tenantId, token, period = "30d") {
  return request(`/api/v1/analytics/${tenantId}/snapshot?period=${period}`, { token });
}

export function fetchAgentControlCenter(tenantId, token, period = "30d") {
  return request(`/api/v1/analytics/${tenantId}/control-center?period=${period}`, { token });
}
