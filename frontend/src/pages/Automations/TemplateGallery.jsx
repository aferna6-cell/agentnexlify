const TEMPLATES = [
  {
    id: "welcome",
    name: "Welcome Email Series",
    description: "Automatically welcome new leads with a warm intro and 24h follow-up.",
    trigger: "new_lead",
    steps: 2,
    icon: "W",
  },
  {
    id: "no_response",
    name: "No Response Follow-Up",
    description: "Re-engage leads who haven't responded within 24 hours.",
    trigger: "no_response_24h",
    steps: 1,
    icon: "N",
  },
  {
    id: "appointment",
    name: "Appointment Booked Series",
    description: "Confirm and remind leads when they move to the appointment stage.",
    trigger: "lead_stage_change",
    steps: 2,
    icon: "A",
  },
  {
    id: "review_request",
    name: "Review Request",
    description: "Ask for a Google review after an appointment is completed. Sends initial request after 1 hour and a reminder after 3 days.",
    trigger: "appointment_completed",
    steps: 2,
    icon: "R",
  },
];

const triggerLabels = {
  new_lead: "New Lead",
  no_response_24h: "No Response",
  lead_stage_change: "Stage Change",
  appointment_completed: "Appointment Completed",
};

const cardStyle = {
  background: "var(--bg-card)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  padding: "24px",
  display: "flex",
  flexDirection: "column",
  gap: "12px",
  transition: "border-color 0.2s",
};

const btnStyle = {
  padding: "8px 16px",
  background: "var(--accent)",
  color: "var(--accent-contrast)",
  border: "none",
  borderRadius: "var(--radius-sm)",
  cursor: "pointer",
  fontWeight: 600,
  fontSize: "13px",
  alignSelf: "flex-start",
};

export default function TemplateGallery({ onUseTemplate, loading }) {
  return (
    <div>
      <h3 style={{ color: "var(--text-primary)", margin: "0 0 16px" }}>Quick Start Templates</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "16px" }}>
        {TEMPLATES.map((t) => (
          <div
            key={t.id}
            style={cardStyle}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
          >
            <div style={{ fontSize: "28px" }}>{t.icon}</div>
            <div style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "15px" }}>{t.name}</div>
            <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: 1.5 }}>{t.description}</div>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <span style={{
                padding: "2px 8px",
                background: "var(--accent-dim)",
                color: "var(--accent)",
                borderRadius: "var(--radius-sm)",
                fontSize: "11px",
                fontWeight: 600,
              }}>
                {triggerLabels[t.trigger]}
              </span>
              <span style={{
                padding: "2px 8px",
                background: "var(--purple)",
                color: "var(--text-on-accent, #fff)",
                borderRadius: "var(--radius-sm)",
                fontSize: "11px",
                fontWeight: 600,
                opacity: 0.8,
              }}>
                {t.steps} step{t.steps > 1 ? "s" : ""}
              </span>
            </div>
            <button
              style={{ ...btnStyle, opacity: loading ? 0.6 : 1 }}
              disabled={loading}
              onClick={() => onUseTemplate(t.id)}
            >
              Use This Template
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
