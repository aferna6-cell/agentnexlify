/**
 * Tenant KB sources API - bulk upload, provenance list, Drive sync.
 * (backend/routers/tenant_kb.py + backend/routers/kb_integrations.py)
 */
import { BASE, request } from "./_client";

export function listKbDocuments(tenantId, token) {
  return request(`/api/v1/kb/${tenantId}/documents`, { token });
}

export function deleteKbDocument(tenantId, docId, token) {
  return request(`/api/v1/kb/${tenantId}/documents/${docId}`, {
    method: "DELETE",
    token,
  });
}

export function recompileKb(tenantId, token) {
  return request(`/api/v1/kb/${tenantId}/recompile`, { method: "POST", token });
}

// Multipart upload - bypasses the JSON request() helper on purpose.
export async function uploadKbDocuments(tenantId, token, files) {
  const form = new FormData();
  for (const file of files) form.append("files", file, file.name);
  const res = await fetch(`${BASE}/api/v1/kb/${tenantId}/documents`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) throw new Error(`Upload failed (${res.status})`);
  return res.json();
}

// Long-lived (180d) scoped token for the local folder-sync CLI.
export function createKbSyncToken(tenantId, token) {
  return request(`/api/v1/kb/${tenantId}/sync-token`, {
    method: "POST",
    token,
  });
}

export function getDriveStatus(token) {
  return request("/api/v1/kb/integrations/drive/status", { token });
}

export function getDriveAuthUrl(token) {
  return request("/api/v1/kb/integrations/drive/auth", { token });
}

export function listDriveFolders(token) {
  return request("/api/v1/kb/integrations/drive/folders", { token });
}

export function setDriveFolder(token, folderId, folderName) {
  return request("/api/v1/kb/integrations/drive/folder", {
    method: "POST",
    token,
    body: { folder_id: folderId, folder_name: folderName },
  });
}

export function driveSyncNow(token) {
  return request("/api/v1/kb/integrations/drive/sync-now", {
    method: "POST",
    token,
  });
}

export function getDriveSyncLog(token) {
  return request("/api/v1/kb/integrations/drive/sync-log", { token });
}

export function disconnectDrive(token) {
  return request("/api/v1/kb/integrations/drive/", { method: "DELETE", token });
}
