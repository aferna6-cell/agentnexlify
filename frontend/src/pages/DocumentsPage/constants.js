export const STATUS_FILTERS = [
  "all",
  "draft",
  "sent",
  "viewed",
  "signed",
  "expired",
  "cancelled",
];

export const STATUS_COLORS = {
  draft: { color: "var(--text-muted)", bg: "var(--hover-overlay)" },
  sent: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  viewed: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  signed: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  expired: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
  cancelled: { color: "var(--text-muted)", bg: "var(--hover-overlay)" },
};

export const emptyForm = {
  title: "",
  html_content: "",
  signer_name: "",
  signer_email: "",
  signer_phone: "",
  lead_id: "",
  expiry_days: 30,
  notes: "",
};
