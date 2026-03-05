const BASE = import.meta.env.VITE_API_BASE_URL || "https://agentnexlify-production.up.railway.app";

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

export function fetchLeads(tenantId, token, { stage, search, sort, order } = {}) {
  const params = new URLSearchParams();
  if (stage) params.set("stage", stage);
  if (search) params.set("search", search);
  if (sort) params.set("sort", sort);
  if (order) params.set("order", order);
  const qs = params.toString();
  return request(`/api/v1/leads/${tenantId}${qs ? `?${qs}` : ""}`, { token });
}

export function updateLead(tenantId, token, leadId, data) {
  return request(`/api/v1/leads/${tenantId}/${leadId}`, {
    method: "PATCH",
    token,
    body: data,
  });
}

export async function deleteLead(tenantId, token, leadId) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}/api/v1/leads/${tenantId}/${leadId}`, {
    method: "DELETE",
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, err);
  }
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

// --- Widget Config ---

export function updateWidgetConfig(tenantId, token, data) {
  return request(`/api/v1/auth/widget-config/${tenantId}`, {
    method: "PUT",
    token,
    body: data,
  });
}

// --- FAQ CRUD ---

export function fetchFaqEntries(tenantId, token) {
  return request(`/api/v1/auth/faq/${tenantId}`, { token });
}

export function createFaqEntry(tenantId, token, { question, answer, category }) {
  return request(`/api/v1/auth/faq/${tenantId}`, {
    method: "POST",
    token,
    body: { question, answer, category },
  });
}

export async function deleteFaqEntry(tenantId, token, faqId) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}/api/v1/auth/faq/${tenantId}/${faqId}`, {
    method: "DELETE",
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, err);
  }
}

// --- Lead Scoring ---

export function fetchLeadScore(tenantId, leadId, token) {
  return request(`/api/v1/leads/${tenantId}/${leadId}/score`, { token });
}

export function rescoreAllLeads(tenantId, token) {
  return request(`/api/v1/leads/${tenantId}/score-all`, { method: "POST", token });
}

// --- CRM / Clients ---

export function fetchClients(tenantId, token, { search, stage, sort, order } = {}) {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (stage) params.set("stage", stage);
  if (sort) params.set("sort", sort);
  if (order) params.set("order", order);
  const qs = params.toString();
  return request(`/api/v1/clients/${tenantId}${qs ? `?${qs}` : ""}`, { token });
}

export function fetchClientProfile(tenantId, leadId, token) {
  return request(`/api/v1/clients/${tenantId}/${leadId}`, { token });
}

export function fetchClientTimeline(tenantId, leadId, token, { offset = 0, limit = 20 } = {}) {
  return request(`/api/v1/clients/${tenantId}/${leadId}/timeline?offset=${offset}&limit=${limit}`, { token });
}

export function addClientNote(tenantId, leadId, token, content) {
  return request(`/api/v1/clients/${tenantId}/${leadId}/notes`, {
    method: "POST",
    token,
    body: { content },
  });
}

export function updateClient(tenantId, leadId, token, data) {
  return request(`/api/v1/clients/${tenantId}/${leadId}`, {
    method: "PUT",
    token,
    body: data,
  });
}

export function changeClientStage(tenantId, leadId, token, stage) {
  return request(`/api/v1/clients/${tenantId}/${leadId}/stage`, {
    method: "PUT",
    token,
    body: { stage },
  });
}

export function fetchCrmDashboardWidgets(tenantId, token) {
  return request(`/api/v1/clients/${tenantId}/dashboard-widgets`, { token });
}

// --- Appointments / Availability ---

export function fetchAvailability(tenantId, token) {
  return request(`/api/v1/appointments/availability/${tenantId}`, { token });
}

export function updateAvailability(tenantId, token, data) {
  return request(`/api/v1/appointments/availability/${tenantId}`, {
    method: "PUT",
    token,
    body: data,
  });
}

export function fetchAppointments(tenantId, token, { startDate, endDate, status } = {}) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  if (status) params.set("status", status);
  const qs = params.toString();
  return request(`/api/v1/appointments/${tenantId}${qs ? `?${qs}` : ""}`, { token });
}

export function updateAppointment(tenantId, token, appointmentId, data) {
  return request(`/api/v1/appointments/${tenantId}/${appointmentId}`, {
    method: "PATCH",
    token,
    body: data,
  });
}

export function cancelAppointment(tenantId, token, appointmentId) {
  return request(`/api/v1/appointments/${tenantId}/${appointmentId}`, {
    method: "DELETE",
    token,
  });
}

// --- Automation Sequences ---

export function fetchSequences(tenantId, token) {
  return request(`/api/v1/sequences/${tenantId}`, { token });
}

export function createSequence(tenantId, token, data) {
  return request(`/api/v1/sequences/${tenantId}`, { method: "POST", token, body: data });
}

export function updateSequence(tenantId, token, seqId, data) {
  return request(`/api/v1/sequences/${tenantId}/${seqId}`, { method: "PUT", token, body: data });
}

export function deleteSequence(tenantId, token, seqId) {
  return request(`/api/v1/sequences/${tenantId}/${seqId}`, { method: "DELETE", token });
}

export function toggleSequence(tenantId, token, seqId) {
  return request(`/api/v1/sequences/${tenantId}/${seqId}/toggle`, { method: "POST", token });
}

export function fetchSequenceDetail(tenantId, token, seqId) {
  return request(`/api/v1/sequences/${tenantId}/${seqId}`, { token });
}

export function fetchSequenceStats(tenantId, token) {
  return request(`/api/v1/sequences/${tenantId}/stats`, { token });
}

export function createFromTemplate(tenantId, token, templateId) {
  return request(`/api/v1/sequences/${tenantId}/templates`, {
    method: "POST",
    token,
    body: { template_id: templateId },
  });
}

export function updateLeadStage(tenantId, token, leadId, stage) {
  return request(`/api/v1/leads/${tenantId}/${leadId}/stage`, {
    method: "PATCH",
    token,
    body: { stage },
  });
}

// --- Conversations ---

export function fetchConversations(tenantId, token) {
  return request(`/api/v1/auth/conversations/${tenantId}`, { token });
}

export function fetchConversationMessages(tenantId, sessionId, token) {
  return request(`/api/v1/auth/conversations/${tenantId}/${sessionId}`, { token });
}

// --- Tenant Settings ---

export function fetchTenant(tenantId, token) {
  return request(`/api/v1/auth/tenant/${tenantId}`, { token });
}

export function updateTenantSettings(tenantId, token, data) {
  return request(`/api/v1/auth/settings/${tenantId}`, { method: "PUT", token, body: data });
}

// --- Billing (JWT-authenticated) ---

export function billingCheckout(token, { plan, promo_code } = {}) {
  return request("/api/v1/auth/billing/checkout", { method: "POST", token, body: { plan, promo_code } });
}

export function billingPortal(tenantId, token) {
  return request(`/api/v1/auth/billing/portal/${tenantId}`, { token });
}

// --- Contact / Support ---

export function submitContactForm(data) {
  return request("/api/v1/support/contact", { method: "POST", body: data });
}

export { ApiError };
