import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";

const planLabels = {
  free: "Free",
  growth: "Growth",
  professional: "Professional",
  autopilot: "Autopilot",
  enterprise: "Enterprise",
  foundation: "Growth",
  operations: "Professional",
};

const planColors = {
  free: { color: "var(--green)", bg: "var(--green-dim)" },
  growth: { color: "var(--accent)", bg: "var(--accent-dim)" },
  professional: { color: "var(--purple)", bg: "rgba(139, 92, 246, 0.15)" },
  autopilot: { color: "var(--accent)", bg: "var(--accent-dim)" },
  enterprise: { color: "var(--yellow)", bg: "var(--yellow-dim)" },
  foundation: { color: "var(--accent)", bg: "var(--accent-dim)" },
  operations: { color: "var(--purple)", bg: "rgba(139, 92, 246, 0.15)" },
};

const Icon = ({ d, ...props }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}><path d={d} /></svg>
);

const roleColors = {
  owner: { color: "var(--yellow)", bg: "var(--yellow-dim)" },
  admin: { color: "var(--purple)", bg: "rgba(139, 92, 246, 0.15)" },
  member: { color: "var(--accent)", bg: "var(--accent-dim)" },
  viewer: { color: "var(--text-secondary)", bg: "var(--hover-overlay)" },
};

