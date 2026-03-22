/**
 * Business page (hosted landing page) API functions.
 */
import { request } from "./_client";

export function fetchBusinessPagePublic(slug) {
  return request(`/biz/${slug}`);
}

export function fetchBusinessPageSettings(tenantId, token) {
  return request(`/api/v1/business-page/${tenantId}`, { token });
}

export function updateBusinessPageSettings(tenantId, token, data) {
  return request(`/api/v1/business-page/${tenantId}`, { method: "PUT", token, body: data });
}
