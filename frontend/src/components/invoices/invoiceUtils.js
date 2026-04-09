export const STATUS_FILTERS = [
  "all",
  "draft",
  "sent",
  "viewed",
  "paid",
  "overdue",
  "cancelled",
];

export const STATUS_COLORS = {
  draft: { color: "var(--text-muted)", bg: "var(--hover-overlay)" },
  sent: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  viewed: { color: "#8b5cf6", bg: "rgba(139,92,246,0.1)" },
  paid: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  overdue: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
  cancelled: { color: "var(--text-muted)", bg: "var(--hover-overlay)" },
};

export const emptyItem = { description: "", quantity: 1, unit_price: 0 };

export const emptyForm = {
  lead_id: "",
  items: [{ ...emptyItem }],
  tax_rate: 0,
  due_date: "",
  notes: "",
  deposit_amount: 0,
  is_recurring: false,
  recurrence_interval: "",
};

export function formatCurrency(val) {
  const num = Number(val);
  if (Number.isNaN(num)) return "$0.00";
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
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function calcSubtotal(items) {
  return (items || []).reduce(
    (sum, item) =>
      sum + (Number(item.quantity) || 0) * (Number(item.unit_price) || 0),
    0,
  );
}

export function calcTotal(items, taxRate) {
  const subtotal = calcSubtotal(items);
  return subtotal + subtotal * (Number(taxRate) / 100 || 0);
}
