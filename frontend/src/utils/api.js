const BASE = import.meta.env.VITE_API_BASE_URL || "";

class ApiError extends Error {
  constructor(status, body) {
    super(body?.detail || `API error ${status}`);
    this.status = status;
    this.body = body;
  }
}

async function request(path, { method = "GET", body, token } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, err);
  }

  return res.json();
}

// --- Dashboard API ---

export function fetchLeads(tenantId, token) {
  return request(`/api/v1/leads/${tenantId}`, { token });
}

export function fetchLeadSummary(tenantId, token) {
  return request(`/api/v1/leads/${tenantId}/summary`, { token });
}

export function fetchAutomations(tenantId, token) {
  return request(`/api/v1/automations/${tenantId}`, { token });
}

export function fetchActivity(tenantId, token) {
  return request(`/api/v1/activity/${tenantId}`, { token });
}

export function fetchWidgetConfig(tenantId, token) {
  return request(`/api/v1/widget-config/${tenantId}`, { token });
}

export function fetchUsage(tenantId, token) {
  return request(`/api/v1/usage/${tenantId}`, { token });
}

export function fetchDashboard(tenantId, token) {
  return request(`/api/v1/auth/dashboard/${tenantId}`, { token });
}

export function getMe(token) {
  return request("/api/v1/auth/me", { token });
}

export { ApiError };
