/**
 * Phone number provisioning API functions.
 */
import { request } from "./_client";

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
