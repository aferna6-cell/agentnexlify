/**
 * One-click recurring tasks offered after a new owner names their business.
 * Departments must stay inside the engine's known set. Prompts for warehouse
 * work ask for an internal SOP or a business summary so they are not read as
 * a customer appointment text.
 */

export const BUSINESS_TYPES = [
  { id: "warehouse", label: "Warehouse / distribution" },
  { id: "restaurant", label: "Restaurant / cafe" },
  { id: "home_services", label: "Home services" },
  { id: "automotive", label: "Auto shop" },
  { id: "salon", label: "Salon / spa" },
  { id: "medical", label: "Clinic / dental" },
  { id: "retail", label: "Retail" },
  { id: "other", label: "Something else" },
];

const WEEKLY_SUMMARY = {
  label: "Weekly business summary",
  blurb: "A scannable recap of leads, bookings, and what needs you.",
  department: "accounting",
  interval_days: 7,
  prompt:
    "Prepare my weekly business summary: leads, bookings, conversations, and anything that needs my attention. Keep it to a scannable summary.",
};

const WAREHOUSE = [
  {
    label: "Low-stock alert",
    blurb: "A morning check of what is running low and who should reorder.",
    department: "people",
    interval_days: 1,
    prompt:
      "Draft an SOP for the warehouse low-stock alert: what to count, who to tell, and when to reorder.",
  },
  {
    label: "Late-shipment follow-up",
    blurb: "What to do when an outbound shipment is late.",
    department: "people",
    interval_days: 1,
    prompt: "Draft an SOP for late-shipment follow-up in the warehouse.",
  },
  {
    label: "Supplier reorder",
    blurb: "The reorder check your buyers run before stock runs out.",
    department: "people",
    interval_days: 7,
    prompt: "Draft an SOP for the warehouse supplier reorder check.",
  },
  {
    label: "Daily ops summary",
    blurb: "Shipments, stock, returns, and anything that needs a person.",
    department: "accounting",
    interval_days: 1,
    prompt:
      "Prepare my daily business summary of shipments, stock, returns, and anything that needs attention. Keep it a scannable summary, not a message to a customer.",
  },
  {
    label: "Shift and safety reminders",
    blurb: "What the oncoming shift needs to remember before the floor starts.",
    department: "people",
    interval_days: 1,
    prompt:
      "Draft a training checklist for warehouse shift and safety reminders.",
  },
  {
    label: "Returns handling",
    blurb: "Inspect, restock, or flag a return for the owner.",
    department: "people",
    interval_days: 1,
    prompt: "Draft an SOP for warehouse returns handling.",
  },
  {
    label: "Receiving check",
    blurb: "What to verify when a delivery hits the dock.",
    department: "people",
    interval_days: 1,
    prompt:
      "Draft an SOP for the warehouse receiving check when a delivery arrives.",
  },
  {
    label: "End-of-shift handoff",
    blurb: "The note the leaving shift leaves for the next one.",
    department: "people",
    interval_days: 1,
    prompt:
      "Draft a training checklist for the warehouse end-of-shift handoff.",
  },
];

