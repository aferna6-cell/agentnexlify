import { TIMELINE_ICONS } from "./constants";

export function scoreClass(score) {
  if (score >= 80) return "score-hot";
  if (score >= 60) return "score-warm";
  if (score >= 40) return "score-cool";
  return "score-cold";
}

export function scoreLabel(score) {
  if (score >= 80) return "Hot";
  if (score >= 60) return "Warm";
  if (score >= 40) return "Cool";
  return "Cold";
}

export function scoreColor(score) {
  if (score >= 80) return "var(--red)";
  if (score >= 60) return "var(--yellow)";
  if (score >= 40) return "var(--accent)";
  return "var(--text-muted)";
}

export function temperatureBadge(temp) {
  if (!temp) return null;
  const t = temp.toLowerCase();
  const config = {
    hot: {
      color: "#ff4444",
      bg: "rgba(255, 68, 68, 0.15)",
      border: "rgba(255, 68, 68, 0.3)",
    },
    warm: {
      color: "#f5a623",
      bg: "rgba(245, 166, 35, 0.15)",
      border: "rgba(245, 166, 35, 0.3)",
    },
    cold: {
      color: "#00bfff",
      bg: "rgba(0, 191, 255, 0.15)",
      border: "rgba(0, 191, 255, 0.3)",
    },
  };
  const c = config[t] || config.cold;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "3px 10px",
        borderRadius: 12,
        fontSize: "0.75rem",
        fontWeight: 600,
        background: c.bg,
        color: c.color,
        border: `1px solid ${c.border}`,
      }}
    >
      {t === "hot" ? (
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 2v10m0 0l-3-3m3 3l3-3M5 21a7 7 0 0114 0" />
          <circle cx="12" cy="17" r="4" fill="currentColor" opacity="0.3" />
        </svg>
      ) : t === "warm" ? (
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
      ) : (
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        >
          <path d="M20 17.58A11 11 0 0 0 18 4.41C9.71 4.41 3 11.12 3 19.41h9.71" />
          <path d="M12.71 12.71L17 8.41" />
        </svg>
      )}
      {temp.charAt(0).toUpperCase() + temp.slice(1).toLowerCase()}
    </span>
  );
}

export function timelineIcon(type) {
  const cfg = TIMELINE_ICONS[type] || {
    icon: "•",
    color: "var(--text-muted)",
  };
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 24,
        height: 24,
        borderRadius: "50%",
        background: `${cfg.color}22`,
        color: cfg.color,
        fontSize: 12,
        fontWeight: 700,
        flexShrink: 0,
      }}
    >
      {cfg.icon}
    </span>
  );
}

export function formatTimelineDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now - d;
  const diffH = diffMs / (1000 * 60 * 60);
  if (diffH < 1) return `${Math.max(1, Math.floor(diffMs / 60000))}m ago`;
  if (diffH < 24) return `${Math.floor(diffH)}h ago`;
  if (diffH < 48) return "Yesterday";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
