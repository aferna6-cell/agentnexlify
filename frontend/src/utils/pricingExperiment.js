/* Pricing page A/B experiment client (launch rubric 9.3).
 *
 * Anonymous: visitor id is a first-party cookie UUID — no PII.
 * Fault-tolerant: any API failure falls back to the control variant and
 * silently drops events; the marketing page must never break on analytics.
 */
import { useEffect, useState } from "react";

const API =
  import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "";
const COOKIE = "anx_vid";

export function getVisitorId() {
  const match = document.cookie.match(new RegExp(`(?:^|; )${COOKIE}=([^;]+)`));
  if (match) return match[1];
  const id =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
  document.cookie = `${COOKIE}=${id}; path=/; max-age=31536000; SameSite=Lax`;
  return id;
}

export function trackPricingEvent(event, plan) {
  try {
    fetch(`${API}/api/v1/public/pricing-experiment/event`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        visitor_id: getVisitorId(),
        event,
        plan: plan || undefined,
      }),
      keepalive: true,
    }).catch(() => {});
  } catch {
    /* analytics never breaks the page */
  }
}

export function usePricingVariant() {
  const [variant, setVariant] = useState("control");

  useEffect(() => {
    let cancelled = false;
    const visitorId = getVisitorId();
    fetch(
      `${API}/api/v1/public/pricing-experiment?visitor_id=${encodeURIComponent(visitorId)}`
    )
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled && data && (data.variant === "control" || data.variant === "variant_b")) {
          setVariant(data.variant);
          trackPricingEvent("view");
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  return variant;
}
