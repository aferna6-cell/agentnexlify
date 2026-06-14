import { request } from "./_client";

export async function fetchQualifierSettings(tenantId, token) {
  return request(`/api/v1/qualifier/${tenantId}`, { token });
}

export async function updateQualifierSettings(tenantId, data, token) {
  return request(`/api/v1/qualifier/${tenantId}`, { method: "PUT", body: data, token });
}
