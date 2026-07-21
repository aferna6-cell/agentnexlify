import { useEffect, useState } from "react";

/* App-wide upsell for the 402 plan gate.
 *
 * The API client dispatches "anx:plan-upgrade-required" whenever the backend
 * answers 402 with a plan_upgrade_required payload (agent_os_gate /
 * plan_gate). This banner renders that payload once, bottom-right, with a
 * link to the upgrade path - so a Front Desk (chatbot) tenant tapping a
 * suite card sees the offer instead of a dead error string. Dismiss hides it
 * for the rest of the page visit (component state only - no storage).
 */

export default function UpgradeGateBanner({ onNavigate }) {
  const [gate, setGate] = useState(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const onGate = (event) => {
      const detail = event?.detail || {};
      setGate({
        message:
          detail.message ||
          "This feature is part of the Agent OS plan. Upgrade to unlock it.",
        upgradePath: detail.upgrade_path || "/billing",
      });
    };
    window.addEventListener("anx:plan-upgrade-required", onGate);
    return () =>
      window.removeEventListener("anx:plan-upgrade-required", onGate);
  }, []);

  if (!gate || dismissed) return null;

  const goToBilling = () => {
    if (onNavigate) {
      onNavigate("billing");
      setDismissed(true);
      return;
    }
    window.location.href = gate.upgradePath;
  };

  return (
    <div
      role="status"
      style={{
        position: "fixed",
        right: 24,
        bottom: 24,
        zIndex: 1000,
        maxWidth: 360,
        background: "var(--bg-secondary, #1e293b)",
        border: "1px solid var(--border, #334155)",
        borderRadius: 12,
        padding: "16px 18px",
        boxShadow: "0 8px 30px rgba(0,0,0,0.35)",
      }}
    >
      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: "var(--accent, #6366f1)",
          letterSpacing: 1.1,
          marginBottom: 6,
        }}
      >
        AGENT OS PLAN
      </div>
      <div
        style={{
          fontSize: "0.9rem",
          color: "var(--text-primary, #f1f5f9)",
          marginBottom: 12,
        }}
      >
        {gate.message}
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={goToBilling}
          style={{
            border: "none",
            borderRadius: 8,
            padding: "8px 16px",
            cursor: "pointer",
            fontSize: "0.85rem",
            fontWeight: 600,
            color: "#fff",
            background: "var(--accent, #6366f1)",
          }}
        >
          See plans
        </button>
        <button
          onClick={() => setDismissed(true)}
          style={{
            borderRadius: 8,
            padding: "8px 16px",
            cursor: "pointer",
            fontSize: "0.85rem",
            color: "var(--text-secondary, #94a3b8)",
            background: "transparent",
            border: "1px solid var(--border, #334155)",
          }}
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
