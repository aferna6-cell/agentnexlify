const CRITERIA_CONFIG = [
  {
    key: "services_count",
    label: "Services added",
    check: (v) => v >= 3,
  },
  {
    key: "hours_filled",
    label: "Hours configured",
    check: (v) => !!v,
  },
  {
    key: "faqs_count",
    label: "FAQs added",
    check: (v) => v >= 5,
  },
  {
    key: "logo_uploaded",
    label: "Logo uploaded",
    check: (v) => !!v,
  },
];

export default function ReadyToLaunchBadge({ criteria = {} }) {
  const results = CRITERIA_CONFIG.map((c) => ({
    ...c,
    met: c.check(criteria[c.key]),
  }));
  const metCount = results.filter((r) => r.met).length;
  const allMet = metCount === results.length;

  return (
    <div
      style={{
        border: allMet
          ? "1px solid rgba(34, 197, 94, 0.4)"
          : "1px solid rgba(255,255,255,0.1)",
        borderRadius: 12,
        padding: "16px 20px",
        background: allMet
          ? "rgba(34, 197, 94, 0.08)"
          : "rgba(255,255,255,0.03)",
        transition: "all 0.2s ease",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
        }}
      >
        <span
          style={{
            fontWeight: 600,
            fontSize: "0.9rem",
            color: allMet ? "#4ade80" : "rgba(255,255,255,0.7)",
          }}
        >
          {allMet
            ? "Ready to launch!"
            : `${metCount} of ${results.length} complete`}
        </span>
        {allMet && (
          <span
            style={{
              background: "rgba(34, 197, 94, 0.2)",
              color: "#4ade80",
              fontSize: "0.75rem",
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: 99,
            }}
          >
            READY
          </span>
        )}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {results.map((r) => (
          <div
            key={r.key}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              fontSize: "0.85rem",
              color: r.met ? "#4ade80" : "rgba(255,255,255,0.4)",
            }}
          >
            <span
              style={{
                width: 18,
                height: 18,
                borderRadius: "50%",
                border: r.met ? "none" : "1.5px solid rgba(255,255,255,0.2)",
                background: r.met ? "#4ade80" : "transparent",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              {r.met && (
                <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
                  <polyline
                    points="2,6 5,9 10,3"
                    stroke="#0a0a0f"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
            </span>
            {r.label}
          </div>
        ))}
      </div>
    </div>
  );
}
