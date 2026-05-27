/**
 * Integration API functions (Google Calendar, Facebook Messenger).
 */
import { request } from "./_client";

// --- Google Calendar ---

export function fetchGoogleCalendarStatus(tenantId, token) {
  return request(`/api/v1/integrations/google/status`, { token });
}

export function startGoogleCalendarAuth(tenantId, token) {
  return request(`/api/v1/integrations/google/auth`, { token });
}

export function disconnectGoogleCalendar(tenantId, token) {
  return request(`/api/v1/integrations/google`, { method: "DELETE", token });
}

// --- Microsoft 365 Calendar ---

export function fetchM365CalendarStatus(tenantId, token) {
  return request(`/api/v1/integrations/m365/status`, { token });
}

export function startM365CalendarAuth(tenantId, token) {
  return request(`/api/v1/integrations/m365/auth`, { token });
}

export function disconnectM365Calendar(tenantId, token) {
  return request(`/api/v1/integrations/m365`, { method: "DELETE", token });
}

// --- Facebook Messenger ---

export function fetchFacebookStatus(tenantId, token) {
  return request(`/api/v1/channels/facebook/${tenantId}/status`, { token });
}

export function getFacebookAuthUrl(tenantId, token) {
  return request(`/api/v1/channels/facebook/${tenantId}/auth-url`, { token });
}

export function disconnectFacebook(tenantId, token) {
  return request(`/api/v1/channels/facebook/${tenantId}/disconnect`, {
    method: "DELETE",
    token,
  });
}
