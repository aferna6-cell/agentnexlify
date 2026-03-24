import { request } from "./_client";

export async function fetchScoringFactors(tenantId, token) {
  return request(`/api/v1/scoring/${tenantId}`, { token });
}

export async function updateScoringFactor(tenantId, factorId, data, token) {
  return request(`/api/v1/scoring/${tenantId}/${factorId}`, { method: "PUT", body: data, token });
}

export async function createScoringFactor(tenantId, data, token) {
  return request(`/api/v1/scoring/${tenantId}`, { method: "POST", body: data, token });
}

export async function deleteScoringFactor(tenantId, factorId, token) {
  return request(`/api/v1/scoring/${tenantId}/${factorId}`, { method: "DELETE", token });
}

export async function resetScoringFactors(tenantId, token) {
  return request(`/api/v1/scoring/${tenantId}/reset`, { method: "POST", token });
}
