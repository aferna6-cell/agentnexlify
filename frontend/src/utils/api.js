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

export function createLead(tenantId, token, data) {
  return request(`/api/v1/leads/${tenantId}`, { method: "POST", token, body: data });
}
export function fetchLeads(tenantId, token, { stage, search, sort, order, assigned_to, page, per_page } = {}) {
  const params = new URLSearchParams();
  if (stage) params.set("stage", stage);
  if (search) params.set("search", search);
  if (sort) params.set("sort", sort);
  if (order) params.set("order", order);
  if (assigned_to) params.set("assigned_to", assigned_to);
  if (page) params.set("page", String(page));
  if (per_page) params.set("per_page", String(per_page));
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
export function sendLeadSms(tenantId, token, leadId, message) {
  return request(`/api/v1/leads/${tenantId}/${leadId}/sms`, {
    method: "POST",
    token,
    body: { message },
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

export function fetchConversations(tenantId, token, { channel } = {}) {
  const params = new URLSearchParams();
  if (channel) params.set("channel", channel);
  const qs = params.toString();
  return request(`/api/v1/auth/conversations/${tenantId}${qs ? `?${qs}` : ""}`, { token });
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

export function replyToConversation(tenantId, token, conversationId, content) {
  return request(`/api/v1/inbox/${tenantId}/conversations/${conversationId}/reply`, {
    method: "POST", token, body: { content },
  });
}

export function updatePresence(tenantId, token, conversationId) {
  return request(`/api/v1/inbox/${tenantId}/presence${conversationId ? `?conversation_id=${conversationId}` : ""}`, {
    method: "PUT", token,
  });
}

export function getPresence(tenantId, token) {
  return request(`/api/v1/inbox/${tenantId}/presence`, { token });
}

// --- Snippets ---

export function fetchSnippets(tenantId, token, params = {}) {
  const qs = new URLSearchParams();
  if (params.category) qs.set("category", params.category);
  if (params.search) qs.set("search", params.search);
  const q = qs.toString();
  return request(`/api/v1/snippets/${tenantId}${q ? `?${q}` : ""}`, { token });
}

export function getSnippet(tenantId, token, snippetId) {
  return request(`/api/v1/snippets/${tenantId}/${snippetId}`, { token });
}

export function createSnippet(tenantId, token, data) {
  return request(`/api/v1/snippets/${tenantId}`, { method: "POST", token, body: data });
}

export function updateSnippet(tenantId, token, snippetId, data) {
  return request(`/api/v1/snippets/${tenantId}/${snippetId}`, { method: "PUT", token, body: data });
}

export function deleteSnippet(tenantId, token, snippetId) {
  return request(`/api/v1/snippets/${tenantId}/${snippetId}`, { method: "DELETE", token });
}

// --- Chat Flows ---

export function fetchChatFlows(tenantId, token) {
  return request(`/api/v1/chat-flows/${tenantId}`, { token });
}

export function fetchFlowTemplates(tenantId, token) {
  return request(`/api/v1/chat-flows/${tenantId}/templates`, { token });
}

export function createChatFlow(tenantId, token, data) {
  return request(`/api/v1/chat-flows/${tenantId}`, { method: "POST", token, body: data });
}

export function createFlowFromTemplate(tenantId, token, templateIndex) {
  return request(`/api/v1/chat-flows/${tenantId}/from-template/${templateIndex}`, { method: "POST", token });
}

export function updateChatFlow(tenantId, token, flowId, data) {
  return request(`/api/v1/chat-flows/${tenantId}/${flowId}`, { method: "PUT", token, body: data });
}

export function deleteChatFlow(tenantId, token, flowId) {
  return request(`/api/v1/chat-flows/${tenantId}/${flowId}`, { method: "DELETE", token });
}

// --- Snippet Suggestion ---

export function suggestSnippet(tenantId, token, conversationContext) {
  return request(`/api/v1/snippets/${tenantId}/suggest`, {
    method: "POST", token, body: { conversation_context: conversationContext },
  });
}

// --- Lead Suggestions ---

export function fetchLeadSuggestions(tenantId, token) {
  return request(`/api/v1/leads/${tenantId}/suggestions`, { token });
}

export function handleLeadSuggestion(tenantId, token, suggestionId, action) {
  return request(`/api/v1/leads/${tenantId}/suggestions/${suggestionId}`, {
    method: "POST", token, body: { action },
  });
}

// --- MCP API Keys ---

export function generateMcpKey(tenantId, token) {
  return request(`/api/v1/auth/mcp-key/${tenantId}`, { method: "POST", token });
}

export function revokeMcpKey(tenantId, token) {
  return request(`/api/v1/auth/mcp-key/${tenantId}`, { method: "DELETE", token });
}

// --- Bids ---

export function fetchBids(tenantId, token, { status } = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString() ? `?${params}` : "";
  return request(`/api/v1/bids/${tenantId}${qs}`, { token });
}

export function createBid(tenantId, token, data) {
  return request(`/api/v1/bids/${tenantId}`, { method: "POST", token, body: data });
}

export function updateBid(tenantId, token, bidId, data) {
  return request(`/api/v1/bids/${tenantId}/${bidId}`, { method: "PUT", token, body: data });
}

export function deleteBid(tenantId, token, bidId) {
  return request(`/api/v1/bids/${tenantId}/${bidId}`, { method: "DELETE", token });
}

export function updateBidStatus(tenantId, token, bidId, status) {
  return request(`/api/v1/bids/${tenantId}/${bidId}/status`, { method: "PUT", token, body: { status } });
}

export function fetchBidStats(tenantId, token) {
  return request(`/api/v1/bids/${tenantId}/stats`, { token });
}

export function fetchBidTemplates(tenantId, token) {
  return request(`/api/v1/bids/${tenantId}/templates`, { token });
}

export function createBidTemplate(tenantId, token, data) {
  return request(`/api/v1/bids/${tenantId}/templates`, { method: "POST", token, body: data });
}

export function deleteBidTemplate(tenantId, token, templateId) {
  return request(`/api/v1/bids/${tenantId}/templates/${templateId}`, { method: "DELETE", token });
}

export function aiGenerateBid(tenantId, token, jobDescription) {
  return request(`/api/v1/bids/${tenantId}/ai-generate`, { method: "POST", token, body: { job_description: jobDescription } });
}

// --- Client Portal ---

export function fetchServiceRecords(tenantId, token) {
  return request(`/api/v1/portal/${tenantId}/service-records`, { token });
}

export function createServiceRecord(tenantId, token, data) {
  return request(`/api/v1/portal/${tenantId}/service-records`, { method: "POST", token, body: data });
}

export function updateServiceRecord(tenantId, token, recordId, data) {
  return request(`/api/v1/portal/${tenantId}/service-records/${recordId}`, { method: "PUT", token, body: data });
}

export function deleteServiceRecord(tenantId, token, recordId) {
  return request(`/api/v1/portal/${tenantId}/service-records/${recordId}`, { method: "DELETE", token });
}

export function generatePortalLink(tenantId, token, leadId) {
  return request(`/api/v1/portal/${tenantId}/portal-link/${leadId}`, { method: "POST", token });
}

// --- Calls ---

export function fetchCalls(tenantId, token, { status } = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString() ? `?${params}` : "";
  return request(`/api/v1/calls/${tenantId}${qs}`, { token });
}

export function fetchCallDetail(tenantId, token, callId) {
  return request(`/api/v1/calls/${tenantId}/${callId}`, { token });
}

export function fetchCallStats(tenantId, token) {
  return request(`/api/v1/calls/${tenantId}/stats`, { token });
}

// --- Local SEO ---

export function analyzeSeoProfile(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/analyze`, { method: "POST", token });
}

export function fetchSeoProfile(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}`, { token });
}

export function fetchSeoKeywords(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/keywords`, { token });
}

// --- SEO Audit ---

export function runSeoAudit(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/audit`, { method: "POST", token });
}

export function fetchSeoAudit(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/audit`, { token });
}

export function fetchSeoAuditHistory(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/audit/history`, { token });
}

// --- GEO Score (AI Visibility) ---

export function runGeoScore(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/geo-score`, { method: "POST", token });
}

export function fetchGeoScore(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/geo-score`, { token });
}

// --- Keyword Tracking ---

export function trackKeywords(tenantId, token, keywords) {
  return request(`/api/v1/seo/${tenantId}/keywords/track`, { method: "POST", token, body: { keywords } });
}

export function fetchKeywordRankings(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/keywords/rankings`, { token });
}

// --- Missed Call Analytics ---

export function fetchMissedCallAnalytics(tenantId, token, period = "30d") {
  return request(`/api/v1/analytics/${tenantId}/missed-calls?period=${period}`, { token });
}

// --- Onboarding Status ---

export function fetchOnboardingStatus(tenantId, token) {
  return request(`/api/v1/onboarding/${tenantId}/status`, { token });
}

// --- Client Portal Public ---

export function fetchClientPortalPublic(portalToken) {
  return request(`/api/v1/portal/portal/${portalToken}`);
}

// --- Social Media ---

export function fetchSocialPosts(tenantId, token, filters = {}) {
  const params = new URLSearchParams();
  if (filters.platform) params.set("platform", filters.platform);
  if (filters.status) params.set("status", filters.status);
  const qs = params.toString();
  return request(`/api/v1/social/${tenantId}/posts${qs ? "?" + qs : ""}`, { token });
}

export function createSocialPost(tenantId, token, data) {
  return request(`/api/v1/social/${tenantId}/posts`, { method: "POST", token, body: data });
}

export function updateSocialPost(tenantId, token, postId, data) {
  return request(`/api/v1/social/${tenantId}/posts/${postId}`, { method: "PUT", token, body: data });
}

export function deleteSocialPost(tenantId, token, postId) {
  return request(`/api/v1/social/${tenantId}/posts/${postId}`, { method: "DELETE", token });
}

export function generateSocialContent(tenantId, token, data) {
  return request(`/api/v1/social/${tenantId}/generate`, { method: "POST", token, body: data });
}

export function generateSocialCampaign(tenantId, token, data) {
  return request(`/api/v1/social/${tenantId}/generate-campaign`, { method: "POST", token, body: data });
}

export function fetchSocialCalendar(tenantId, token, month, year) {
  return request(`/api/v1/social/${tenantId}/calendar?month=${month}&year=${year}`, { token });
}

export function fetchSocialAnalytics(tenantId, token) {
  return request(`/api/v1/social/${tenantId}/analytics`, { token });
}

// --- Marketing Campaigns ---

export function fetchMarketingCampaigns(tenantId, token, filters = {}) {
  const params = new URLSearchParams();
  if (filters.type) params.set("type", filters.type);
  if (filters.status) params.set("status", filters.status);
  const qs = params.toString();
  return request(`/api/v1/campaigns/${tenantId}${qs ? "?" + qs : ""}`, { token });
}

export function createMarketingCampaign(tenantId, token, data) {
  return request(`/api/v1/campaigns/${tenantId}`, { method: "POST", token, body: data });
}

export function sendMarketingCampaign(tenantId, token, campaignId) {
  return request(`/api/v1/campaigns/${tenantId}/${campaignId}/send`, { method: "POST", token });
}

export function fetchCampaignDetail(tenantId, token, campaignId) {
  return request(`/api/v1/campaigns/${tenantId}/${campaignId}`, { token });
}

export function fetchCampaignAnalytics(tenantId, token, campaignId) {
  return request(`/api/v1/campaigns/${tenantId}/${campaignId}/analytics`, { token });
}

export function generateCampaignContent(tenantId, token, data) {
  return request(`/api/v1/campaigns/${tenantId}/generate-email`, { method: "POST", token, body: data });
}

export function estimateCampaignRecipients(tenantId, token, filters) {
  return request(`/api/v1/campaigns/${tenantId}/estimate`, { method: "POST", token, body: filters });
}

// Invoices
export function fetchInvoices(tenantId, token, filters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.lead_id) params.set("lead_id", filters.lead_id);
  const qs = params.toString();
  return request(`/api/v1/invoices/${tenantId}${qs ? "?" + qs : ""}`, { token });
}
export function createInvoice(tenantId, token, data) {
  return request(`/api/v1/invoices/${tenantId}`, { method: "POST", token, body: data });
}
export function updateInvoice(tenantId, token, invoiceId, data) {
  return request(`/api/v1/invoices/${tenantId}/${invoiceId}`, { method: "PUT", token, body: data });
}
export function deleteInvoice(tenantId, token, invoiceId) {
  return request(`/api/v1/invoices/${tenantId}/${invoiceId}`, { method: "DELETE", token });
}
export function sendInvoice(tenantId, token, invoiceId, data) {
  return request(`/api/v1/invoices/${tenantId}/${invoiceId}/send`, { method: "POST", token, body: data });
}
export function markInvoicePaid(tenantId, token, invoiceId) {
  return request(`/api/v1/invoices/${tenantId}/${invoiceId}/mark-paid`, { method: "POST", token, body: {} });
}
export function fetchInvoiceStats(tenantId, token) {
  return request(`/api/v1/invoices/${tenantId}/stats`, { token });
}
export function createInvoiceFromBid(tenantId, token, bidId) {
  return request(`/api/v1/invoices/${tenantId}/from-bid/${bidId}`, { method: "POST", token });
}

// Pipeline
export function fetchPipelineStages(tenantId, token) {
  return request(`/api/v1/pipeline/${tenantId}/stages`, { token });
}
export function fetchPipelineBoard(tenantId, token) {
  return request(`/api/v1/pipeline/${tenantId}/board`, { token });
}
export function fetchPipelineAnalytics(tenantId, token) {
  return request(`/api/v1/pipeline/${tenantId}/analytics`, { token });
}
export function movePipelineLead(tenantId, token, leadId, data) {
  return request(`/api/v1/pipeline/${tenantId}/move/${leadId}`, { method: "PUT", token, body: data });
}

// AI Insights
export function fetchAIInsights(tenantId, token) {
  return request(`/api/v1/analytics/${tenantId}/ai-insights`, { token });
}

// Smart Lists
export function fetchSmartLists(tenantId, token) {
  return request(`/api/v1/smart-lists/${tenantId}`, { token });
}
export function createSmartList(tenantId, token, data) {
  return request(`/api/v1/smart-lists/${tenantId}`, { method: "POST", token, body: data });
}
export function updateSmartList(tenantId, token, listId, data) {
  return request(`/api/v1/smart-lists/${tenantId}/${listId}`, { method: "PUT", token, body: data });
}
export function deleteSmartList(tenantId, token, listId) {
  return request(`/api/v1/smart-lists/${tenantId}/${listId}`, { method: "DELETE", token });
}
export function fetchSmartListLeads(tenantId, token, listId) {
  return request(`/api/v1/smart-lists/${tenantId}/${listId}/leads`, { token });
}
export function refreshSmartList(tenantId, token, listId) {
  return request(`/api/v1/smart-lists/${tenantId}/${listId}/refresh`, { method: "POST", token });
}
export async function exportSmartList(tenantId, token, listId) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}/api/v1/smart-lists/${tenantId}/${listId}/export`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, err);
  }
  return res.blob();
}

