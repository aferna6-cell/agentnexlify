import { useState, useEffect } from "react";
import { fetchFrontDeskHealth } from "../../utils/api/analytics";

const SENTIMENT_META = {
  positive: { label: "Positive", color: "#22c55e" },
  neutral: { label: "Neutral", color: "#94a3b8" },
  negative: { label: "Negative", color: "#ef4444" },
};

function StatBlock({ value, label, color }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div
        style={{
          fontSize: "1.4rem",
          fontWeight: 700,
          color: color || "var(--text-primary)",
        }}
      >
        {value}
      </div>
      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
        {label}
      </div>
    </div>
  );
}

export default function FrontDeskHealthCard({ tenantId, token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!tenantId || !token) return;
    let cancelled = false;

    fetchFrontDeskHealth(tenantId, token)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [tenantId, token]);

  if (loading) {
    return (
      <div className="crm-widget-card">
        <h3>Front Desk Health</h3>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          Loading conversation data...
        </p>
      </div>
    );
  }

  // Hide on hard error so a failed call never breaks the dashboard grid.
  if (error || !data) return null;

  const total = data.total_conversations ?? 0;
  const captureRate = data.capture_rate ?? 0;
  const leadsCaptured = data.leads_captured ?? 0;
  const kbGaps = data.kb_gap_count ?? 0;
  const sentiment = data.sentiment_breakdown || {};
  const topIntents = data.top_intents || [];
  const classified = data.classification_available;

  if (total === 0) {
    return (
      <div className="crm-widget-card">
        <h3>Front Desk Health</h3>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          No conversations yet. Share your widget link and your front desk
          performance will appear here within minutes of the first chat.
        </p>
      </div>
    );
  }

  const sentimentTotal =
    (sentiment.positive || 0) +
    (sentiment.neutral || 0) +
    (sentiment.negative || 0);

  return (
    <div className="crm-widget-card">
      <h3 style={{ marginBottom: "12px" }}>Front Desk Health</h3>

      {/* Headline stats */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "8px",
          marginBottom: "16px",
        }}
      >
        <StatBlock value={total} label="Conversations" />
        <StatBlock
          value={`${captureRate}%`}
          label="Capture Rate"
          color="#22c55e"
        />
        <StatBlock
          value={kbGaps}
          label="KB Gaps"
          color={kbGaps > 0 ? "#f59e0b" : "var(--text-primary)"}
        />
      </div>

      <div
        style={{
          fontSize: "0.72rem",
          color: "var(--text-muted)",
          marginBottom: "16px",
        }}
      >
        {leadsCaptured} of {total} conversations captured a lead
      </div>

      {/* Sentiment breakdown */}
      <div style={{ marginBottom: "16px" }}>
        <div
          style={{
            fontSize: "0.72rem",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            color: "var(--text-muted)",
            marginBottom: "8px",
          }}
        >
          Sentiment
        </div>
        {classified && sentimentTotal > 0 ? (
          <>
            <div
              style={{
                display: "flex",
                height: "8px",
                borderRadius: "4px",
                overflow: "hidden",
                marginBottom: "8px",
              }}
            >
              {["positive", "neutral", "negative"].map((key) => {
                const count = sentiment[key] || 0;
                if (count === 0) return null;
                return (
                  <div
                    key={key}
                    style={{
                      width: `${(count / sentimentTotal) * 100}%`,
                      background: SENTIMENT_META[key].color,
                    }}
                  />
                );
              })}
            </div>
            <div style={{ display: "flex", gap: "14px", flexWrap: "wrap" }}>
              {["positive", "neutral", "negative"].map((key) => (
                <span
                  key={key}
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-secondary)",
                    display: "flex",
                    alignItems: "center",
                    gap: "5px",
                  }}
                >
                  <span
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "2px",
                      background: SENTIMENT_META[key].color,
                      display: "inline-block",
                    }}
                  />
                  {SENTIMENT_META[key].label} {sentiment[key] || 0}
                </span>
              ))}
            </div>
          </>
        ) : (
          <p style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            Sentiment analysis runs after conversations close. Check back
            shortly.
          </p>
        )}
      </div>

      {/* Top topics / intents */}
      <div>
        <div
          style={{
            fontSize: "0.72rem",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            color: "var(--text-muted)",
            marginBottom: "8px",
          }}
        >
          Top Topics
        </div>
        {topIntents.length > 0 ? (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
            {topIntents.map((item) => (
              <span
                key={item.intent}
                style={{
                  fontSize: "0.75rem",
                  padding: "4px 10px",
                  borderRadius: "12px",
                  background: "var(--bg-tertiary, rgba(148,163,184,0.12))",
                  color: "var(--text-secondary)",
                  border: "1px solid rgba(148,163,184,0.18)",
                }}
              >
                {item.intent} ({item.count})
              </span>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            Topics will appear once conversations are classified.
          </p>
        )}
      </div>
    </div>
  );
}
