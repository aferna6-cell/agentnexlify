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

const navItems = [
  { key: "dashboard", icon: "\u{1F4CA}", label: "Dashboard" },
  { key: "leads", icon: "\u{1F465}", label: "Leads" },
  { key: "conversations", icon: "\u{1F4AC}", label: "Conversations" },
  { key: "automations", icon: "\u26A1", label: "Automations" },
  { key: "widget", icon: "\u{1F4BB}", label: "Widget" },
  { key: "faq", icon: "\u2753", label: "FAQ Manager" },
  { key: "billing", icon: "\u{1F4B3}", label: "Billing" },
  { key: "settings", icon: "\u2699\uFE0F", label: "Settings" },
];

export default function Sidebar({ currentPage, onNavigate, plan }) {
  const { user, logout } = useAuth();
  const activePlan = plan || user?.plan || "free";

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
            onClick={() => onNavigate(item.key)}
          >
            <span className="nav-item-icon">{item.icon}</span>
            <span className="nav-item-label">{item.label}</span>
          </div>
        ))}
      </nav>
      <div className="sidebar-footer">
        {user && (
          <div className="sidebar-user">
            <div className="sidebar-user-name">{user.businessName || user.email}</div>
            <div
              className="sidebar-plan-badge"
              style={planColors[activePlan] ? { color: planColors[activePlan].color, background: planColors[activePlan].bg } : undefined}
            >{planLabels[activePlan] || activePlan}</div>
          </div>
        )}
        <button className="sidebar-logout" onClick={logout}>
          Log out
        </button>
      </div>
    </div>
  );
}
