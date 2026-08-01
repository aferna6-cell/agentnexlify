/**
 * Prospecting API functions - Google Places-driven local business search
 * that feeds a promote/reject queue into leads. Tenant is derived from the
 * JWT; no tenant id in the path.
 */
import { request } from "./_client";

export function fetchProspectingStatus(token) {
  return request("/api/v1/prospecting/status", { token });
}

export function searchProspects(token, { query, location, limit }) {
  return request("/api/v1/prospecting/search", {
    method: "POST",
    token,
    body: { query, location, limit },
  });
}

export function fetchProspects(token, status) {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/v1/prospecting/prospects${qs}`, { token });
}

export function promoteProspect(token, prospectId) {
  return request(`/api/v1/prospecting/prospects/${prospectId}/promote`, {
    method: "POST",
    token,
  });
}

export function rejectProspect(token, prospectId) {
  return request(`/api/v1/prospecting/prospects/${prospectId}/reject`, {
    method: "POST",
    token,
  });
}
