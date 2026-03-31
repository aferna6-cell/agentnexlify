/**
 * Reviews (Reputation Manager) API functions.
 */
import { request } from "./_client";

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

export function fetchReviewResponseStats(tenantId, token) {
  return request(`/api/v1/reviews/${tenantId}/response-stats`, { token });
}

export function requestReview(tenantId, token, leadId, channel) {
  return request(`/api/v1/reviews/${tenantId}/request-review/${leadId}`, {
    method: "POST",
    token,
    body: { channel },
  });
}
