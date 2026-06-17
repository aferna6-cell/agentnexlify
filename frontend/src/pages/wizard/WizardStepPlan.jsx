// frontend/src/pages/wizard/WizardStepPlan.jsx
import { useState } from "react";
import { completeOnboarding, checkoutForWizard, buildWizardPayload } from "../../utils/api/onboarding";

// Plan keys map to Stripe via PLAN_PRICES on the backend. Two plans only:
// Chatbot $19.99 (chatbot) / Full Agent OS $99.99 (agent_os). No free tier.
const PLANS = [
  {
    key: "chatbot",
    name: "AI Front Desk",
    price: "$19.99/mo",
    color: "#6366f1",
    features: ["AI chat widget", "Lead capture", "FAQ knowledge base", "Appointment booking"],
    cta: "Start AI Front Desk",
    highlight: false,
  },
  {
    key: "agent_os",
    name: "AI Workforce",
    price: "$99.99/mo",
    color: "#8b5cf6",
    features: ["Everything in AI Front Desk", "Your AI staff in AI Workforce", "Marketing, SEO & campaigns", "Automations & follow-ups"],
    cta: "Start AI Workforce",
    highlight: true,
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

      // Both plans are paid - redirect to Stripe Checkout
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
        Pick the plan that fits. Need something custom? <a href="/contact" style={{ color: "#a5b4fc" }}>Talk to us</a>.
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