const BY_TYPE = {
  warehouse: WAREHOUSE,
  restaurant: [
    {
      label: "Reservation follow-up",
      blurb:
        "A note for guests who asked about a table and have not confirmed.",
      department: "customer_service",
      interval_days: 1,
      prompt:
        "Draft a friendly follow-up for guests who asked about a reservation and have not confirmed.",
    },
    {
      label: "Tomorrow's bookings",
      blurb: "Day-before reminders for reservations already on the book.",
      department: "operations",
      interval_days: 1,
      prompt: "Draft reminder texts for tomorrow's reservations.",
    },
    WEEKLY_SUMMARY,
    {
      label: "Review ask",
      blurb: "A short text for happy guests after their visit.",
      department: "marketing",
      interval_days: 7,
      prompt:
        "Write a short, friendly text I can send to happy guests asking for a Google review.",
    },
    {
      label: "Weekly special",
      blurb: "This week's promo, ready for you to approve.",
      department: "marketing",
      interval_days: 7,
      prompt:
        "Draft this week's promotional post for my restaurant. Keep it short and friendly.",
    },
    {
      label: "Staff opening checklist",
      blurb: "The opening SOP so every shift starts the same way.",
      department: "people",
      interval_days: 7,
      prompt: "Draft a training checklist for opening the restaurant.",
    },
  ],
  home_services: [
    {
      label: "Open estimate follow-up",
      blurb: "A nudge for estimates that have not been booked.",
      department: "sales",
      interval_days: 3,
      prompt:
        "Draft a short follow-up for open estimates that have not been accepted.",
    },
    {
      label: "Missed-call callback",
      blurb: "A text for people we did not reach.",
      department: "customer_service",
      interval_days: 1,
      prompt: "Draft a callback text for missed calls from today.",
    },
    {
      label: "Job reminder",
      blurb: "Day-before reminders for scheduled jobs.",
      department: "operations",
      interval_days: 1,
      prompt: "Draft reminder texts for tomorrow's appointments.",
    },
    WEEKLY_SUMMARY,
    {
      label: "Review ask",
      blurb: "Ask a finished job for a review.",
      department: "marketing",
      interval_days: 7,
      prompt:
        "Write a short text asking a happy customer for a Google review after a finished job.",
    },
    {
      label: "Seasonal promo",
      blurb: "A limited-time offer for past customers.",
      department: "marketing",
      interval_days: 14,
      prompt:
        "Draft a short promotional message for past customers about a limited-time offer.",
    },
  ],
  automotive: [
    {
      label: "Open quote follow-up",
      blurb: "Quotes that have not turned into a visit.",
      department: "sales",
      interval_days: 3,
      prompt: "Draft a follow-up for open quotes that have not been booked.",
    },
    {
      label: "Appointment reminder",
      blurb: "Day-before reminders for the shop calendar.",
      department: "operations",
      interval_days: 1,
      prompt: "Draft reminder texts for tomorrow's appointments.",
    },
    WEEKLY_SUMMARY,
    {
      label: "Review ask",
      blurb: "A text after a finished repair.",
      department: "marketing",
      interval_days: 7,
      prompt:
        "Write a short text asking a customer for a Google review after their repair.",
    },
    {
      label: "Service special",
      blurb: "This week's shop promo.",
      department: "marketing",
      interval_days: 7,
      prompt: "Draft this week's promotional post for my auto shop.",
    },
    {
      label: "New-hire checklist",
      blurb: "How a new tech gets up to speed.",
      department: "people",
      interval_days: 30,
      prompt: "Draft a training checklist for a new technician.",
    },
  ],
  salon: [
    {
      label: "Booking follow-up",
      blurb: "Guests who asked for a time and have not confirmed.",
      department: "customer_service",
      interval_days: 1,
      prompt:
        "Draft a friendly follow-up for open booking requests that have not been confirmed.",
    },
    {
      label: "Tomorrow's appointments",
      blurb: "Day-before reminders.",
      department: "operations",
      interval_days: 1,
      prompt: "Draft reminder texts for tomorrow's appointments.",
    },
    WEEKLY_SUMMARY,
    {
      label: "Rebook message",
      blurb: "Invite regulars back.",
      department: "marketing",
      interval_days: 14,
      prompt:
        "Draft a short message inviting regular clients to rebook their next visit.",
    },
    {
      label: "Review ask",
      blurb: "A thank-you that asks for a review.",
      department: "marketing",
      interval_days: 7,
      prompt: "Write a short text asking a happy client for a Google review.",
    },
    {
      label: "Weekly promo",
      blurb: "This week's chair special.",
      department: "marketing",
      interval_days: 7,
      prompt: "Draft this week's promotional post for my salon.",
    },
  ],
  medical: [
    {
      label: "Recall message",
      blurb: "Patients who are due to come back.",
      department: "customer_service",
      interval_days: 7,
      prompt:
        "Draft a recall message for patients who have not been seen in 6 months.",
    },
    {
      label: "Appointment reminder",
      blurb: "Day-before reminders.",
      department: "operations",
      interval_days: 1,
      prompt: "Draft reminder texts for tomorrow's appointments.",
    },
    WEEKLY_SUMMARY,
    {
      label: "New-patient welcome",
      blurb: "What to expect before a first visit.",
      department: "customer_service",
      interval_days: 7,
      prompt:
        "Draft a welcome message for a new patient before their first visit.",
    },
    {
      label: "Review ask",
      blurb: "A short thank-you after a visit.",
      department: "marketing",
      interval_days: 14,
      prompt: "Write a short, friendly text asking a patient for a review.",
    },
    {
      label: "Front-desk checklist",
      blurb: "Opening the desk the same way every day.",
      department: "people",
      interval_days: 7,
      prompt: "Draft a training checklist for the front desk opening routine.",
    },
  ],
  retail: [
    {
      label: "Low-stock alert",
      blurb: "What is running low on the floor.",
      department: "people",
      interval_days: 1,
      prompt:
        "Draft an SOP for the low-stock alert: what to count, who to tell, and when to reorder.",
    },
    {
      label: "Weekly promo",
      blurb: "This week's offer for past customers.",
      department: "marketing",
      interval_days: 7,
      prompt: "Draft this week's promotional post for my shop.",
    },
    WEEKLY_SUMMARY,
    {
      label: "Review ask",
      blurb: "A thank-you that asks for a review.",
      department: "marketing",
      interval_days: 7,
      prompt: "Write a short text asking a happy customer for a Google review.",
    },
    {
      label: "Returns handling",
      blurb: "How the team handles a return.",
      department: "people",
      interval_days: 7,
      prompt: "Draft an SOP for returns handling at the counter.",
    },
    {
      label: "Opening checklist",
      blurb: "The same open, every morning.",
      department: "people",
      interval_days: 7,
      prompt: "Draft a training checklist for opening the shop.",
    },
  ],
  other: [
    WEEKLY_SUMMARY,
    {
      label: "Lead follow-up",
      blurb: "A note for people who have not heard back.",
      department: "sales",
      interval_days: 3,
      prompt: "Draft a friendly follow-up for leads who have not replied yet.",
    },
    {
      label: "Appointment reminder",
      blurb: "Day-before reminders.",
      department: "operations",
      interval_days: 1,
      prompt: "Draft reminder texts for tomorrow's appointments.",
    },
    {
      label: "Review ask",
      blurb: "Ask happy customers for a review.",
      department: "marketing",
      interval_days: 7,
      prompt:
        "Write a short, friendly text asking a happy customer for a Google review.",
    },
    {
      label: "Weekly promo",
      blurb: "A short offer you can approve before it goes out.",
      department: "marketing",
      interval_days: 7,
      prompt: "Draft this week's short promotional message for my customers.",
    },
    {
      label: "Welcome message",
      blurb: "What a new customer hears after a first visit.",
      department: "customer_service",
      interval_days: 7,
      prompt:
        "Write a warm welcome message for a new customer after their first visit.",
    },
  ],
};

