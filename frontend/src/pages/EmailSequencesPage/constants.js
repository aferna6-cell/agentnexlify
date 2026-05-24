export const TRIGGER_TYPES = [
  { key: "lead_captured", label: "Lead Captured" },
  { key: "tag_added", label: "Tag Added" },
  { key: "manual", label: "Manual" },
];

export const EMAIL_TYPES = [
  { key: "email", label: "Email" },
  { key: "sms", label: "SMS" },
];

export const STATUS_STYLES = {
  active: { label: "Active", color: "var(--green)", bg: "var(--green-dim)" },
  paused: {
    label: "Paused",
    color: "var(--yellow, #f59e0b)",
    bg: "rgba(245, 158, 11, 0.15)",
  },
  completed: {
    label: "Completed",
    color: "var(--text-secondary)",
    bg: "var(--hover-overlay)",
  },
  unsubscribed: {
    label: "Unsubscribed",
    color: "#f87171",
    bg: "rgba(248, 113, 113, 0.15)",
  },
};

export const ENROLLMENT_STATUS_STYLES = {
  active: { label: "Active", color: "var(--green)", bg: "var(--green-dim)" },
  paused: {
    label: "Paused",
    color: "var(--yellow, #f59e0b)",
    bg: "rgba(245, 158, 11, 0.15)",
  },
  completed: {
    label: "Completed",
    color: "var(--accent)",
    bg: "var(--accent-dim)",
  },
  unsubscribed: {
    label: "Unsubscribed",
    color: "#f87171",
    bg: "rgba(248, 113, 113, 0.15)",
  },
};
