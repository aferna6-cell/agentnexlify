import { STATUS_STYLES } from "./utils";

export default function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.draft;
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
      {s.label}
    </span>
  );
}
