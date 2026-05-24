import { STATUS_COLORS } from "./constants";

export default function StatusBadge({ status }) {
  const sc = STATUS_COLORS[status] || STATUS_COLORS.draft;
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: "0.7rem",
        fontWeight: 600,
        color: sc.color,
        background: sc.bg,
        textTransform: "capitalize",
      }}
    >
      {status}
    </span>
  );
}
