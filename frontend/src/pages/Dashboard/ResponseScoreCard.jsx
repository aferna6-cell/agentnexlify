import { useState, useEffect } from "react";
import { fetchResponseScore } from "../../utils/api/insights";

const COMPONENT_LABELS = {
  responsiveness: "Speed to lead",
  momentum: "Warm leads active",
  conversion: "Leads → bookings",
  reliability: "Show-up rate",
};

function scoreColor(score) {
  if (score >= 75) return "#22c55e";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
}

export default function ResponseScoreCard({ tenantId, token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tenantId || !token) return;
    let cancelled = false;

    fetchResponseScore(tenantId, token)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        console.warn("Response score fetch failed:", err?.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [tenantId, token]);

  if (loading || !data) return null; // silently hide until loaded

  return (
    <div className="crm-widget-card">
      <h3>Nexlify Score</h3>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 4 }}>
        <span style={{ fontSize: "2rem", fontWeight: 700, color: scoreColor(data.score) }}>
          {Math.round(data.score)}
        </span>
        <span style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>
          / 100 · grade {data.grade}
        </span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 10 }}>
        {Object.entries(data.components).map(([key, value]) => (
          <div key={key}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: 2 }}>
              <span>{COMPONENT_LABELS[key] || key}</span>
              <span>{Math.round(value)}</span>
            </div>
            <div style={{ height: 5, borderRadius: 3, background: "var(--bg-primary)", overflow: "hidden" }}>
              <div
                style={{
                  width: `${Math.min(100, value)}%`,
                  height: "100%",
                  background: scoreColor(value),
                }}
              />
            </div>
          </div>
        ))}
      </div>
      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 8 }}>
        Every fast reply and kept appointment grows your score.
      </div>
    </div>
  );
}
