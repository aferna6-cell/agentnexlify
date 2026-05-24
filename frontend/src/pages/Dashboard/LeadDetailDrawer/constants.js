export const STAGE_OPTIONS = [
  { value: "new", label: "New" },
  { value: "contacted", label: "Contacted" },
  { value: "appointment_booked", label: "Appointment" },
  { value: "closed", label: "Closed" },
  { value: "lost", label: "Lost" },
];

export const QUALIFICATION_LABELS = {
  hot_call_now: {
    label: "Hot - Call Now",
    color: "#ff4444",
    bg: "rgba(255,68,68,0.15)",
    border: "rgba(255,68,68,0.3)",
  },
  warm_nurture_sequence: {
    label: "Warm - Nurture",
    color: "#f5a623",
    bg: "rgba(245,166,35,0.15)",
    border: "rgba(245,166,35,0.3)",
  },
  cold_drop: {
    label: "Cold - Drop",
    color: "#00bfff",
    bg: "rgba(0,191,255,0.15)",
    border: "rgba(0,191,255,0.3)",
  },
  disqualify_spam: {
    label: "Spam - Disqualify",
    color: "#666",
    bg: "rgba(102,102,102,0.15)",
    border: "rgba(102,102,102,0.3)",
  },
};

export const TIMELINE_ICONS = {
  lead_created: { icon: "+", color: "#22c55e" },
  lead_updated: { icon: "✎", color: "#00BFFF" },
  assignment: { icon: "→", color: "#8b5cf6" },
  lead_suggestion: { icon: "✨", color: "#f5a623" },
  appointment_scheduled: { icon: "📅", color: "#22c55e" },
  appointment_completed: { icon: "✓", color: "#22c55e" },
  appointment_cancelled: { icon: "✗", color: "#ef4444" },
  appointment_no_show: { icon: "!", color: "#f5a623" },
  email_open: { icon: "📧", color: "#00BFFF" },
  email_click: { icon: "🔗", color: "#8b5cf6" },
  conversation_assigned: { icon: "⇄", color: "#8b5cf6" },
  status_change: { icon: "⬆", color: "#00BFFF" },
};
