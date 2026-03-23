/**
 * FAQ entry management API functions.
 */
import { request, BASE, ApiError } from "./_client";

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

export function suggestFaqEntries(tenantId, token) {
  return request(`/api/v1/auth/faq/${tenantId}/suggest`, { method: "POST", token });
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
