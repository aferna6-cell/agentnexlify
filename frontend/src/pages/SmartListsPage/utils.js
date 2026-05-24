export const STATUS_OPTIONS = [
  { value: "new", label: "New" },
  { value: "contacted", label: "Contacted" },
  { value: "appointment_booked", label: "Appt Booked" },
  { value: "closed", label: "Closed" },
  { value: "lost", label: "Lost" },
];

export const TEMPERATURE_OPTIONS = [
  { value: "", label: "Any" },
  { value: "hot", label: "Hot" },
  { value: "warm", label: "Warm" },
  { value: "cold", label: "Cold" },
];

export const TEMPERATURE_COLORS = {
  hot: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
  warm: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  cold: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
};

export const STATUS_BADGE_COLORS = {
  new: { color: "#6b7280", bg: "rgba(107,114,128,0.1)" },
  contacted: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  appointment_booked: { color: "#8b5cf6", bg: "rgba(139,92,246,0.1)" },
  closed: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  lost: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
};

export const emptyFilters = {
  status: [],
  lead_temperature: "",
  min_score: "",
  max_score: "",
  tags_include: [],
  assigned_to: "",
  created_after: "",
  created_before: "",
  has_email: false,
  has_phone: false,
  search: "",
};
