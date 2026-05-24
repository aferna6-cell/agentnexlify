import { TRIGGER_TYPES, ENROLLMENT_STATUS_STYLES } from "./constants";

export function TriggerBadge({ type }) {
  const t = TRIGGER_TYPES.find((x) => x.key === type);
  const label = t?.label || type;
  const colorMap = {
    lead_captured: { color: "var(--green)", bg: "var(--green-dim)" },
    tag_added: { color: "var(--accent)", bg: "var(--accent-dim)" },
    manual: { color: "var(--text-secondary)", bg: "var(--hover-overlay)" },
  };
  const colors = colorMap[type] || colorMap.manual;
  return (
    <span
      style={{
        padding: "2px 10px",
        borderRadius: 12,
        fontSize: "0.75rem",
        fontWeight: 600,
        color: colors.color,
        background: colors.bg,
      }}
    >
      {label}
    </span>
  );
}

export function StatusBadge({ status, map = ENROLLMENT_STATUS_STYLES }) {
  const s = map[status] || map.active;
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

export function Toggle({ checked, onChange, label }) {
  return (
    <label
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        cursor: "pointer",
      }}
    >
      <div
        onClick={() => onChange(!checked)}
        style={{
          width: 38,
          height: 20,
          borderRadius: 10,
          position: "relative",
          cursor: "pointer",
          background: checked ? "var(--accent)" : "var(--border)",
          transition: "background 0.2s",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 3,
            left: checked ? 19 : 3,
            width: 14,
            height: 14,
            borderRadius: "50%",
            background: "#fff",
            transition: "left 0.2s",
          }}
        />
      </div>
      {label && (
        <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
          {label}
        </span>
      )}
    </label>
  );
}
