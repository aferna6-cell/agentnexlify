/**
 * Auth API functions — login, demo login, etc.
 * Uses raw fetch (not the request() helper) because these endpoints
 * return tokens before auth is established.
 */

import { BASE } from "./_client";

/**
 * POST /api/v1/auth/demo-login
 * No body, no auth required. Rate-limited 10/min.
 * Returns { tenant_id, token, business_name, plan, demo }
 */
export async function demoLogin() {
  const res = await fetch(`${BASE}/api/v1/auth/demo-login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Demo login failed. Please try again.");
  }
  return res.json();
}
