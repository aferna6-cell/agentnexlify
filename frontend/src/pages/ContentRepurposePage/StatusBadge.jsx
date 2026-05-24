export default function StatusBadge({ status }) {
  const styles = {
    processing: { color: "var(--accent)", bg: "var(--accent-dim)" },
    completed: { color: "var(--green)", bg: "var(--green-dim)" },
    failed: { color: "#ef4444", bg: "rgba(239,68,68,0.15)" },
  };
  const s = styles[status] || styles.processing;
  return (
    <span
      style={{
        padding: "2px 10px",
        borderRadius: 12,
        fontSize: "0.75rem",
        fontWeight: 600,
        color: s.color,
        background: s.bg,
      }}
    >
      {status}
    </span>
  );
}
