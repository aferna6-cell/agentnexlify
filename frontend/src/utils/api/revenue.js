/**
 * Revenue Analytics API functions.
 */
import { request } from "./_client";

export function fetchRevenueOverview(tenantId, token, period = "30d") {
  return request(`/api/v1/revenue/${tenantId}/overview?period=${period}`, { token });
}

export function fetchRevenueTrend(tenantId, token, period = "30d") {
  return request(`/api/v1/revenue/${tenantId}/trend?period=${period}`, { token });
}

export function fetchTopCustomers(tenantId, token, period = "30d", limit = 10) {
  return request(`/api/v1/revenue/${tenantId}/top-customers?period=${period}&limit=${limit}`, { token });
}

export function fetchRevenueBreakdown(tenantId, token, period = "30d") {
  return request(`/api/v1/revenue/${tenantId}/breakdown?period=${period}`, { token });
}
