/**
 * Local SEO, audit, GEO score, keyword tracking API functions.
 */
import { request } from "./_client";

// SEO Profile
export function analyzeSeoProfile(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/analyze`, { method: "POST", token });
}

export function fetchSeoProfile(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}`, { token });
}

export function fetchSeoKeywords(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/keywords`, { token });
}

// SEO Audit
export function runSeoAudit(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/audit`, { method: "POST", token });
}

export function fetchSeoAudit(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/audit`, { token });
}

export function fetchSeoAuditHistory(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/audit/history`, { token });
}

// GEO Score
export function runGeoScore(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/geo-score`, { method: "POST", token });
}

export function fetchGeoScore(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/geo-score`, { token });
}

// Keyword Tracking
export function trackKeywords(tenantId, token, keywords) {
  return request(`/api/v1/seo/${tenantId}/keywords/track`, { method: "POST", token, body: { keywords } });
}

export function fetchKeywordRankings(tenantId, token) {
  return request(`/api/v1/seo/${tenantId}/keywords/rankings`, { token });
}
