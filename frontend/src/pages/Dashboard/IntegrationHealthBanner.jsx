import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { fetchIntegrationsHealth } from "../../utils/api/integrationKeys";

/**
 * actionableIntegrationAlerts(health) - pure filter, exported for testing.
 *
 * Returns only the providers an owner needs to act on: ones that are failing
 * (red) or degraded (yellow) AND were actually set up. A provider that simply
 * says "not configured" is NOT an alert - a chatbot-tier owner who never
 * connected Stripe should not see a scary banner. The point of this banner is
 * the council finding: a connection that WAS working and lapsed must surface
 * to the owner, not get swallowed.
 */
export function actionableIntegrationAlerts(health) {
  if (!health || !Array.isArray(health.providers)) return [];
  return health.providers.filter((p) => {
    if (!p || (p.health !== "red" && p.health !== "yellow")) return false;
    const detail = (p.detail || "").toLowerCase();
    return detail !== "not configured";
  });
}

const PROVIDER_LABELS = {
  stripe: "Stripe payments",
  twilio: "Twilio texting & calls",
  resend: "Email sending",
  google_calendar: "Google Calendar",
};

function providerLabel(provider) {
  return PROVIDER_LABELS[provider] || provider;
}

export default function IntegrationHealthBanner({ onNavigate }) {
  const { user, token } = useAuth();
  const [alerts, setAlerts] = useState([]);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!user?.tenantId || !token) return undefined;
    fetchIntegrationsHealth(token)
      .then((health) => {
        if (!cancelled) setAlerts(actionableIntegrationAlerts(health));
      })
      .catch(() => {
        // Health endpoint is best-effort. A failed check should not block the
        // dashboard or itself become a fake alert.
        if (!cancelled) setAlerts([]);
      });
    return () => {
      cancelled = true;
    };
  }, [user?.tenantId, token]);

  if (dismissed || alerts.length === 0) return null;

  const hasRed = alerts.some((a) => a.health === "red");
  const accent = hasRed ? "#ef4444" : "#f59e0b";
  const tint = hasRed ? "rgba(239,68,68,0.08)" : "rgba(245,158,11,0.08)";

  const names = alerts.map((a) => providerLabel(a.provider)).join(", ");
  const headline = hasRed
    ? `Action needed: ${names} stopped working`
    : `Heads up: ${names} needs attention`;
  const subline = hasRed
    ? "A connection that was set up is now failing. Bookings, texts, or payments tied to it will not go through until it is reconnected."
    : "A connection is degraded. Reconnect it before it stops working.";

  return (
    <div
      role="alert"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
        padding: "12px 16px",
        marginBottom: 16,
        borderRadius: 8,
        border: `1px solid ${accent}`,
        borderLeft: `4px solid ${accent}`,
        background: tint,
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>
          {headline}
        </div>
        <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: 2 }}>
          {subline}
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
        <button
          className="upgrade-btn"
          onClick={() => onNavigate?.("integrations")}
        >
          Fix it
        </button>
        <button
          aria-label="Dismiss"
          onClick={() => setDismissed(true)}
          style={{
            background: "transparent",
            border: "none",
            color: "var(--text-muted)",
            cursor: "pointer",
            fontSize: "1.1rem",
            lineHeight: 1,
          }}
        >
          {"×"}
        </button>
      </div>
    </div>
  );
}
