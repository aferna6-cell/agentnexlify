import React from "react";
import { useAuth } from "../context/AuthContext";

const planLabels = {
  free: "Free",
  foundation: "Foundation",
  growth: "Growth",
  operations: "Operations",
  enterprise: "Enterprise",
};

const planColors = {
  free: { color: "var(--green)", bg: "var(--green-dim)" },
  foundation: { color: "var(--accent)", bg: "var(--accent-dim)" },
  growth: { color: "var(--purple)", bg: "rgba(139, 92, 246, 0.15)" },
  operations: { color: "#f59e0b", bg: "rgba(245, 158, 11, 0.15)" },
  enterprise: { color: "#f59e0b", bg: "rgba(245, 158, 11, 0.15)" },
};

const Icon = ({ d, ...props }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}><path d={d} /></svg>
);

const roleColors = {
  owner: { color: "#f59e0b", bg: "rgba(245, 158, 11, 0.15)" },
  admin: { color: "var(--purple)", bg: "rgba(139, 92, 246, 0.15)" },
  member: { color: "var(--accent)", bg: "var(--accent-dim)" },
  viewer: { color: "var(--text-secondary)", bg: "rgba(148, 148, 168, 0.15)" },
};

const allNavItems = [
  { key: "dashboard", icon: <Icon d="M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z" />, label: "Dashboard" },
  { key: "analytics", icon: <Icon d="M18 20V10M12 20V4M6 20v-6" />, label: "Analytics" },
  { key: "clients", icon: <Icon d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />, label: "Clients" },
  { key: "calendar", icon: <Icon d="M19 4H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zM16 2v4M8 2v4M3 10h18" />, label: "Calendar" },
  { key: "conversations", icon: <Icon d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />, label: "Conversations" },
  { key: "automations", icon: <Icon d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />, label: "Automations" },
  { key: "widget", icon: <Icon d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zM7 15h0M2 10h20" />, label: "Widget" },
  { key: "faq", icon: <Icon d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zM9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01" />, label: "FAQ Manager" },
  { key: "team", icon: <Icon d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM20 8v6M23 11h-6" />, label: "Team", roles: ["owner", "admin"] },
  { key: "billing", icon: <Icon d="M21 4H3a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zM1 10h22" />, label: "Billing", roles: ["owner"] },
  { key: "business_page", icon: <Icon d="M3 3h18v18H3zM3 9h18M9 21V9" />, label: "Business Page", roles: ["owner", "admin"] },
  { key: "integrations", icon: <Icon d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />, label: "Integrations" },
  { key: "settings", icon: <Icon d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" />, label: "Settings", roles: ["owner", "admin"] },
  { key: "support", icon: <Icon d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zM12 16v-4M12 8h.01" />, label: "Support" },
];

export default function Sidebar({ currentPage, onNavigate, plan }) {
  const { user, logout } = useAuth();
  const activePlan = plan || user?.plan || "free";
  const userRole = user?.role || "owner";

  const navItems = allNavItems.filter(
    (item) => !item.roles || item.roles.includes(userRole)
  );

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <span>AgentNexLiFy</span>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <div
            key={item.key}
            className={`nav-item${currentPage === item.key ? " active" : ""}`}
            onClick={() => item.key === "support" ? window.open("/contact", "_blank") : onNavigate(item.key)}
          >
            <span className="nav-item-icon">{item.icon}</span>
            <span className="nav-item-label">{item.label}</span>
          </div>
        ))}
      </nav>
      <div className="sidebar-footer">
        {user && (
          <div className="sidebar-user">
            <div className="sidebar-user-name">{user.name || user.businessName || user.email}</div>
            <div className="sidebar-user-badges">
              <div
                className="sidebar-plan-badge"
                style={planColors[activePlan] ? { color: planColors[activePlan].color, background: planColors[activePlan].bg } : undefined}
              >{planLabels[activePlan] || activePlan}</div>
              {user.isTeamMember && (
                <div
                  className="sidebar-role-badge"
                  style={roleColors[userRole] ? { color: roleColors[userRole].color, background: roleColors[userRole].bg } : undefined}
                >{userRole}</div>
              )}
            </div>
          </div>
        )}
        <button className="sidebar-logout" onClick={logout}>
          Log out
        </button>
      </div>
    </div>
  );
}
