import { useEffect } from "react";

const PLAN_ORDER = ["free", "growth", "autopilot", "professional", "enterprise"];

const PLAN_DISPLAY = {
  free: { name: "Free", price: "$0" },
  growth: { name: "Growth", price: "$99/mo" },
  professional: { name: "Professional", price: "$150/mo" },
  autopilot: { name: "Autopilot", price: "$299/mo" },
  enterprise: { name: "Enterprise", price: "$250/mo" },
};

const overlayStyle = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.65)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 2000,
};

const modalStyle = {
  background: "var(--bg-secondary, #1a1a2e)",
  border: "1px solid var(--border)",
  borderRadius: 16,
  padding: "32px 36px",
  width: "90%",
  maxWidth: 480,
  textAlign: "center",
  boxShadow: "0 24px 64px rgba(0,0,0,0.4)",
};

const bannerStyle = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 16,
  padding: "14px 20px",
  borderRadius: 12,
  background: "rgba(139,92,246,0.12)",
  border: "1px solid rgba(139,92,246,0.3)",
  marginBottom: 16,
};

/**
 * UpgradePrompt — reusable modal that appears when a user tries to access
 * a feature above their current plan.
 *
 * Props:
 *   feature       {string}   — human-readable feature name, e.g. "Local SEO"
 *   requiredPlan  {string}   — plan key required, e.g. "professional"
 *   onClose       {fn}       — called when the user dismisses without upgrading
 *   onNavigate    {fn}       — called with "billing" when Upgrade Now is clicked
 *   variant       {string}   — "modal" (default) | "banner"
 */
export default function UpgradePrompt({ feature, requiredPlan, onClose, onNavigate, variant = "modal" }) {
  const plan = PLAN_DISPLAY[requiredPlan] || { name: requiredPlan, price: "" };

  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose?.(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const handleUpgrade = () => {
    onNavigate?.("billing");
    onClose?.();
  };

  if (variant === "banner") {
    return (
      <div style={bannerStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: "1.2rem" }}>&#x1F512;</span>
          <div style={{ textAlign: "left" }}>
            <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-primary)" }}>
              {plan.name} plan required
            </div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: 2 }}>
              Upgrade to {plan.name} to unlock {feature}
            </div>
          </div>
        </div>
        <button
          onClick={handleUpgrade}
          style={{
            background: "var(--accent, #00bfff)",
            color: "#fff",
            border: "none",
            padding: "8px 18px",
            borderRadius: 8,
            fontWeight: 600,
            fontSize: "0.85rem",
            cursor: "pointer",
            whiteSpace: "nowrap",
            flexShrink: 0,
          }}
        >
          Upgrade Now
        </button>
      </div>
    );
  }

  // Default: modal
  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        {/* Lock icon */}
        <div style={{
          width: 64,
          height: 64,
          borderRadius: "50%",
          background: "rgba(139,92,246,0.15)",
          border: "2px solid rgba(139,92,246,0.4)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "1.8rem",
          margin: "0 auto 20px",
        }}>
          &#x1F512;
        </div>

        <h2 style={{ margin: "0 0 8px", fontSize: "1.25rem", color: "var(--text-primary)" }}>
          Upgrade to {plan.name}
        </h2>
        <p style={{ margin: "0 0 6px", color: "var(--text-secondary)", fontSize: "0.95rem" }}>
          to unlock {feature}
        </p>
        {plan.price && (
          <p style={{ margin: "0 0 24px", color: "var(--text-muted)", fontSize: "0.85rem" }}>
            Starting at {plan.price}
          </p>
        )}

        <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
          <button
            onClick={onClose}
            style={{
              background: "var(--bg-primary, #0d0d1a)",
              color: "var(--text-secondary)",
              border: "1px solid var(--border)",
              padding: "10px 22px",
              borderRadius: 8,
              fontWeight: 500,
              fontSize: "0.9rem",
              cursor: "pointer",
            }}
          >
            Maybe Later
          </button>
          <button
            onClick={handleUpgrade}
            style={{
              background: "linear-gradient(135deg, var(--accent, #00bfff), #8b5cf6)",
              color: "#fff",
              border: "none",
              padding: "10px 22px",
              borderRadius: 8,
              fontWeight: 600,
              fontSize: "0.9rem",
              cursor: "pointer",
            }}
          >
            Upgrade Now &rarr;
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Utility: return true if `currentPlan` is below `requiredPlan`.
 * Use this to conditionally render an UpgradePrompt.
 */
export function planBelowRequired(currentPlan, requiredPlan) {
  const current = PLAN_ORDER.indexOf(currentPlan ?? "free");
  const required = PLAN_ORDER.indexOf(requiredPlan);
  if (required === -1) return false;
  return current < required;
}
