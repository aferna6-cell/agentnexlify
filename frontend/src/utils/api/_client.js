/**
 * Shared API client — used by all domain modules.
 * DO NOT import this directly in components. Import from ../api.js instead.
 */

export const BASE = import.meta.env.VITE_API_BASE_URL || "https://agentnexlify-production.up.railway.app";

export class ApiError extends Error {
  constructor(status, body) {
    super(body?.detail || `API error ${status}`);
    this.status = status;
    this.body = body;
  }
}

export async function request(path, { method = "GET", body, token } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, err);
  }

  // 204 No Content — nothing to parse (common for DELETE endpoints)
  if (res.status === 204) return null;

  // Some endpoints may return empty bodies with 200/201
  const text = await res.text();
  if (!text) return null;
  return JSON.parse(text);
}
