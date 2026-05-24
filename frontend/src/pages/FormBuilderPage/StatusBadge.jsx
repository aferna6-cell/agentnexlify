export default function StatusBadge({ active }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: "0.7rem",
        fontWeight: 600,
        color: active ? "#22c55e" : "var(--text-muted)",
        background: active ? "rgba(34,197,94,0.1)" : "var(--hover-overlay)",
      }}
    >
      {active ? "Active" : "Inactive"}
    </span>
  );
}
