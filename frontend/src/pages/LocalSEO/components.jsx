export function ScoreGauge({ score, label = "Score", size = 70 }) {
  const radius = size;
  const stroke = 10;
  const normalizedRadius = radius - stroke / 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const safeScore = Math.max(0, Math.min(100, score || 0));
  const offset = circumference - (safeScore / 100) * circumference;

  let strokeColor = "#ef4444";
  if (safeScore >= 70) strokeColor = "#22c55e";
  else if (safeScore >= 40) strokeColor = "#f59e0b";

  return (
    <div
      style={{ display: "flex", flexDirection: "column", alignItems: "center" }}
    >
      <svg
        height={radius * 2}
        width={radius * 2}
        style={{ transform: "rotate(-90deg)" }}
      >
        <circle
          stroke="var(--border)"
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        <circle
          stroke={strokeColor}
          fill="transparent"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={offset}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
      </svg>
      <div
        style={{
          position: "relative",
          marginTop: -radius - 20,
          fontSize: "2rem",
          fontWeight: 700,
          color: strokeColor,
          height: radius * 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {safeScore}
      </div>
      <div
        style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4 }}
      >
        {label}
      </div>
    </div>
  );
}

export function SectionHeader({ children }) {
  return (
    <div
      style={{
        fontSize: "0.75rem",
        color: "var(--text-muted)",
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "0.05em",
        marginBottom: 12,
      }}
    >
      {children}
    </div>
  );
}

export function Card({ children, style = {} }) {
  return (
    <div
      style={{
        background: "var(--bg-secondary)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        padding: 24,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export function PriorityBadge({ priority }) {
  const colors = {
    critical: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
    high: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
    medium: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
    low: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  };
  const c = colors[priority] || colors.medium;
  return (
    <span
      style={{
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: "0.7rem",
        fontWeight: 600,
        color: c.color,
        background: c.bg,
        textTransform: "capitalize",
      }}
    >
      {priority}
    </span>
  );
}

export function ErrorBanner({ error, onDismiss }) {
  if (!error) return null;
  return (
    <div
      style={{
        marginBottom: 16,
        padding: "10px 16px",
        background: "rgba(239,68,68,0.1)",
        border: "1px solid rgba(239,68,68,0.3)",
        borderRadius: 8,
        color: "#ef4444",
        fontSize: "0.85rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <span>{error}</span>
      <button
        onClick={onDismiss}
        style={{
          background: "none",
          border: "none",
          color: "#ef4444",
          cursor: "pointer",
          fontSize: "0.8rem",
          textDecoration: "underline",
        }}
      >
        dismiss
      </button>
    </div>
  );
}
