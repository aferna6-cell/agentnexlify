/**
 * Integration API functions (Google Calendar, Microsoft 365, HubSpot, Facebook).
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

// --- HubSpot ---

export function fetchHubSpotStatus(tenantId, token) {
  return request(`/api/v1/integrations/hubspot/status`, { token });
}

export function startHubSpotAuth(tenantId, token) {
  return request(`/api/v1/integrations/hubspot/auth`, { token });
}

export function disconnectHubSpot(tenantId, token) {
  return request(`/api/v1/integrations/hubspot`, { method: "DELETE", token });
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

// --- Instagram Business ---

export function fetchInstagramStatus(tenantId, token) {
  return request(`/api/v1/channels/instagram/${tenantId}/status`, { token });
}

export function getInstagramAuthUrl(tenantId, token) {
  return request(`/api/v1/channels/instagram/auth`, { token });
}

export function disconnectInstagram(tenantId, token) {
  return request(`/api/v1/channels/instagram/${tenantId}/disconnect`, {
    method: "DELETE",
    token,
  });
}

// --- Gmail ---

export function startGmailAuth(tenantId, token) {
  return request(`/api/v1/integrations/gmail/connect`, { token });
}

export function fetchGmailStatus(tenantId, token) {
  return request(`/api/v1/integrations/gmail/status`, { token });
}

export function disconnectGmail(tenantId, token) {
  return request(`/api/v1/integrations/gmail/disconnect`, {
    method: "POST",
    token,
  });
}

// --- Agent OS Inbound Bridges ---

export function fetchBridgeConfig(token) {
  return request(`/api/v1/os/inbound/bridge-config`, { token });
}

export function toggleBridge(source, enabled, token) {
  return request(`/api/v1/os/inbound/bridge-toggle`, {
    method: "POST",
    token,
    body: { source, enabled },
  });
}

export function saveBridgeConfig(updates, token) {
  return request(`/api/v1/os/inbound/bridge-config`, {
    method: "POST",
    token,
    body: updates,
  });
}
