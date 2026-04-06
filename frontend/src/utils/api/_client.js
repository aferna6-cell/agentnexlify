/**
 * Shared API client — used by all domain modules.
 * DO NOT import this directly in components. Import from ../api.js instead.
 */

export const BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://agentnexlify-production.up.railway.app";

export class ApiError extends Error {
  constructor(status, body) {
    super(body?.detail || `API error ${status}`);
    this.status = status;
    this.body = body;
  }
}

/**
 * Handle 401 by clearing token and redirecting to login.
 * Prevents "invalid or expired token" errors from appearing on every page.
 */
function handleUnauthorized() {
  localStorage.removeItem("anx_token");
  localStorage.removeItem("anx_tenant_id");
  // Only redirect if not already on login/signup/reset pages
  const path = window.location.pathname;
  if (
    !["/login", "/signup", "/reset-password", "/auth/callback"].some((p) =>
      path.startsWith(p),
    )
  ) {
    window.location.href = "/login?expired=1";
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
    if (res.status === 401) {
      handleUnauthorized();
      throw new ApiError(res.status, err);
    }
    throw new ApiError(res.status, err);
  }

  // 204 No Content — nothing to parse (common for DELETE endpoints)
  if (res.status === 204) return null;

  // Some endpoints may return empty bodies with 200/201
  const text = await res.text();
  if (!text) return null;
  return JSON.parse(text);
}
