import { cardStyle, btnPrimary } from "./styles";

export function StatCard({ label, value, color }) {
  return (
    <div style={{ ...cardStyle, flex: 1, minWidth: 140 }}>
      <div
        style={{
          fontSize: "0.8rem",
          color: "var(--text-secondary)",
          marginBottom: 6,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "1.8rem",
          fontWeight: 700,
          color: color || "var(--text-primary)",
        }}
      >
        {value ?? "—"}
      </div>
    </div>
  );
}

export function EmptyState({ onCreateFirst }) {
  return (
    <div
      style={{
        ...cardStyle,
        textAlign: "center",
        padding: "56px 32px",
        color: "var(--text-secondary)",
      }}
    >
      <div style={{ fontSize: "2.5rem", marginBottom: 16 }}>
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ opacity: 0.4, margin: "0 auto" }}
        >
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <path d="M22 6l-10 7L2 6" />
          <path d="M8 14h3M8 18h8" />
        </svg>
      </div>
      <div
        style={{
          fontSize: "1.15rem",
          fontWeight: 600,
          color: "var(--text-primary)",
          marginBottom: 8,
        }}
      >
        No email sequences yet
      </div>
      <p
        style={{
          maxWidth: 380,
          margin: "0 auto 24px",
          lineHeight: 1.6,
          fontSize: "0.9rem",
        }}
      >
        Email sequences automatically send a series of emails when a trigger
        event fires (e.g., a new lead is captured). Create your first sequence
        to start nurturing leads on autopilot.
      </p>
      <button style={btnPrimary} onClick={onCreateFirst}>
        Create First Sequence
      </button>
    </div>
  );
}

export function LoadingRows({ count = 4 }) {
  return Array.from({ length: count }).map((_, i) => (
    <tr key={i}>
      {Array.from({ length: 6 }).map((__, j) => (
        <td key={j} style={{ padding: "14px 16px" }}>
          <div
            style={{
              height: 14,
              borderRadius: 6,
              background: "var(--hover-overlay)",
              width: j === 0 ? "60%" : j === 5 ? "70%" : "40%",
              animation: "pulse 1.5s ease-in-out infinite",
            }}
          />
        </td>
      ))}
    </tr>
  ));
}
