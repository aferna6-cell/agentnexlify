export const TRIGGER_OPTIONS = [
  { value: "new_lead", label: "New Lead Created" },
  { value: "lead_stage_change", label: "Lead Stage Changes" },
  { value: "no_response_24h", label: "No Response (24 hours)" },
  { value: "appointment_completed", label: "Appointment Completed" },
];

export const DELAY_UNITS = [
  { value: 1, label: "minutes" },
  { value: 60, label: "hours" },
  { value: 1440, label: "days" },
];

export const TEMPLATE_VARS = [
  { token: "{{name}}", label: "Name" },
  { token: "{{business_name}}", label: "Business" },
  { token: "{{email}}", label: "Email" },
  { token: "{{phone}}", label: "Phone" },
  { token: "{{review_link}}", label: "Review Link" },
];

export const FORMAT_ACTIONS = [
  { label: "B", tag: "strong", title: "Bold" },
  { label: "I", tag: "em", title: "Italic" },
  { label: "H2", tag: "h2", title: "Heading" },
  { label: "P", tag: "p", title: "Paragraph" },
  { label: "Link", tag: "a", title: "Insert link" },
  { label: "BR", tag: "br", title: "Line break" },
];

export const SAMPLE_CONTEXT = {
  "{{name}}": "Alex Johnson",
  "{{business_name}}": "Your Business",
  "{{email}}": "alex@example.com",
  "{{phone}}": "(555) 123-4567",
  "{{review_link}}": "https://g.page/your-business/review",
};

export const SAMPLE_DATA = {
  name: "Alex Johnson",
  first_name: "Alex",
  email: "alex@example.com",
  phone: "(555) 123-4567",
  business_name: "Your Business",
  business_phone: "(555) 987-6543",
  appointment_date: "Friday, April 10, 2026",
  appointment_time: "2:00 PM",
  review_link: "https://g.page/your-business/review",
  unsubscribe_url: "#",
  status: "New Lead",
  service: "General Consultation",
};

export const catColors = {
  welcome: "#22c55e",
  follow_up: "#3b82f6",
  reminder: "#eab308",
  review: "#a855f7",
  promotion: "#ec4899",
  custom: "#94a3b8",
};
