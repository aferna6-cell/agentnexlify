import { STATUS_BADGE_COLORS } from "./utils";

export default function StatusBadge({ status }) {
  const sc = STATUS_BADGE_COLORS[status] || STATUS_BADGE_COLORS.new;
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
      {(status || "").replace(/_/g, " ")}
    </span>
  );
}
