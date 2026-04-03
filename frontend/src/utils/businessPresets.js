const PROFILE_ALIASES = {
  plumbing: "home_services",
  electrical: "home_services",
  roofing: "home_services",
  landscaping: "home_services",
  cleaning: "home_services",
  pest_control: "home_services",
  painting: "home_services",
  flooring: "home_services",
  general_contractor: "home_services",
  construction: "home_services",
  home_services: "home_services",
  real_estate: "real_estate",
  realestate: "real_estate",
  spa: "salon",
  veterinary: "medical",
  accounting: "professional_services",
};

const WIDGET_PRESETS = {
  default: {
    suffix: "Assistant",
    color: "#00BFFF",
    greeting: (businessName) => `Hi! Welcome to ${businessName}. How can I help you today?`,
    position: "bottom-right",
  },
  hvac: {
    suffix: "Dispatch",
    color: "#f97316",
    greeting: (businessName) => `Hi! Thanks for contacting ${businessName}. Do you need AC repair, heating service, or a new system estimate?`,
    position: "bottom-right",
  },
  home_services: {
    suffix: "Scheduling Desk",
    color: "#0f766e",
    greeting: (businessName) => `Hi! Thanks for contacting ${businessName}. What kind of service do you need today?`,
    position: "bottom-right",
  },
  real_estate: {
    suffix: "Lead Desk",
    color: "#2563eb",
    greeting: (businessName) => `Hi! Welcome to ${businessName}. Are you looking to buy, sell, or schedule a showing?`,
    position: "bottom-right",
  },
  dental: {
    suffix: "Front Desk",
    color: "#0ea5e9",
    greeting: (businessName) => `Hi! Thanks for contacting ${businessName}. Are you booking a cleaning, asking about treatment, or looking for a new patient appointment?`,
    position: "bottom-right",
  },
  medical: {
    suffix: "Care Desk",
    color: "#14b8a6",
    greeting: (businessName) => `Hi! Thanks for contacting ${businessName}. How can we help with your appointment or patient question today?`,
    position: "bottom-right",
  },
  salon: {
    suffix: "Booking Desk",
    color: "#db2777",
    greeting: (businessName) => `Hi! Welcome to ${businessName}. Are you booking a service, asking about availability, or checking pricing?`,
    position: "bottom-right",
  },
  restaurant: {
    suffix: "Host Stand",
    color: "#b45309",
    greeting: (businessName) => `Hi! Welcome to ${businessName}. Are you looking to book a table, ask about catering, or place an order?`,
    position: "bottom-right",
  },
  legal: {
    suffix: "Intake Desk",
    color: "#1d4ed8",
    greeting: (businessName) => `Hi! Thanks for contacting ${businessName}. Are you looking to schedule a consultation or ask about a legal matter?`,
    position: "bottom-right",
  },
  auto_shop: {
    suffix: "Service Desk",
    color: "#374151",
    greeting: (businessName) => `Hi! Thanks for contacting ${businessName}. What vehicle issue or service do you need help with today?`,
    position: "bottom-right",
  },
  fitness: {
    suffix: "Member Desk",
    color: "#16a34a",
    greeting: (businessName) => `Hi! Welcome to ${businessName}. Are you interested in a membership, class schedule, or personal training?`,
    position: "bottom-right",
  },
  professional_services: {
    suffix: "Client Desk",
    color: "#4338ca",
    greeting: (businessName) => `Hi! Thanks for contacting ${businessName}. How can we help with your inquiry today?`,
    position: "bottom-right",
  },
};

function resolvePresetKey(businessType) {
  const raw = (businessType || "").trim().toLowerCase();
  if (!raw) return "default";
  return PROFILE_ALIASES[raw] || raw;
}

export function getPresetWidgetDefaults(businessType, businessName) {
  const safeBusinessName = (businessName || "Your Business").trim() || "Your Business";
  const preset = WIDGET_PRESETS[resolvePresetKey(businessType)] || WIDGET_PRESETS.default;
  return {
    widget_bot_name: `${safeBusinessName} ${preset.suffix}`.trim(),
    widget_primary_color: preset.color,
    widget_greeting_message: preset.greeting(safeBusinessName),
    widget_position: preset.position,
  };
}

