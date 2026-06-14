// frontend/src/pages/wizard/WizardStepPlan.jsx
import { useState } from "react";
import { completeOnboarding, checkoutForWizard, buildWizardPayload } from "../../utils/api/onboarding";

// Plan keys map to Stripe via PLAN_PRICES on the backend. Display names and
// prices must match the public pricing page: Free / Starter $99 (growth) /
// Growth $150 (autopilot) / Professional $250. Enterprise ($899) is sales-led.
const PLANS = [
  {
    key: "free",
    name: "Free",
    price: "$0/mo",
    color: "#64748b",
    features: ["Your AI staff in Agent OS", "AI chat widget", "Up to 50 conversations/mo", "Basic lead capture"],
    cta: "Continue Free",
    highlight: false,
  },
  {
    key: "growth",
    name: "Starter",
    price: "$99/mo",
    color: "#6366f1",
    features: ["7-day free trial", "Unlimited conversations", "CRM & lead management", "Email sequences"],
    cta: "Start Starter",
    highlight: false,
  },
  {
    key: "autopilot",
    name: "Growth",
    price: "$150/mo",
    color: "#8b5cf6",
    features: ["Everything in Starter", "Marketing campaigns", "Review requests", "Automated follow-ups"],
    cta: "Start Growth",
    highlight: true,
  },
  {
    key: "professional",
    name: "Professional",
    price: "$250/mo",
    color: "#0ea5e9",
    features: ["Everything in Growth", "AI answering service", "Priority support", "White-label options"],
    cta: "Start Professional",
    highlight: false,
  },
];

export default function WizardStepPlan({ wizardData, onNext, onBack, token, tenantId }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handlePlan(plan) {
    setLoading(true);
    setError("");
    try {
      // Always persist wizard data first
      await completeOnboarding(tenantId, token, buildWizardPayload(wizardData));

      if (plan === "free") {
        onNext({ chosen_plan: "free" });
        return;
      }

      // Paid plan - redirect to Stripe Checkout
      const res = await checkoutForWizard(token, plan);
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      } else {
        setError("Checkout failed. Try again.");
      }
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 8 }}>Choose your plan</h2>
      <p style={{ color: "rgba(255,255,255,0.5)", marginBottom: 32, fontSize: "0.9rem" }}>
        Start free, or try Starter free for 7 days before billing starts.
        Need Enterprise? <a href="/contact" style={{ color: "#a5b4fc" }}>Talk to us</a>.
      </p>

      {error && <div style={{ background: "rgba(220,38,38,0.1)", border: "1px solid rgba(220,38,38,0.3)", borderRadius: 10, padding: 14, marginBottom: 20, color: "#f87171", fontSize: "0.9rem" }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12, marginBottom: 24 }}>
        {PLANS.map(plan => (
          <div
            key={plan.key}
            style={{
              border: `1px solid ${plan.highlight ? plan.color : "rgba(255,255,255,0.12)"}`,
              borderRadius: 12,
              padding: 20,
              background: plan.highlight ? `rgba(99,102,241,0.1)` : "rgba(255,255,255,0.04)",
              position: "relative",
            }}
          >
            {plan.highlight && (
              <div style={{ position: "absolute", top: -10, left: "50%", transform: "translateX(-50%)", background: plan.color, color: "#fff", fontSize: "0.7rem", fontWeight: 700, padding: "3px 10px", borderRadius: 20 }}>POPULAR</div>
            )}
            <div style={{ fontWeight: 700, fontSize: "1rem", marginBottom: 4 }}>{plan.name}</div>
            <div style={{ fontSize: "1.4rem", fontWeight: 800, color: plan.color, marginBottom: 12 }}>{plan.price}</div>
            <ul style={{ margin: 0, paddingLeft: 16, fontSize: "0.82rem", color: "rgba(255,255,255,0.7)", marginBottom: 16 }}>
              {plan.features.map(f => <li key={f} style={{ marginBottom: 4 }}>{f}</li>)}
            </ul>
            <button
              onClick={() => handlePlan(plan.key)}
              disabled={loading}
              style={{
                width: "100%", padding: "10px", background: plan.highlight ? plan.color : "rgba(255,255,255,0.08)",
                color: "#fff", border: "none", borderRadius: 8, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
                fontSize: "0.85rem", opacity: loading ? 0.7 : 1, minHeight: 44,
              }}
            >
              {loading ? "..." : plan.cta}
            </button>
          </div>
        ))}
      </div>

      <button onClick={onBack} style={{ background: "none", border: "none", color: "rgba(255,255,255,0.4)", cursor: "pointer", fontSize: "0.85rem", padding: "12px", minHeight: 44 }}>Back</button>
    </div>
  );
}
