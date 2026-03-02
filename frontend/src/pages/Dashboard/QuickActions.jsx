const actions = [
  {
    icon: "\u2753",
    label: "Add FAQ Entry",
    description: "Add common questions to your bot",
    page: "faq",
  },
  {
    icon: "\u26A1",
    label: "Configure Automations",
    description: "Set up text-backs, drip sequences",
    page: "automations",
  },
  {
    icon: "\u{1F465}",
    label: "View All Leads",
    description: "See your full lead pipeline",
    page: "leads",
  },
  {
    icon: "\u{1F4B3}",
    label: "Manage Billing",
    description: "Update plan, payment method",
    page: "billing",
  },
];

export default function QuickActions({ onNavigate }) {
  return (
    <div className="quick-actions">
      <div className="quick-actions-title">Quick Actions</div>
      {actions.map((action) => (
        <div
          className="quick-action-card"
          key={action.page}
          onClick={() => onNavigate && onNavigate(action.page)}
          style={{ cursor: "pointer" }}
        >
          <span className="quick-action-icon">{action.icon}</span>
          <div className="quick-action-body">
            <div className="quick-action-label">{action.label}</div>
            <div className="quick-action-desc">{action.description}</div>
          </div>
          <span className="quick-action-arrow">&rarr;</span>
        </div>
      ))}
    </div>
  );
}