const KNOWN = new Set([
  "sales",
  "marketing",
  "customer_service",
  "operations",
  "invoicing",
  "accounting",
  "admin_records",
  "people",
]);

export function resolveBusinessType(raw) {
  const key = (raw || "").toLowerCase();
  if (!key) return "";
  if (
    key.includes("warehouse") ||
    key.includes("distribution") ||
    key.includes("fulfillment") ||
    key.includes("logistics")
  ) {
    return "warehouse";
  }
  if (
    key.includes("restaurant") ||
    key.includes("food") ||
    key.includes("cafe")
  )
    return "restaurant";
  if (
    key.includes("plumb") ||
    key.includes("hvac") ||
    key.includes("roof") ||
    key.includes("electric") ||
    key.includes("landscap") ||
    key.includes("contractor") ||
    key.includes("home_services") ||
    key.includes("home services")
  )
    return "home_services";
  if (key.includes("auto") || key.includes("mechanic")) return "automotive";
  if (
    key.includes("salon") ||
    key.includes("spa") ||
    key.includes("beauty") ||
    key.includes("hair")
  )
    return "salon";
  if (
    key.includes("dental") ||
    key.includes("medical") ||
    key.includes("clinic") ||
    key.includes("health")
  )
    return "medical";
  if (key.includes("retail") || key.includes("store") || key.includes("shop"))
    return "retail";
  if (BY_TYPE[key]) return key;
  return "other";
}

export function templatesFor(businessType) {
  const id = resolveBusinessType(businessType) || "other";
  const list = BY_TYPE[id] || BY_TYPE.other;
  return list.filter((item) => KNOWN.has(item.department));
}
