export default function SuggestionsPanel({
  suggestions,
  onApprove,
  onDismiss,
}) {
  if (suggestions.length === 0) return null;
  return (
    <div
      style={{
        marginBottom: 16,
        padding: "12px 16px",
        borderRadius: 10,
        background: "rgba(139,92,246,0.1)",
        border: "1px solid rgba(139,92,246,0.3)",
      }}
    >
      <div
        style={{
          fontWeight: 600,
          fontSize: 13,
          color: "#8b5cf6",
          marginBottom: 8,
        }}
      >
        AI Suggestions ({suggestions.length})
      </div>
      {suggestions.slice(0, 5).map((s) => {
        const sData = s.metadata?.suggestions || {};
        return (
          <div
            key={s.id}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "6px 0",
              borderTop: "1px solid rgba(139,92,246,0.15)",
              fontSize: 12,
              gap: 8,
            }}
          >
            <div style={{ flex: 1, color: "var(--text-primary)" }}>
              {s.description}
              {Object.entries(sData).map(([field, vals]) => (
                <span
                  key={field}
                  style={{ marginLeft: 8, color: "var(--text-secondary)" }}
                >
                  {field}: <s style={{ opacity: 0.5 }}>{vals.old}</s> →{" "}
                  <strong>{vals.new}</strong>
                </span>
              ))}
            </div>
            <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
              <button
                onClick={() => onApprove(s.id)}
                style={{
                  background: "rgba(34,197,94,0.15)",
                  color: "#22c55e",
                  border: "none",
                  borderRadius: 4,
                  padding: "3px 8px",
                  cursor: "pointer",
                  fontSize: 11,
                }}
              >
                Approve
              </button>
              <button
                onClick={() => onDismiss(s.id)}
                style={{
                  background: "rgba(239,68,68,0.1)",
                  color: "#ef4444",
                  border: "none",
                  borderRadius: 4,
                  padding: "3px 8px",
                  cursor: "pointer",
                  fontSize: 11,
                }}
              >
                Dismiss
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
