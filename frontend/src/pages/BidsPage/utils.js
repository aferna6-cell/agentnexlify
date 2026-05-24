export const STATUS_FILTERS = [
  "all",
  "draft",
  "sent",
  "viewed",
  "accepted",
  "rejected",
];

export const STATUS_COLORS = {
  draft: { color: "var(--text-muted)", bg: "var(--hover-overlay)" },
  sent: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  viewed: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  accepted: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  rejected: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
};

export const STATUS_PROGRESSION = {
  draft: ["sent"],
  sent: ["viewed", "accepted", "rejected"],
  viewed: ["accepted", "rejected"],
  accepted: [],
  rejected: [],
};

export const emptyLineItem = { name: "", qty: 1, unit_price: 0 };

export const emptyForm = {
  title: "",
  description: "",
  line_items: [{ ...emptyLineItem }],
  terms: "",
  timeline: "",
};

export function formatCurrency(val) {
  const num = Number(val);
  if (isNaN(num)) return "$0.00";
  return (
    "$" +
    num.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

export function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function calcTotal(items) {
  return (items || []).reduce(
    (sum, it) => sum + (Number(it.qty) || 0) * (Number(it.unit_price) || 0),
    0,
  );
}
