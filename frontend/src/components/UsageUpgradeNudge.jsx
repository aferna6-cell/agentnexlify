import { useState } from "react";

/**
 * UsageUpgradeNudge - honest, dismissible in-app upgrade prompt.
 *
 * Shows when a tenant is near (>=80%) or at their monthly agent-run cap and a
 * higher plan exists. States the real usage vs limit (no invented numbers; the
 * caller passes the live /api/v1/os/usage payload) and the concrete benefit of
 * upgrading - a larger agent-run allowance. CTA routes to the billing page.
 *
 * Design constraints (frontend-patterns.md): flat dark theme, no gradients, no
 * emoji in chrome, no fake urgency. Dismiss is in-memory only (no localStorage,
 * which is unavailable in the artifact sandbox) so it never blocks the app and
 * reappears on next mount/refresh.
 */

const NEAR_THRESHOLD = 80;

// Allowance of the next tier up, used only to state a concrete, true benefit.
// Keys are live plan names from usage_meter.PLAN_AGENT_RUN_CAPS.
const NEXT_TIER = {
  free: { plan: "agent_os", label: "Agent OS", runs: 2000 },
  chatbot: { plan: "agent_os", label: "Agent OS", runs: 2000 },
};

export default function UsageUpgradeNudge({ usage, onNavigate }) {
  const [dismissed, setDismissed] = useState(false);

  if (!usage) return null;

  const plan = (usage.plan || "free").toLowerCase();
  const next = NEXT_TIER[plan];
  // Already on the top tier (or an unknown plan with no defined upgrade): the
  // honest move is to show nothing rather than prompt an upgrade that does not
  // exist.
  if (!next) return null;

  const capReached = Boolean(usage.cap_reached);
  const percent =
    typeof usage.percent === "number"
      ? usage.percent
      : usage.cap > 0
        ? Math.min(100, Math.round((usage.agent_runs * 100) / usage.cap))
        : 0;

  const near = capReached || percent >= NEAR_THRESHOLD;
  if (!near || dismissed) return null;

  const used = usage.agent_runs ?? 0;
  const cap = usage.cap ?? 0;

  const headline = capReached
    ? "You have used all your agent runs this month"
    : "You are close to your monthly agent-run limit";

  const detail = capReached
    ? `You have used ${used} of ${cap} agent runs this billing cycle. New tasks resume next cycle, or upgrade to ${next.label} for ${next.runs.toLocaleString()} runs a month.`
    : `You have used ${used} of ${cap} agent runs (${percent}%) this billing cycle. Upgrade to ${next.label} for ${next.runs.toLocaleString()} runs a month.`;

  return (
    <div
      data-testid="usage-upgrade-nudge"
      role="status"
      style={{
        padding: "12px 16px",
        background: "var(--bg-secondary, #16161d)",
        border: "1px solid rgba(245,158,11,0.35)",
        borderRadius: 8,
        margin: "12px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "1rem",
        flexWrap: "wrap",
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div
          style={{
            fontSize: "0.85rem",
            fontWeight: 600,
            color: "var(--text-primary, #e8e8ea)",
            marginBottom: 2,
          }}
        >
          {headline}
        </div>
        <div
          style={{
            fontSize: "0.8rem",
            color: "var(--text-muted, #9a9aa5)",
          }}
        >
          {detail}
        </div>
      </div>
      <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
        <button
          type="button"
          onClick={() => onNavigate && onNavigate("billing")}
          style={{
            background: "#f59e0b",
            color: "#0a0a0f",
            border: "none",
            padding: "7px 16px",
            borderRadius: 6,
            cursor: "pointer",
            fontWeight: 600,
            fontSize: "0.8rem",
            whiteSpace: "nowrap",
          }}
        >
          View plans
        </button>
        <button
          type="button"
          aria-label="Dismiss"
          onClick={() => setDismissed(true)}
          style={{
            background: "transparent",
            color: "var(--text-muted, #9a9aa5)",
            border: "1px solid var(--border, rgba(255,255,255,0.12))",
            padding: "7px 12px",
            borderRadius: 6,
            cursor: "pointer",
            fontSize: "0.8rem",
            whiteSpace: "nowrap",
          }}
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
