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

export function fetchLeads(tenantId, token, { stage, search, sort, order, assigned_to } = {}) {
  const params = new URLSearchParams();
  if (stage) params.set("stage", stage);
  if (search) params.set("search", search);
  if (sort) params.set("sort", sort);
  if (order) params.set("order", order);
  if (assigned_to) params.set("assigned_to", assigned_to);
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

export function fetchAutomations(tenantId, token) {
  return request(`/api/v1/automations/${tenantId}`, { token });
}

export function fetchActivity(tenantId, token) {
  return request(`/api/v1/auth/activity/${tenantId}`, { token });
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

export async function importLeadsCSV(tenantId, token, file) {
  const formData = new FormData();
  formData.append("file", file);
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}/api/v1/leads/${tenantId}/import`, {
    method: "POST",
    headers,
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, err);
  }
  return res.json();
}

export function sendLeadEmail(tenantId, token, leadId, data) {
  return request(`/api/v1/leads/${tenantId}/${leadId}/email`, {
    method: "POST",
    token,
    body: data,
  });
}

export function assignLead(tenantId, token, leadId, assignedTo) {
  return request(`/api/v1/leads/${tenantId}/${leadId}/assign`, {
    method: "PUT",
    token,
    body: { assigned_to: assignedTo },
  });
}

export function findDuplicateLeads(tenantId, token) {
  return request(`/api/v1/leads/${tenantId}/duplicates`, { token });
}

export function mergeLeads(tenantId, token, keepId, mergeId) {
  return request(`/api/v1/leads/${tenantId}/merge`, {
    method: "POST",
    token,
    body: { keep_id: keepId, merge_id: mergeId },
  });
}

// --- Reviews (Reputation Manager) ---

export function fetchReviews(tenantId, token, { platform, rating, responded } = {}) {
  const params = new URLSearchParams();
  if (platform) params.set("platform", platform);
  if (rating) params.set("rating", rating);
  if (responded !== undefined && responded !== null) params.set("responded", responded);
  const qs = params.toString() ? `?${params}` : "";
  return request(`/api/v1/reviews/${tenantId}${qs}`, { token });
}

export function createReview(tenantId, token, data) {
  return request(`/api/v1/reviews/${tenantId}`, { method: "POST", token, body: data });
}

export function updateReview(tenantId, token, reviewId, data) {
  return request(`/api/v1/reviews/${tenantId}/${reviewId}`, { method: "PATCH", token, body: data });
}

export function deleteReview(tenantId, token, reviewId) {
  return request(`/api/v1/reviews/${tenantId}/${reviewId}`, { method: "DELETE", token });
}

export function generateAIDraft(tenantId, token, reviewId, tone = "professional") {
  return request(`/api/v1/reviews/${tenantId}/${reviewId}/ai-draft`, { method: "POST", token, body: { tone } });
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

export function setAppointmentRecurrence(tenantId, token, appointmentId, rule, endDate) {
  return request(`/api/v1/appointments/${tenantId}/${appointmentId}/recur`, {
    method: "POST",
    token,
    body: { rule, end_date: endDate },
  });
}

// --- Integrations (Google Calendar) ---

export function fetchGoogleCalendarStatus(tenantId, token) {
  return request(`/api/v1/integrations/google/status`, { token });
}

export function startGoogleCalendarAuth(tenantId, token) {
  return request(`/api/v1/integrations/google/auth`, { token });
}

export function disconnectGoogleCalendar(tenantId, token) {
  return request(`/api/v1/integrations/google`, { method: "DELETE", token });
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

// --- Email Templates ---

export function fetchEmailTemplates(tenantId, token) {
  return request(`/api/v1/email-templates/${tenantId}`, { token });
}

export function createEmailTemplate(tenantId, token, data) {
  return request(`/api/v1/email-templates/${tenantId}`, { method: "POST", token, body: data });
}

export function updateEmailTemplate(tenantId, token, templateId, data) {
  return request(`/api/v1/email-templates/${tenantId}/${templateId}`, { method: "PUT", token, body: data });
}

export function deleteEmailTemplate(tenantId, token, templateId) {
  return request(`/api/v1/email-templates/${tenantId}/${templateId}`, { method: "DELETE", token });
}

// --- Conversations ---

export function fetchConversations(tenantId, token) {
  return request(`/api/v1/auth/conversations/${tenantId}`, { token });
}

export function fetchConversationMessages(tenantId, sessionId, token) {
  return request(`/api/v1/auth/conversations/${tenantId}/${sessionId}`, { token });
}

export function updateConversationTags(tenantId, sessionId, token, tags) {
  return request(`/api/v1/auth/conversations/${tenantId}/${sessionId}/tags`, {
    method: "PUT",
    token,
    body: { tags },
  });
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

export function fetchTrialStatus(tenantId, token) {
  return request(`/api/v1/auth/trial-status/${tenantId}`, { token });
}

// --- Team ---

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

// --- Contact / Support ---

export function submitContactForm(data) {
  return request("/api/v1/support/contact", { method: "POST", body: data });
}

// --- Analytics ---

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

// --- Webhooks ---

export function fetchWebhooks(tenantId, token) {
  return request(`/api/v1/webhooks/${tenantId}`, { token });
}

export function createWebhook(tenantId, token, data) {
  return request(`/api/v1/webhooks/${tenantId}`, { method: "POST", token, body: data });
}

export function updateWebhook(tenantId, token, webhookId, data) {
  return request(`/api/v1/webhooks/${tenantId}/${webhookId}`, { method: "PUT", token, body: data });
}

export function toggleWebhook(tenantId, token, webhookId) {
  return request(`/api/v1/webhooks/${tenantId}/${webhookId}/toggle`, { method: "PATCH", token });
}

export function deleteWebhook(tenantId, token, webhookId) {
  return request(`/api/v1/webhooks/${tenantId}/${webhookId}`, { method: "DELETE", token });
}

export function fetchWebhookLogs(tenantId, token, limit = 20) {
  return request(`/api/v1/webhooks/${tenantId}/logs/recent?limit=${limit}`, { token });
}

export function testWebhook(tenantId, token, webhookId) {
  return request(`/api/v1/webhooks/${tenantId}/${webhookId}/test`, {
    method: "POST",
    token,
  });
}

// --- SMS ---

export function sendSms(token, { lead_id, phone, message }) {
  return request("/api/v1/sms/send", { method: "POST", token, body: { lead_id, phone, message } });
}

// --- Business Page ---

export function fetchBusinessPagePublic(slug) {
  return request(`/biz/${slug}`);
}

export function fetchBusinessPageSettings(tenantId, token) {
  return request(`/api/v1/business-page/${tenantId}`, { token });
}

export function updateBusinessPageSettings(tenantId, token, data) {
  return request(`/api/v1/business-page/${tenantId}`, { method: "PUT", token, body: data });
}

// --- Notifications ---

export function fetchNotifications(tenantId, token) {
  return request(`/api/v1/notifications/${tenantId}`, { token });
}

// --- Widget Online/Offline ---

export function toggleWidgetOnlineStatus(tenantId, token, isOnline) {
  return request(`/api/v1/widget/config/${tenantId}/online-status`, {
    method: "PUT",
    token,
    body: { is_online: isOnline },
  });
}

// --- Campaign blast ---
export function sendCampaign(tenantId, token, { subject, body_html, channel, filters }) {
  return request(`/api/v1/sequences/${tenantId}/campaigns/send`, {
    method: "POST",
    token,
    body: { subject, body_html, channel, filters },
  });
}

// --- Content Studio ---

export function fetchContentItems(tenantId, token, { status } = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString() ? `?${params}` : "";
  return request(`/api/v1/content/${tenantId}${qs}`, { token });
}

export function fetchContentItem(tenantId, token, contentId) {
  return request(`/api/v1/content/${tenantId}/${contentId}`, { token });
}

export function createContentItem(tenantId, token, data) {
  return request(`/api/v1/content/${tenantId}`, { method: "POST", token, body: data });
}

export function updateContentItem(tenantId, token, contentId, data) {
  return request(`/api/v1/content/${tenantId}/${contentId}`, { method: "PATCH", token, body: data });
}

export function deleteContentItem(tenantId, token, contentId) {
  return request(`/api/v1/content/${tenantId}/${contentId}`, { method: "DELETE", token });
}

export function repurposeContent(tenantId, token, contentId) {
  return request(`/api/v1/content/${tenantId}/${contentId}/repurpose`, { method: "POST", token });
}

// --- Billing Management ---

export function changePlan(token, plan) {
  return request("/api/v1/auth/billing/change-plan", { method: "POST", token, body: { plan } });
}

export function cancelSubscription(token) {
  return request("/api/v1/auth/billing/cancel", { method: "POST", token });
}

// --- AI Feedback ---

export function fetchAiFeedback(tenantId, token) {
  return request(`/api/v1/widget/feedback/${tenantId}`, { token });
}

export function deleteAiFeedback(tenantId, token, feedbackId) {
  return request(`/api/v1/widget/feedback/${tenantId}/${feedbackId}`, { method: "DELETE", token });
}

// --- Website Crawl ---

export function startWebsiteCrawl(tenantId, token) {
  return request(`/api/v1/crawl/${tenantId}/start`, { method: "POST", token });
}

export function getCrawlStatus(tenantId, token) {
  return request(`/api/v1/crawl/${tenantId}/status`, { token });
}

// --- Menu ---

export function fetchMenuItems(tenantId, token, category) {
  const params = category ? `?category=${encodeURIComponent(category)}` : "";
  return request(`/api/v1/menu/${tenantId}${params}`, { token });
}

export function createMenuItem(tenantId, token, data) {
  return request(`/api/v1/menu/${tenantId}`, { method: "POST", token, body: data });
}

export function updateMenuItem(tenantId, token, itemId, data) {
  return request(`/api/v1/menu/${tenantId}/${itemId}`, { method: "PUT", token, body: data });
}

export function deleteMenuItem(tenantId, token, itemId) {
  return request(`/api/v1/menu/${tenantId}/${itemId}`, { method: "DELETE", token });
}

export function toggleMenuItemAvailability(tenantId, token, itemId) {
  return request(`/api/v1/menu/${tenantId}/${itemId}/toggle`, { method: "PUT", token });
}

export function importMenuFromWebsite(tenantId, token) {
  return request(`/api/v1/menu/${tenantId}/import-from-website`, { method: "POST", token });
}

// --- Orders ---

export function fetchOrders(tenantId, token, { status } = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString() ? `?${params}` : "";
  return request(`/api/v1/orders/${tenantId}${qs}`, { token });
}

export function fetchOrderStats(tenantId, token) {
  return request(`/api/v1/orders/${tenantId}/stats`, { token });
}

export function updateOrderStatus(tenantId, token, orderId, status) {
  return request(`/api/v1/orders/${tenantId}/${orderId}/status`, {
    method: "PUT",
    token,
    body: { status },
  });
}

// --- Jobs ---

export function fetchJobs(tenantId, token) {
  return request(`/api/v1/jobs/${tenantId}`, { token });
}

export function createJob(tenantId, token, jobData) {
  return request(`/api/v1/jobs/${tenantId}`, { method: "POST", token, body: jobData });
}

export function updateJob(tenantId, token, jobId, jobData) {
  return request(`/api/v1/jobs/${tenantId}/${jobId}`, { method: "PUT", token, body: jobData });
}

export function deleteJob(tenantId, token, jobId) {
  return request(`/api/v1/jobs/${tenantId}/${jobId}`, { method: "DELETE", token });
}

export function fetchJobApplications(tenantId, token, jobId) {
  return request(`/api/v1/jobs/${tenantId}/${jobId}/applications`, { token });
}

export function updateApplicationStatus(tenantId, token, appId, status, notes) {
  return request(`/api/v1/jobs/${tenantId}/applications/${appId}/status`, {
    method: "PUT",
    token,
    body: { status, notes },
  });
}

export function aiWriteJobDescription(tenantId, token, roleDescription) {
  return request(`/api/v1/jobs/${tenantId}/ai-write`, {
    method: "POST",
    token,
    body: { role_description: roleDescription },
  });
}

// --- Tag Definitions ---

export function fetchTagDefinitions(tenantId, token) {
  return request(`/api/v1/tags/${tenantId}`, { token });
}

export function createTagDefinition(tenantId, token, data) {
  return request(`/api/v1/tags/${tenantId}`, { method: "POST", token, body: data });
}

export function updateTagDefinition(tenantId, token, tagId, data) {
  return request(`/api/v1/tags/${tenantId}/${tagId}`, { method: "PUT", token, body: data });
}

export function deleteTagDefinition(tenantId, token, tagId) {
  return request(`/api/v1/tags/${tenantId}/${tagId}`, { method: "DELETE", token });
}

// --- Action Items ---

export function fetchActionItems(tenantId, token, params = {}) {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.priority) qs.set("priority", params.priority);
  if (params.limit) qs.set("limit", params.limit);
  const q = qs.toString();
  return request(`/api/v1/action-items/${tenantId}${q ? `?${q}` : ""}`, { token });
}

export function fetchActionItemsSummary(tenantId, token) {
  return request(`/api/v1/action-items/${tenantId}/summary`, { token });
}

export function createActionItem(tenantId, token, data) {
  return request(`/api/v1/action-items/${tenantId}`, { method: "POST", token, body: data });
}

export function updateActionItem(tenantId, token, itemId, data) {
  return request(`/api/v1/action-items/${tenantId}/${itemId}`, { method: "PUT", token, body: data });
}

export function deleteActionItem(tenantId, token, itemId) {
  return request(`/api/v1/action-items/${tenantId}/${itemId}`, { method: "DELETE", token });
}

// --- Shared Inbox ---

export function assignConversation(tenantId, token, conversationId, assignedTo) {
  return request(`/api/v1/inbox/${tenantId}/conversations/${conversationId}/assign`, {
    method: "PUT", token, body: { assigned_to: assignedTo },
  });
}

export function fetchConversationNotes(tenantId, token, conversationId) {
  return request(`/api/v1/inbox/${tenantId}/conversations/${conversationId}/notes`, { token });
}

export function createConversationNote(tenantId, token, conversationId, content) {
  return request(`/api/v1/inbox/${tenantId}/conversations/${conversationId}/notes`, {
    method: "POST", token, body: { content },
  });
}

export function deleteConversationNote(tenantId, token, noteId) {
  return request(`/api/v1/inbox/${tenantId}/notes/${noteId}`, { method: "DELETE", token });
}

export { ApiError };
