/**
 * Claude Managed Agents API - backend-driven agent runs.
 *
 * These endpoints are backed by `backend/routers/managed_agent_runs.py`
 * and spend container runtime + model tokens per call. Rate-limited at
 * the backend. Free tier is blocked server-side.
 */
import { request } from "./_client";

export function managedAgentsHealth(tenantId, token) {
  return request(`/api/v1/managed-agents/${tenantId}/health`, { token });
}

export function draftDocument(tenantId, token, body) {
  // body: { kind, lead_id?, customer, line_items, notes? }
  return request(`/api/v1/managed-agents/${tenantId}/draft-document`, {
    method: "POST",
    token,
    body,
  });
}

/**
 * Download a drafted document. Returns a blob - caller is responsible
 * for creating a temporary object URL and triggering browser download.
 */
export async function downloadDraftedDocument(tenantId, token, documentId) {
  const resp = await fetch(
    `${import.meta.env.VITE_API_BASE_URL || ""}/api/v1/managed-agents/${tenantId}/documents/${documentId}/download`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    const err = new Error(
      `Download failed (${resp.status}): ${text || resp.statusText}`,
    );
    err.status = resp.status;
    throw err;
  }
  const blob = await resp.blob();
  const cd = resp.headers.get("Content-Disposition") || "";
  const match = /filename="?([^";]+)"?/.exec(cd);
  const filename = match ? match[1] : `document-${documentId}`;
  return { blob, filename };
}
