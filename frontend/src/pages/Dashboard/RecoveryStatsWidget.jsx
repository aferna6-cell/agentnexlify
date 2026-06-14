import { useState, useEffect } from "react";
import { fetchRecoveryStats } from "../../utils/api/analytics";

export default function RecoveryStatsWidget({ tenantId, token }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tenantId || !token) return;
    fetchRecoveryStats(tenantId, token, 30)
      .then(setStats)
      .catch((err) => { console.warn("Recovery stats fetch failed:", err?.message); setStats(null); })
      .finally(() => setLoading(false));
  }, [tenantId, token]);

  if (loading || !stats) return null;

  const hasActivity =
    stats.noshow_recovered > 0 ||
    stats.reviews_requested > 0 ||
    stats.briefings_sent > 0;

  if (!hasActivity) return null;

  const cards = [];

  if (stats.noshow_recovered > 0) {
    cards.push({
      label: "No-Shows Recovered",
      value: stats.noshow_recovered,
      detail: `${stats.noshow_total} total no-shows`,
      color: "#f59e0b",
      icon: "\u{1F504}",
    });
  }

  if (stats.reviews_requested > 0) {
    cards.push({
      label: "Review Requests Sent",
      value: stats.reviews_requested,
      detail: "Last 30 days",
      color: "#22c55e",
      icon: "\u2B50",
    });
  }

  if (stats.briefings_sent > 0) {
    cards.push({
      label: "Daily Briefings",
      value: stats.briefings_sent,
      detail: "Morning SMS summaries",
      color: "#3b82f6",
      icon: "\u{1F4CB}",
    });
  }

  return (
    <div style={{ marginBottom: "18px" }}>
      <h3
        style={{
          fontSize: "0.85rem",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          color: "var(--text-muted)",
          marginBottom: "10px",
        }}
      >
        Automation ROI - Last 30 Days
      </h3>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${cards.length}, 1fr)`,
          gap: "12px",
        }}
      >
        {cards.map((c) => (
          <div
            key={c.label}
            style={{
              padding: "16px 18px",
              borderRadius: "12px",
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "8px",
              }}
            >
              <span style={{ fontSize: "1.2rem" }}>{c.icon}</span>
              <span
                style={{
                  fontSize: "0.78rem",
                  color: "var(--text-muted)",
                  fontWeight: 600,
                }}
              >
                {c.label}
              </span>
            </div>
            <div
              style={{
                fontSize: "1.6rem",
                fontWeight: 700,
                color: c.color,
                lineHeight: 1,
              }}
            >
              {c.value}
            </div>
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                marginTop: "4px",
              }}
            >
              {c.detail}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