// Forms
export function fetchForms(tenantId, token) {
  return request(`/api/v1/forms/${tenantId}`, { token });
}
export function createForm(tenantId, token, data) {
  return request(`/api/v1/forms/${tenantId}`, { method: "POST", token, body: data });
}
export function fetchForm(tenantId, token, formId) {
  return request(`/api/v1/forms/${tenantId}/${formId}`, { token });
}
export function updateForm(tenantId, token, formId, data) {
  return request(`/api/v1/forms/${tenantId}/${formId}`, { method: "PUT", token, body: data });
}
export function deleteForm(tenantId, token, formId) {
  return request(`/api/v1/forms/${tenantId}/${formId}`, { method: "DELETE", token });
}
export function fetchFormSubmissions(tenantId, token, formId) {
  return request(`/api/v1/forms/${tenantId}/${formId}/submissions`, { token });
}
export function fetchFormStats(tenantId, token) {
  return request(`/api/v1/forms/${tenantId}/stats`, { token });
}

// --- CSAT ---

export function fetchCSATStats(tenantId, token, period = "30d") {
  return request(`/api/v1/csat/${tenantId}/stats?period=${period}`, { token });
}

export function fetchCSATResponses(tenantId, token) {
  return request(`/api/v1/csat/${tenantId}/responses`, { token });
}

