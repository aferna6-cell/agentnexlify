import { STATUS_COLORS } from "./invoiceUtils";

export default function StatusBadge({ status }) {
  const style = STATUS_COLORS[status] || STATUS_COLORS.draft;
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: "0.7rem",
        fontWeight: 600,
        color: style.color,
        background: style.bg,
        textTransform: "capitalize",
      }}
    >
      {status}
    </span>
  );
}
