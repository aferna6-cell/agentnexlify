export default function QualityStatBar({ completionPct, aiEnrichedCount }) {
  if (completionPct === null) return null;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        marginBottom: 12,
        padding: "8px 14px",
        borderRadius: 8,
        background: "var(--bg-secondary)",
        border: "1px solid var(--border)",
        fontSize: 13,
        color: "var(--text-secondary)",
      }}
    >
      <span>
        <span
          style={{
            fontWeight: 700,
            color:
              completionPct >= 95
                ? "#22c55e"
                : completionPct >= 70
                  ? "#f5a623"
                  : "#ef4444",
          }}
        >
          {completionPct}%
        </span>{" "}
        leads have name + email + phone
      </span>
      {aiEnrichedCount > 0 && (
        <span style={{ color: "var(--accent, #00BFFF)" }}>
          · {aiEnrichedCount} AI-enriched
        </span>
      )}
    </div>
  );
}
