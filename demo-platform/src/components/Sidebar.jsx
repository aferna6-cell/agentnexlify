const navItems = [
  { key: 'dashboard', icon: '\u{1F4CA}', label: 'Dashboard' },
  { key: 'chat', icon: '\u{1F4AC}', label: 'Live Chat' },
  { key: 'faq', icon: '\u{1F916}', label: 'FAQ Bot' },
  { key: 'automations', icon: '\u26A1', label: 'Automations' },
  { key: 'notifications', icon: '\u{1F514}', label: 'Notifications', badge: 12 },
  { key: 'settings', icon: '\u2699\uFE0F', label: 'Settings' },
];

export default function Sidebar({ currentPage, onNavigate }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <img src="/logo.png" alt="AgentNexLiFy" />
        <span>AgentNexLiFy</span>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <div
            key={item.key}
            className={`nav-item ${currentPage === item.key ? 'active' : ''}`}
            onClick={() => onNavigate(item.key)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && onNavigate(item.key)}
          >
            <span className="nav-item-icon">{item.icon}</span>
            <span className="nav-item-label">{item.label}</span>
            {item.badge && <span className="nav-badge">{item.badge}</span>}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="demo-badge">
          {'\uD83D\uDEE1\uFE0F'} DEMO MODE
        </div>
      </div>
    </aside>
  );
}
