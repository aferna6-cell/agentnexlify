import { useState, useEffect } from "react";
import { fetchAIInsights } from "../../utils/api/dashboard";

export default function AIInsightsWidget({ tenantId, token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!tenantId || !token) return;
    let cancelled = false;

    fetchAIInsights(tenantId, token)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [tenantId, token]);

  if (loading) {
    return (
      <div className="crm-widget-card">
        <h3 style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "1.1rem" }}>AI Insights</span>
        </h3>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Analyzing your business data...</p>
      </div>
    );
  }

  if (error || !data) {
    return null; // Silently hide if insights unavailable
  }

  const m = data.metrics || {};
  const analysis = data.ai_analysis || "";

  // Parse bullet points from AI analysis
  const bullets = analysis
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("- ") || line.startsWith("* ") || line.match(/^\d+\./))
    .map((line) => line.replace(/^[-*]\s*/, "").replace(/^\d+\.\s*/, ""));

  return (
    <div className="crm-widget-card" style={{ borderLeft: "3px solid #8b5cf6" }}>
      <h3 style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
        <span style={{ fontSize: "1.1rem" }}>AI Business Insights</span>
        <span style={{
          fontSize: "0.65rem",
          background: "#8b5cf6",
          color: "white",
          padding: "2px 8px",
          borderRadius: "10px",
          fontWeight: 600,
        }}>
          WEEKLY
        </span>
      </h3>

      {/* Key metrics row */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: "8px",
        marginBottom: "16px",
      }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--text-primary)" }}>
            {m.new_leads ?? 0}
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Leads</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--text-primary)" }}>
            {m.appointments ?? 0}
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Appts</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "#059669" }}>
            ${(m.revenue ?? 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Revenue</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "1.3rem", fontWeight: 700, color: m.pending_actions > 0 ? "#f59e0b" : "var(--text-primary)" }}>
            {m.pending_actions ?? 0}
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Actions</div>
        </div>
      </div>

      {/* AI Analysis bullets */}
      {bullets.length > 0 ? (
        <ul style={{ margin: 0, paddingLeft: "18px", listStyle: "none" }}>
          {bullets.map((bullet, i) => (
            <li key={i} style={{
              fontSize: "0.85rem",
              color: "var(--text-secondary)",
              marginBottom: "8px",
              paddingLeft: "12px",
              position: "relative",
            }}>
              <span style={{
                position: "absolute",
                left: 0,
                color: "#8b5cf6",
                fontWeight: 700,
              }}>
                {i === bullets.length - 1 ? "\u2192" : "\u2022"}
              </span>
              {bullet}
            </li>
          ))}
        </ul>
      ) : analysis ? (
        <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
          {analysis}
        </p>
      ) : (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          Not enough data yet - insights will appear after your first full week.
        </p>
      )}
    </div>
  );
}
