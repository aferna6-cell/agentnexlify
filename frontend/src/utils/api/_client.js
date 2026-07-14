/**
 * Shared API client - used by all domain modules.
 * DO NOT import this directly in components. Import from ../api.js instead.
 */

import { apiErrorMessage, reportError } from "../errorReporting";

export const BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://agentnexlify-production.up.railway.app";

export class ApiError extends Error {
  constructor(status, body = {}) {
    super(apiErrorMessage(status, body));
    this.status = status;
    this.body = body;
    this.requestId = body?.request_id || body?.requestId || null;
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

async function parseErrorBody(res) {
  if (typeof res.text === "function") {
    const text = await res.text().catch(() => "");
    if (!text) return {};
    try {
      return JSON.parse(text);
    } catch {
      return { detail: text };
    }
  }
  if (typeof res.json === "function") {
    return res.json().catch(() => ({}));
  }
  return {};
}

function responseHeader(res, name) {
  if (res.headers && typeof res.headers.get === "function") {
    return res.headers.get(name);
  }
  return null;
}

// A backend that accepts the connection then stalls would otherwise never
// settle this promise, leaving pages spinning forever (audit H11). Abort after
// this ceiling so callers get a real error and their `finally` clears the spinner.
const REQUEST_TIMEOUT_MS = 30000;

export async function request(path, { method = "GET", body, token } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (error) {
    const timedOut = error && error.name === "TimeoutError";
    reportError(error, {
      source: "api-client",
      path,
      method,
      phase: timedOut ? "timeout" : "network",
    });
    throw new ApiError(0, {
      detail: timedOut
        ? "The request timed out. Please try again."
        : "Network error. Check your connection and try again.",
    });
  }

  if (!res.ok) {
    const err = await parseErrorBody(res);
    const requestId = responseHeader(res, "x-request-id");
    if (requestId) err.request_id = requestId;
    if (res.status === 401) {
      handleUnauthorized();
      throw new ApiError(res.status, err);
    }
    if (res.status >= 500) {
      reportError(new ApiError(res.status, err), {
        source: "api-client",
        path,
        method,
        requestId,
      });
    }
    throw new ApiError(res.status, err);
  }

  // 204 No Content - nothing to parse (common for DELETE endpoints)
  if (res.status === 204) return null;

  // Some endpoints may return empty bodies with 200/201
  const text = await res.text();
  if (!text) return null;
  return JSON.parse(text);
}
