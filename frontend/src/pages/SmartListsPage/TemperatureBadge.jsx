import { TEMPERATURE_COLORS } from "./utils";

export default function TemperatureBadge({ temp }) {
  const tc = TEMPERATURE_COLORS[temp];
  if (!tc)
    return (
      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
        --
      </span>
    );
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: "0.7rem",
        fontWeight: 600,
        color: tc.color,
        background: tc.bg,
        textTransform: "capitalize",
      }}
    >
      {temp}
    </span>
  );
}
