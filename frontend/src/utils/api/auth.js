/**
 * Auth API functions — login, demo login, etc.
 * Uses raw fetch (not the request() helper) because these endpoints
 * return tokens before auth is established.
 */

import { BASE } from "./_client";

/**
 * POST /api/v1/auth/demo-login
 * No body, no auth required. Rate-limited 10/min.
 * Optional vertical param selects the demo tenant vertical.
 * Valid values: "plumbing" | "salon" | "financial_services"
 * Absent or unknown value falls back to "plumbing" on the backend.
 * Returns { tenant_id, token, business_name, plan, demo }
 */
export async function demoLogin(vertical) {
  const params = new URLSearchParams();
  if (vertical) {
    params.set("vertical", vertical);
  }
  const qs = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${BASE}/api/v1/auth/demo-login${qs}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Demo login failed. Please try again.");
  }
  return res.json();
}
