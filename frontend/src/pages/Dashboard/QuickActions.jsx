import React from "react";

const Ico = ({ d }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>
);

const actions = [
  {
    icon: <Ico d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zM9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01" />,
    label: "Add FAQ Entry",
    description: "Add common questions to your bot",
    page: "faq",
  },
  {
    icon: <Ico d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />,
    label: "Configure Automations",
    description: "Set up text-backs, drip sequences",
    page: "automations",
  },
  {
    icon: <Ico d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />,
    label: "View All Leads",
    description: "See your full lead pipeline",
    page: "leads",
  },
  {
    icon: <Ico d="M21 4H3a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zM1 10h22" />,
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
