const VERTICALS = [
  { key: "plumbing", label: "Plumbing", icon: "🔧" },
  { key: "hvac", label: "HVAC", icon: "❄️" },
  { key: "cleaning", label: "Cleaning", icon: "🧹" },
  { key: "power_washing", label: "Power Washing", icon: "💧" },
  { key: "landscaping", label: "Landscaping", icon: "🌿" },
  { key: "electrical", label: "Electrical", icon: "⚡" },
];

export default function VerticalPresetPicker({ value, onChange }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(2, 1fr)",
        gap: 12,
      }}
    >
      {VERTICALS.map((v) => {
        const selected = value === v.key;
        return (
          <button
            key={v.key}
            type="button"
            onClick={() => onChange(v.key)}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              padding: "16px 12px",
              minHeight: 80,
              background: selected
                ? "rgba(99, 102, 241, 0.2)"
                : "rgba(255,255,255,0.04)",
              border: selected
                ? "2px solid #6366f1"
                : "2px solid rgba(255,255,255,0.1)",
              borderRadius: 10,
              color: selected ? "#a5b4fc" : "rgba(255,255,255,0.7)",
              cursor: "pointer",
              fontSize: "0.85rem",
              fontWeight: selected ? 600 : 400,
              transition: "all 0.15s ease",
              textAlign: "center",
            }}
          >
            <span style={{ fontSize: "1.5rem", lineHeight: 1 }}>{v.icon}</span>
            <span>{v.label}</span>
          </button>
        );
      })}
    </div>
  );
}
