import { QUALIFICATION_LABELS } from "./constants";

export default function QualificationSection({ lead }) {
  const q = lead?.qualification_json;
  if (!q || typeof q !== "object") return null;

  const rec = q.recommendation || lead.qualification_recommendation;
  const config = QUALIFICATION_LABELS[rec] || {
    label: rec || "Unknown",
    color: "#888",
    bg: "rgba(136,136,136,0.15)",
    border: "rgba(136,136,136,0.3)",
  };
  const qualifiedAt = lead.qualified_at
    ? new Date(lead.qualified_at).toLocaleString()
    : null;

  return (
    <div className="intel-section">
      <div
        className="intel-title"
        style={{ display: "flex", alignItems: "center", gap: 8 }}
      >
        <span>AI Qualification</span>
        <span
          style={{
            display: "inline-block",
            padding: "2px 8px",
            borderRadius: 10,
            fontSize: "0.7rem",
            fontWeight: 600,
            background: config.bg,
            color: config.color,
            border: `1px solid ${config.border}`,
          }}
        >
          {config.label}
        </span>
      </div>
      <div
        style={{
          display: "flex",
          gap: 16,
          fontSize: "0.85rem",
          color: "var(--text-muted)",
          marginBottom: 8,
        }}
      >
        {q.intent_score != null && (
          <span>
            Intent:{" "}
            <strong style={{ color: "var(--text-primary)" }}>
              {q.intent_score}/10
            </strong>
          </span>
        )}
        {q.fit_score != null && (
          <span>
            Fit:{" "}
            <strong style={{ color: "var(--text-primary)" }}>
              {q.fit_score}/10
            </strong>
          </span>
        )}
        {qualifiedAt && <span>Ran: {qualifiedAt}</span>}
      </div>
      {q.reasoning && (
        <div
          style={{
            padding: "10px 12px",
            borderRadius: 8,
            background: "rgba(0,191,255,0.05)",
            border: "1px solid rgba(0,191,255,0.15)",
            fontSize: "0.85rem",
            lineHeight: 1.5,
            color: "var(--text-primary)",
            marginBottom: 8,
          }}
        >
          <div
            style={{
              fontSize: "0.7rem",
              fontWeight: 600,
              color: "var(--text-muted)",
              marginBottom: 4,
              textTransform: "uppercase",
            }}
          >
            Reasoning
          </div>
          {q.reasoning}
        </div>
      )}
      {q.suggested_first_reply && (
        <div
          style={{
            padding: "10px 12px",
            borderRadius: 8,
            background: "rgba(34,197,94,0.05)",
            border: "1px solid rgba(34,197,94,0.15)",
            fontSize: "0.85rem",
            lineHeight: 1.5,
            color: "var(--text-primary)",
          }}
        >
          <div
            style={{
              fontSize: "0.7rem",
              fontWeight: 600,
              color: "var(--text-muted)",
              marginBottom: 4,
              textTransform: "uppercase",
            }}
          >
            Suggested First Reply
          </div>
          {q.suggested_first_reply}
        </div>
      )}
    </div>
  );
}