// --- Phone Provisioning ---

export function searchAvailableNumbers(tenantId, token, areaCode) {
  return request(`/api/v1/phone/${tenantId}/available?area_code=${encodeURIComponent(areaCode)}`, { token });
}

export function provisionPhoneNumber(tenantId, token, areaCode) {
  return request(`/api/v1/phone/${tenantId}/provision`, {
    method: "POST",
    token,
    body: { area_code: areaCode },
  });
}

export function releasePhoneNumber(tenantId, token) {
  return request(`/api/v1/phone/${tenantId}/release`, { method: "DELETE", token });
}

// Provision a specific phone number by its E.164 string (e.g. "+15125551234")
export function provisionPhone(tenantId, token, phoneNumber) {
  return request(`/api/v1/phone/${tenantId}/provision`, {
    method: "POST",
    token,
    body: { phone_number: phoneNumber },
  });
}

// Release the provisioned phone number for this tenant
export function releasePhone(tenantId, token) {
  return request(`/api/v1/phone/${tenantId}/release`, { method: "DELETE", token });
}

// --- Facebook Messenger Channel ---

export function fetchFacebookStatus(tenantId, token) {
  return request(`/api/v1/channels/facebook/${tenantId}/status`, { token });
}

export function getFacebookAuthUrl(tenantId, token) {
  return request(`/api/v1/channels/facebook/${tenantId}/auth-url`, { token });
}

export function disconnectFacebook(tenantId, token) {
  return request(`/api/v1/channels/facebook/${tenantId}/disconnect`, { method: "DELETE", token });
}

// --- Custom Fields ---

export function fetchFieldDefinitions(tenantId, token) {
  return request(`/api/v1/custom-fields/${tenantId}/definitions`, { token });
}

export function createFieldDefinition(tenantId, token, data) {
  return request(`/api/v1/custom-fields/${tenantId}/definitions`, { method: "POST", token, body: data });
}

export function deleteFieldDefinition(tenantId, token, fieldId) {
  return request(`/api/v1/custom-fields/${tenantId}/definitions/${fieldId}`, { method: "DELETE", token });
}

export function fetchLeadFieldValues(tenantId, token, leadId) {
  return request(`/api/v1/custom-fields/${tenantId}/values/${leadId}`, { token });
}

export function updateLeadFieldValues(tenantId, token, leadId, values) {
  return request(`/api/v1/custom-fields/${tenantId}/values/${leadId}`, { method: "PUT", token, body: values });
}

export { ApiError };
