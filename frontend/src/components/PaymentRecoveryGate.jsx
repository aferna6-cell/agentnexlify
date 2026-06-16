/**
 * PaymentRecoveryGate - shown to a LAPSED paying tenant whose card failed.
 *
 * Distinct from the new-signup plan picker: a tenant in past_due / paused /
 * unpaid previously had a subscription, so the right action is "update your
 * card", not "choose a plan". Opens the Stripe billing portal (where they can
 * fix the card / pay the open invoice). Access is restored automatically when
 * the retry succeeds (backend _handle_payment_succeeded un-pauses).
 *
 * No localStorage (artifact sandbox rule). React state only.
 */

import { useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://agentnexlify-production.up.railway.app";

// Statuses that mean "was paying, payment lapsed" - recovery, not signup.
export const RECOVERY_STATUSES = new Set(["past_due", "paused", "unpaid"]);

export default function PaymentRecoveryGate({ tenantId, token }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function openPortal() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/auth/billing/portal/${tenantId}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.portal_url) {
        window.location.href = data.portal_url;
        return;
      }
      setError(
        (data && data.detail) ||
          "Could not open the billing portal. Please try again.",
      );
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      data-testid="payment-recovery-gate"
      style={{
        minHeight: "100vh",
        background: "var(--bg-primary, #0a0a0f)",
        color: "var(--text-primary, #e2e8f0)",
        fontFamily: "system-ui, sans-serif",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 24px",
      }}
    >
      <div style={{ maxWidth: 460, width: "100%", textAlign: "center" }}>
        <span style={{ fontSize: "1.1rem", fontWeight: 700, color: "#6366f1" }}>
          AgentNexLiFy
        </span>
        <h1
          style={{
            fontSize: "1.5rem",
            fontWeight: 700,
            marginTop: 16,
            marginBottom: 10,
          }}
        >
          Your payment didn't go through
        </h1>
        <p
          style={{
            color: "rgba(255,255,255,0.6)",
            fontSize: "0.92rem",
            margin: "0 0 24px",
            lineHeight: 1.5,
          }}
        >
          Your subscription is paused because the last charge failed. Update
          your card to restore access right away - your data is safe.
        </p>

        {error && (
          <div
            style={{
              background: "rgba(220,38,38,0.1)",
              border: "1px solid rgba(220,38,38,0.3)",
              borderRadius: 10,
              padding: 14,
              marginBottom: 20,
              color: "#f87171",
              fontSize: "0.9rem",
            }}
          >
            {error}
          </div>
        )}

        <button
          onClick={openPortal}
          disabled={loading}
          style={{
            width: "100%",
            padding: "12px",
            background: "#6366f1",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            fontWeight: 600,
            cursor: loading ? "not-allowed" : "pointer",
            fontSize: "0.9rem",
            opacity: loading ? 0.7 : 1,
            minHeight: 44,
          }}
        >
          {loading ? "Opening billing..." : "Update payment method"}
        </button>

        <p
          style={{
            marginTop: 24,
            fontSize: "0.8rem",
            color: "rgba(255,255,255,0.3)",
          }}
        >
          Need help?{" "}
          <a href="/contact" style={{ color: "#a5b4fc" }}>
            Contact us
          </a>
        </p>
      </div>
    </div>
  );
}
