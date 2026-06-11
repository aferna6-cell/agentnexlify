/* Weekly value recap + proactive suggestions strip (gaps G2 + G7).
 *
 * Shows the owner what their AI staff was worth this week — leads,
 * appointments, invoice dollars — plus anything the staff noticed
 * (cold leads, overdue invoices). Suggestions click into the composer.
 * Fails silent: a fetch error renders nothing rather than noise.
 */
import { useEffect, useState } from "react";
import { BASE } from "../../utils/api/_client";

export default function OsInsightsCard({ token, onSuggestion }) {
  const [data, setData] = useState(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetch(`${BASE}/api/v1/os/insights`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!cancelled && d) setData(d);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (dismissed || !data) return null;
  const w = data.week || {};
  const hasActivity =
    (w.leads_captured || 0) +
      (w.appointments_booked || 0) +
      (w.invoices_sent || 0) +
      (w.agent_runs_completed || 0) >
    0;
  const suggestions = data.suggestions || [];
  if (!hasActivity && suggestions.length === 0) return null;

  const stat = (label, value) => (
    <div style={{ minWidth: 92 }}>
      <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-primary)" }}>{value}</div>
      <div style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>{label}</div>
    </div>
  );

  return (
    <div
      style={{
        margin: "0 0 16px",
        padding: "12px 14px",
        background: "var(--bg-card, rgba(255,255,255,0.03))",
        border: "1px solid var(--border, rgba(255,255,255,0.08))",
        borderRadius: 10,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: hasActivity ? 10 : 0 }}>
        <span style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-secondary)" }}>
          Your AI staff this week
        </span>
        <button
          onClick={() => setDismissed(true)}
          aria-label="Dismiss weekly recap"
          style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "0.9rem", padding: 0 }}
        >
          ×
        </button>
      </div>
      {hasActivity && (
        <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
          {stat("leads captured", w.leads_captured || 0)}
          {stat("appointments", w.appointments_booked || 0)}
          {stat("invoiced", `$${Math.round(w.invoices_sent_total || 0).toLocaleString()}`)}
          {stat("collected", `$${Math.round(w.invoices_paid_total || 0).toLocaleString()}`)}
          {stat("tasks done", w.agent_runs_completed || 0)}
        </div>
      )}
      {suggestions.length > 0 && (
        <div style={{ marginTop: hasActivity ? 10 : 0, display: "flex", flexDirection: "column", gap: 6 }}>
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => onSuggestion?.(s.summary)}
              title={s.detail}
              style={{
                textAlign: "left",
                background: "rgba(99,102,241,0.08)",
                border: "1px solid rgba(99,102,241,0.25)",
                borderRadius: 8,
                padding: "8px 10px",
                color: "var(--text-secondary)",
                fontSize: "0.78rem",
                cursor: "pointer",
              }}
            >
              {s.summary}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
