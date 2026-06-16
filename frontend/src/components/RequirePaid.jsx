/**
 * RequirePaid - gate wrapper for authenticated routes that require an active plan.
 *
 * Renders children when:
 *   - user is loading (token present, user not yet parsed) - renders null (spinner-free)
 *   - user.payGateExempt is true (grandfathered tenant)
 *   - user.planStatus is "active" or "trialing"
 *
 * Otherwise renders a minimal checkout gate so the user can pick a plan and
 * pay before accessing the dashboard or onboarding wizard.
 *
 * Handles Stripe returns:
 *   - ?session_id= or ?checkout=success → re-fetches /me before deciding
 *   - On re-fetch confirms planStatus; if still unpaid shows error
 *
 * No localStorage (artifact sandbox rule). Uses React state only.
 */

import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import PaymentRecoveryGate, {
  RECOVERY_STATUSES,
} from "./PaymentRecoveryGate";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://agentnexlify-production.up.railway.app";

const ACTIVE_STATUSES = new Set(["active", "trialing"]);

const PLANS = [
  {
    key: "chatbot",
    name: "Chatbot",
    price: "$19.99/mo",
    features: [
      "AI chat widget",
      "Lead capture",
      "FAQ knowledge base",
      "Appointment booking",
    ],
    cta: "Start Chatbot",
    highlight: false,
  },
  {
    key: "agent_os",
    name: "Full Agent OS",
    price: "$99.99/mo",
    features: [
      "Everything in Chatbot",
      "Your AI staff in Agent OS",
      "Marketing, SEO & campaigns",
      "Automations & follow-ups",
    ],
    cta: "Start Agent OS",
    highlight: true,
  },
];

function shouldGate(user) {
  // Gate ONLY when we positively know the tenant is non-exempt AND not on an
  // active/trialing plan. Until /me resolves, payGateExempt is undefined - in
  // that window (and if /me fails) we do NOT gate: render children and let the
  // backend require_active_plan dependency enforce the critical endpoint. This
  // avoids ever stranding grandfathered or paying tenants on the gate.
  if (!user) return false;
  if (user.payGateExempt === undefined) return false; // not loaded / /me failed
  if (user.payGateExempt) return false; // grandfathered existing tenant
  return !ACTIVE_STATUSES.has(user.planStatus);
}

