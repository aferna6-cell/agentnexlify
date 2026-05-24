export default function TagsAndStatusSection({ lead }) {
  const hasTags = lead.tags && lead.tags.length > 0;
  const isUnsub = lead.unsubscribed;
  if (!hasTags && !isUnsub) return null;

  return (
    <>
      {hasTags && (
        <div className="intel-section">
          <div className="intel-title">Tags</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {lead.tags.map((tag, i) => (
              <span
                key={i}
                style={{
                  display: "inline-block",
                  padding: "4px 10px",
                  borderRadius: 14,
                  fontSize: "0.78rem",
                  background: "var(--accent-dim, rgba(0,191,255,0.15))",
                  color: "var(--accent, #00BFFF)",
                  border: "1px solid var(--accent-dim, rgba(0,191,255,0.25))",
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}
      {isUnsub && (
        <div className="intel-section">
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "6px 12px",
              borderRadius: 8,
              fontSize: "0.8rem",
              fontWeight: 600,
              background: "rgba(239,68,68,0.15)",
              color: "#ef4444",
              border: "1px solid rgba(239,68,68,0.3)",
            }}
          >
            Unsubscribed
            {lead.unsubscribed_at
              ? ` on ${new Date(lead.unsubscribed_at).toLocaleDateString()}`
              : ""}
          </div>
        </div>
      )}
    </>
  );
}
