/**
 * Dashboard, auth, billing, tenant settings, and onboarding API functions.
 */
import { request } from "./_client";

// --- Core Dashboard ---

export function fetchDashboard(tenantId, token) {
  return request(`/api/v1/auth/dashboard/${tenantId}`, { token });
}

export function getMe(token) {
  return request("/api/v1/auth/me", { token });
}

export function fetchUsage(tenantId, token) {
  return request(`/api/v1/usage/${tenantId}`, { token });
}

export function fetchActivity(tenantId, token) {
  return request(`/api/v1/auth/activity/${tenantId}`, { token });
}

// --- Tenant Settings ---

export function fetchTenant(tenantId, token) {
  return request(`/api/v1/auth/tenant/${tenantId}`, { token });
}

export function updateTenantSettings(tenantId, token, data) {
  return request(`/api/v1/auth/settings/${tenantId}`, { method: "PUT", token, body: data });
}

// --- Billing ---

export function billingCheckout(token, { plan, promo_code } = {}) {
  return request("/api/v1/auth/billing/checkout", { method: "POST", token, body: { plan, promo_code } });
}

export function billingPortal(tenantId, token) {
  return request(`/api/v1/auth/billing/portal/${tenantId}`, { token });
}

export function fetchTrialStatus(tenantId, token) {
  return request(`/api/v1/auth/trial-status/${tenantId}`, { token });
}

export function changePlan(token, plan) {
  return request("/api/v1/auth/billing/change-plan", { method: "POST", token, body: { plan } });
}

export function cancelSubscription(token) {
  return request("/api/v1/auth/billing/cancel", { method: "POST", token });
}

// --- Onboarding ---

export function fetchOnboardingStatus(tenantId, token) {
  return request(`/api/v1/onboarding/${tenantId}/status`, { token });
}

// --- AI Insights ---

export function fetchAIInsights(tenantId, token) {
  return request(`/api/v1/analytics/${tenantId}/ai-insights`, { token });
}

// --- Contact / Support ---

export function submitContactForm(data) {
  return request("/api/v1/support/contact", { method: "POST", body: data });
}

// --- Notifications ---

export function fetchNotifications(tenantId, token) {
  return request(`/api/v1/notifications/${tenantId}`, { token });
}

// --- MCP API Keys ---

export function generateMcpKey(tenantId, token) {
  return request(`/api/v1/auth/mcp-key/${tenantId}`, { method: "POST", token });
}

export function revokeMcpKey(tenantId, token) {
  return request(`/api/v1/auth/mcp-key/${tenantId}`, { method: "DELETE", token });
}

export function fetchKnowledgeStats(tenantId, token) {
  return request(`/api/v1/auth/knowledge-stats/${tenantId}`, { token });
}

// --- KPI Deltas (week-over-week) ---

export function fetchKpiDeltas(tenantId, token) {
  return request(`/api/v1/analytics/${tenantId}/kpi-deltas`, { token });
}
