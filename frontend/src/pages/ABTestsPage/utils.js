import { BASE } from "../../utils/api/_client";

export const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

export const inputStyle = {
  width: "100%",
  padding: "10px 14px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--bg-primary)",
  color: "var(--text-primary)",
  fontSize: "0.9rem",
  boxSizing: "border-box",
};

export const btnPrimary = {
  background: "var(--accent)",
  color: "#fff",
  border: "none",
  padding: "10px 20px",
  borderRadius: 8,
  fontWeight: 600,
  cursor: "pointer",
  fontSize: "0.9rem",
};

export const btnSecondary = {
  background: "var(--bg-primary)",
  color: "var(--text-secondary)",
  border: "1px solid var(--border)",
  padding: "8px 16px",
  borderRadius: 8,
  cursor: "pointer",
  fontSize: "0.85rem",
};

export const labelStyle = {
  display: "block",
  fontSize: "0.85rem",
  color: "var(--text-secondary)",
  marginBottom: 6,
};

export const overlayStyle = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
};

export const modalStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  borderRadius: 16,
  padding: "28px 32px",
  width: "90%",
  maxWidth: 900,
  maxHeight: "90vh",
  overflowY: "auto",
  border: "1px solid var(--border)",
};

export const TEST_TYPES = [
  {
    key: "subject_line",
    label: "Subject Line",
    desc: "Test different email subject lines",
  },
  {
    key: "send_time",
    label: "Send Time",
    desc: "Test different send times for same content",
  },
  {
    key: "body_content",
    label: "Body Content",
    desc: "Test different email body copy",
  },
  {
    key: "campaign_variant",
    label: "Campaign Variant",
    desc: "Fully different campaigns",
  },
];

export const STATUS_STYLES = {
  draft: {
    label: "Draft",
    color: "var(--text-secondary)",
    bg: "var(--hover-overlay)",
  },
  running: {
    label: "Running",
    color: "var(--accent)",
    bg: "var(--accent-dim)",
  },
  completed: {
    label: "Completed",
    color: "var(--green)",
    bg: "var(--green-dim)",
  },
  paused: {
    label: "Paused",
    color: "var(--yellow, #f59e0b)",
    bg: "rgba(245,158,11,0.15)",
  },
};

const API_BASE = `${BASE}/api/v1`;

export async function apiFetch(path, token, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...opts.headers,
    },
    ...opts,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

export function formatDate(d) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