export default function RequirePaid({ children }) {
  const { user, token } = useAuth();
  const [searchParams] = useSearchParams();

  // State for the checkout-gate UI
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [checkoutError, setCheckoutError] = useState("");
  // State for re-fetching /me after a Stripe return
  const [verifying, setVerifying] = useState(false);
  const [meOverride, setMeOverride] = useState(null);

  // Stripe return detection - ?session_id or ?checkout=success
  const hasStripeReturn =
    searchParams.get("session_id") ||
    searchParams.get("checkout") === "success";

  useEffect(() => {
    if (!hasStripeReturn || !token) return;
    // Stripe's checkout.session.completed webhook is async - it can land AFTER
    // the customer is redirected back. A single /me fetch can race ahead of the
    // webhook and still see the unpaid plan, stranding a paying customer on the
    // gate. Poll with backoff (~10s total) and stop early once the webhook has
    // flipped plan_status to active/trialing (or the tenant is exempt).
    let cancelled = false;
    setVerifying(true);
    const delaysMs = [0, 750, 1500, 3000, 5000];
    async function poll() {
      for (let i = 0; i < delaysMs.length; i++) {
        if (delaysMs[i]) {
          await new Promise((resolve) => setTimeout(resolve, delaysMs[i]));
        }
        if (cancelled) return;
        let me = null;
        try {
          const r = await fetch(`${API_BASE}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          me = r.ok ? await r.json() : null;
        } catch {
          me = null;
        }
        if (cancelled) return;
        if (me) {
          setMeOverride(me);
          if (me.pay_gate_exempt || ACTIVE_STATUSES.has(me.plan_status)) break;
        }
      }
      if (!cancelled) setVerifying(false);
    }
    poll();
    return () => {
      cancelled = true;
    };
  }, [hasStripeReturn, token]);

  // Logged out OR token still parsing - render children so the downstream
  // route (App / OnboardingRoute) runs its own auth/login redirect. Never
  // block an unauthenticated visitor here (that would blank the login bounce).
  if (!user) return children;

  // Build an effective user object using the /me re-fetch override when present
  const effectiveUser = meOverride
    ? {
        ...user,
        planStatus: meOverride.plan_status ?? user.planStatus,
        payGateExempt: meOverride.pay_gate_exempt ?? user.payGateExempt,
      }
    : user;

  if (verifying) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--bg-primary, #0a0a0f)",
          color: "var(--text-secondary, rgba(255,255,255,0.6))",
        }}
      >
        Verifying payment...
      </div>
    );
  }

  if (!shouldGate(effectiveUser)) {
    return children;
  }

  // Lapsed payer (was subscribed, card failed) -> guide to update the card via
  // the Stripe billing portal instead of showing the new-signup plan picker.
  if (RECOVERY_STATUSES.has(effectiveUser.planStatus)) {
    return <PaymentRecoveryGate tenantId={effectiveUser.tenantId} token={token} />;
  }

  // Render the checkout gate
  async function handleChoosePlan(planKey) {
    setCheckoutLoading(true);
    setCheckoutError("");
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/billing/checkout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ plan: planKey }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.checkout_url) {
        window.location.href = data.checkout_url;
        return;
      }
      setCheckoutError(
        data.detail || "Checkout unavailable. Please try again."
      );
    } catch {
      setCheckoutError("Network error. Please try again.");
    } finally {
      setCheckoutLoading(false);
    }
  }

  return (
    <div
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
      <div style={{ maxWidth: 600, width: "100%" }}>
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <span
            style={{ fontSize: "1.1rem", fontWeight: 700, color: "#6366f1" }}
          >
            AgentNexLiFy
          </span>
          <h1
            style={{
              fontSize: "1.6rem",
              fontWeight: 700,
              marginTop: 16,
              marginBottom: 8,
            }}
          >
            Choose your plan to continue
          </h1>
          <p
            style={{
              color: "rgba(255,255,255,0.5)",
              fontSize: "0.9rem",
              margin: 0,
            }}
          >
            Pick the plan that fits your business. Cancel anytime.
          </p>
        </div>

        {checkoutError && (
          <div
            style={{
              background: "rgba(220,38,38,0.1)",
              border: "1px solid rgba(220,38,38,0.3)",
              borderRadius: 10,
              padding: 14,
              marginBottom: 20,
              color: "#f87171",
              fontSize: "0.9rem",
              textAlign: "center",
            }}
          >
            {checkoutError}
          </div>
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: 12,
          }}
        >
          {PLANS.map((plan) => (
            <div
              key={plan.key}
              style={{
                border: `1px solid ${plan.highlight ? "#6366f1" : "rgba(255,255,255,0.12)"}`,
                borderRadius: 12,
                padding: 20,
                background: plan.highlight
                  ? "rgba(99,102,241,0.1)"
                  : "rgba(255,255,255,0.04)",
                position: "relative",
              }}
            >
              {plan.highlight && (
                <div
                  style={{
                    position: "absolute",
                    top: -10,
                    left: "50%",
                    transform: "translateX(-50%)",
                    background: "#6366f1",
                    color: "#fff",
                    fontSize: "0.7rem",
                    fontWeight: 700,
                    padding: "3px 10px",
                    borderRadius: 20,
                  }}
                >
                  POPULAR
                </div>
              )}
              <div style={{ fontWeight: 700, fontSize: "1rem", marginBottom: 4 }}>
                {plan.name}
              </div>
              <div
                style={{
                  fontSize: "1.4rem",
                  fontWeight: 800,
                  color: "#6366f1",
                  marginBottom: 12,
                }}
              >
                {plan.price}
              </div>
              <ul
                style={{
                  margin: 0,
                  paddingLeft: 16,
                  fontSize: "0.82rem",
                  color: "rgba(255,255,255,0.7)",
                  marginBottom: 16,
                }}
              >
                {plan.features.map((f) => (
                  <li key={f} style={{ marginBottom: 4 }}>
                    {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => handleChoosePlan(plan.key)}
                disabled={checkoutLoading}
                style={{
                  width: "100%",
                  padding: "10px",
                  background: plan.highlight
                    ? "#6366f1"
                    : "rgba(255,255,255,0.08)",
                  color: "#fff",
                  border: "none",
                  borderRadius: 8,
                  fontWeight: 600,
                  cursor: checkoutLoading ? "not-allowed" : "pointer",
                  fontSize: "0.85rem",
                  opacity: checkoutLoading ? 0.7 : 1,
                  minHeight: 44,
                }}
              >
                {checkoutLoading ? "..." : plan.cta}
              </button>
            </div>
          ))}
        </div>

        <p
          style={{
            textAlign: "center",
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