const allNavItems = [
  { key: "dashboard", icon: <Icon d="M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z" />, label: "Dashboard" },
  { key: "analytics", icon: <Icon d="M18 20V10M12 20V4M6 20v-6" />, label: "Analytics" },
  { key: "clients", icon: <Icon d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />, label: "Clients" },
  { key: "pipeline", icon: <Icon d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18" />, label: "Pipeline", roles: ["owner", "admin", "member"] },
  { key: "calendar", icon: <Icon d="M19 4H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zM16 2v4M8 2v4M3 10h18" />, label: "Calendar" },
  { key: "conversations", icon: <Icon d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />, label: "Conversations" },
  { key: "action_items", icon: <Icon d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2M9 14l2 2 4-4" />, label: "Action Items" },
  { key: "automations", icon: <Icon d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />, label: "Automations" },
  { key: "snippets", icon: <Icon d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2zM8 9h8M8 13h5" />, label: "Snippets" },
  { key: "widget", icon: <Icon d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zM7 15h0M2 10h20" />, label: "Widget" },
  { key: "calls", icon: <Icon d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />, label: "Calls" },
  { key: "chat_flows", icon: <Icon d="M22 12h-4l-3 9L9 3l-3 9H2" />, label: "Chat Flows", roles: ["owner", "admin"] },
  { key: "faq", icon: <Icon d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zM9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01" />, label: "FAQ Manager" },
  { key: "reviews", icon: <Icon d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />, label: "Reviews" },
  { key: "csat", icon: <Icon d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />, label: "CSAT", roles: ["owner", "admin"] },
  { key: "local_seo", icon: <Icon d="M11 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM21 21l-4.35-4.35" />, label: "Local SEO", roles: ["owner", "admin"] },
  { key: "menu", icon: <Icon d="M3 5h18M3 12h18M3 19h12" />, label: "Menu", roles: ["owner", "admin"], businessTypes: ["restaurant"] },
  { key: "orders", icon: <Icon d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2" />, label: "Orders", businessTypes: ["restaurant"] },
  { key: "jobs", icon: <Icon d="M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2zM16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />, label: "Job Board", roles: ["owner", "admin"] },
  { key: "bids", icon: <Icon d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8" />, label: "Bids", roles: ["owner", "admin"] },
  { key: "invoices", icon: <Icon d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M12 18v-6M9 15h6" />, label: "Invoices", roles: ["owner", "admin", "member"] },
  { key: "documents", icon: <Icon d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M9 15l2 2 4-4" />, label: "Documents", roles: ["owner", "admin"] },
  { key: "smart_lists", icon: <Icon d="M3 6h18M3 12h12M3 18h18M19 12l2 2-2 2" />, label: "Smart Lists", roles: ["owner", "admin", "member"] },
  { key: "form_builder", icon: <Icon d="M9 11H3v10h6V11zM21 3h-6v18h6V3zM15 7H9v4h6V7z" />, label: "Forms", roles: ["owner", "admin"] },
  { key: "waitlist", icon: <Icon d="M12 2v4M12 18v4M8 8h8M6 12h12M8 16h8" />, label: "Waitlist" },
  { key: "scoring_config", icon: <Icon d="M22 12h-4l-3 9L9 3l-3 9H2" />, label: "Lead Scoring", roles: ["owner", "admin"] },
  { key: "client_portal", icon: <Icon d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10zM9 12l2 2 4-4" />, label: "Client Portal" },
  { key: "content_studio", icon: <Icon d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />, label: "Content Studio" },
  { key: "social_media", icon: <Icon d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />, label: "Social Media" },
  { key: "campaigns", icon: <Icon d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zM22 6l-10 7L2 6" />, label: "Campaigns" },
  { key: "team", icon: <Icon d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM20 8v6M23 11h-6" />, label: "Team", roles: ["owner", "admin"] },
  { key: "billing", icon: <Icon d="M21 4H3a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zM1 10h22" />, label: "Billing", roles: ["owner"] },
  { key: "business_page", icon: <Icon d="M3 3h18v18H3zM3 9h18M9 21V9" />, label: "Business Page", roles: ["owner", "admin"] },
  { key: "integrations", icon: <Icon d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />, label: "Integrations" },
  { key: "mcp_setup", icon: <Icon d="M13 10V3L4 14h7v7l9-11h-7z" />, label: "MCP Setup", roles: ["owner", "admin"] },
  { key: "settings", icon: <Icon d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" />, label: "Settings", roles: ["owner", "admin"] },
  { key: "support", icon: <Icon d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zM12 16v-4M12 8h.01" />, label: "Support" },
];

const SunIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5" />
    <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
  </svg>
);

const MoonIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
  </svg>
);

const HamburgerIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="3" y1="6" x2="21" y2="6" />
    <line x1="3" y1="12" x2="21" y2="12" />
    <line x1="3" y1="18" x2="21" y2="18" />
  </svg>
);

const CloseIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

export default function Sidebar({ currentPage, onNavigate, plan }) {
  const { user, logout } = useAuth();
  const activePlan = plan || user?.plan || "free";
  const userRole = user?.role || "owner";
  const [mobileOpen, setMobileOpen] = useState(false);

  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("theme") || "dark";
  });

  useEffect(() => {
    const appEl = document.querySelector(".app");
    if (appEl) appEl.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  // Close sidebar on mobile when clicking outside
  useEffect(() => {
    if (!mobileOpen) return;
    const handleClickOutside = (e) => {
      if (!e.target.closest(".sidebar") && !e.target.closest(".sidebar-hamburger")) {
        setMobileOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [mobileOpen]);

  // Close sidebar on mobile when navigating
  const handleNavClick = (key) => {
    setMobileOpen(false);
    if (key === "support") {
      window.open("/contact", "_blank");
    } else {
      onNavigate(key);
    }
  };

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const businessType = (user?.businessType || "").toLowerCase();
  const navItems = allNavItems.filter(
    (item) =>
      (!item.roles || item.roles.includes(userRole)) &&
      (!item.businessTypes || item.businessTypes.includes(businessType))
  );

  return (
    <>
      {/* Hamburger button — only visible on mobile */}
      <button
        className="sidebar-hamburger"
        onClick={() => setMobileOpen((prev) => !prev)}
        aria-label={mobileOpen ? "Close menu" : "Open menu"}
      >
        {mobileOpen ? <CloseIcon /> : <HamburgerIcon />}
      </button>

      {/* Backdrop overlay — only on mobile when open */}
      {mobileOpen && <div className="sidebar-backdrop" onClick={() => setMobileOpen(false)} />}

      <div className={`sidebar${mobileOpen ? " sidebar-mobile-open" : ""}`}>
        <div className="sidebar-logo">
          <span>AgentNexLiFy</span>
        </div>
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <div
              key={item.key}
              className={`nav-item${currentPage === item.key ? " active" : ""}`}
              onClick={() => handleNavClick(item.key)}
            >
              <span className="nav-item-icon">{item.icon}</span>
              <span className="nav-item-label">{item.label}</span>
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="theme-toggle" onClick={toggleTheme} title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}>
            <span className="nav-item-icon">{theme === "dark" ? <SunIcon /> : <MoonIcon />}</span>
            <span className="nav-item-label">{theme === "dark" ? "Light mode" : "Dark mode"}</span>
          </button>
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
    </>
  );
}
