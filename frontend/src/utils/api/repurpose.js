import { request } from "../api/_client.js";

export async function createRepurposeJob(tenantId, data) {
  return request(`/api/v1/repurpose/${tenantId}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listRepurposeJobs(tenantId, limit = 20, offset = 0) {
  return request(
    `/api/v1/repurpose/${tenantId}?limit=${limit}&offset=${offset}`,
  );
}

export async function getRepurposeJob(tenantId, jobId) {
  return request(`/api/v1/repurpose/${tenantId}/${jobId}`);
}

export async function updateRepurposeJob(tenantId, jobId, data) {
  return request(`/api/v1/repurpose/${tenantId}/${jobId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function connectRepurposeOutputs(tenantId, jobId, targets) {
  return request(`/api/v1/repurpose/${tenantId}/${jobId}/connect`, {
    method: "POST",
    body: JSON.stringify({ targets }),
  });
}

export async function deleteRepurposeJob(tenantId, jobId) {
  return request(`/api/v1/repurpose/${tenantId}/${jobId}`, {
    method: "DELETE",
  });
}
