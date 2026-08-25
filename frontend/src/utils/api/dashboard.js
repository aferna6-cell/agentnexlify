/**
 * Dashboard, auth, billing, tenant settings, and onboarding API functions.
 */
import { request } from "./_client";

// --- Core Dashboard ---

export function fetchDashboard(tenantId, token) {
  return request(`/api/v1/auth/dashboard/${tenantId}`, { token });
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

export function billingCheckout(token, { plan, promo_code, billing_interval } = {}) {
  return request("/api/v1/auth/billing/checkout", { method: "POST", token, body: { plan, promo_code, billing_interval } });
}

export function billingPortal(tenantId, token) {
  return request(`/api/v1/auth/billing/portal/${tenantId}`, { token });
}

export function fetchTrialStatus(tenantId, token) {
  return request(`/api/v1/auth/trial-status/${tenantId}`, { token });
}

export function changePlan(token, plan, billing_interval) {
  return request("/api/v1/auth/billing/change-plan", { method: "POST", token, body: { plan, billing_interval } });
}

export function cancelSubscription(token, { reason, reason_detail, feedback } = {}) {
  return request("/api/v1/auth/billing/cancel", {
    method: "POST",
    token,
    body: { reason, reason_detail, feedback },
  });
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

export function fetchKnowledgeStats(tenantId, token) {
  return request(`/api/v1/auth/knowledge-stats/${tenantId}`, { token });
}

// --- KPI Deltas (week-over-week) ---

export function fetchKpiDeltas(tenantId, token) {
  return request(`/api/v1/analytics/${tenantId}/kpi-deltas`, { token });
}

// --- AI Usage (for billing usage meter) ---
// Returns the nested ai_usage object from GET /api/v1/billing/ai-usage.
// Same snapshot as /api/v1/os/usage but ungated: chatbot-plan tenants burn
// widget AI tokens too and must see the meter (os/usage 402s for them).
// Shape: { limit_units, used_units, remaining_units, pct_used, period_month, alert_reached, hard_limit_reached }
export function fetchAiUsage(token) {
  return request("/api/v1/billing/ai-usage", { token }).then((data) => data?.ai_usage ?? null);
}

// POST /api/v1/billing/buy-usage - purchase additional usage credits.
// Returns { checkout_url } which the caller redirects to.
export function buyMoreUsage(token) {
  return request("/api/v1/billing/buy-usage", { method: "POST", token });
}
