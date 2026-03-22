import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchNotifications } from "../utils/api/dashboard";

export default function NotificationBell({ onNavigate }) {
  const { user, token } = useAuth();
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const load = useCallback(async () => {
    if (!user?.tenantId || !token) return;
    try {
      const res = await fetchNotifications(user.tenantId, token);
      setData(res);
    } catch (err) {
      console.error("Failed to load notifications", err);
    }
  }, [user?.tenantId, token]);

  // Poll every 60s
  useEffect(() => {
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, [load]);

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const totalUnread = data?.total_unread || 0;

  const typeIcons = {
    new_lead: "\u{1F464}",
    appointment: "\u{1F4C5}",
    new_conversation: "\u{1F4AC}",
    activity: "\u{1F4CB}",
  };

  const handleItemClick = (item) => {
    setOpen(false);
    if (item.type === "new_lead") onNavigate?.("leads");
    else if (item.type === "appointment") onNavigate?.("calendar");
    else if (item.type === "new_conversation") onNavigate?.("conversations");
  };

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          position: "relative",
          padding: "6px",
          borderRadius: "8px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--text-secondary)",
          transition: "background 0.2s",
        }}
        title="Notifications"
        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--hover-overlay)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "none")}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {totalUnread > 0 && (
          <span style={{
            position: "absolute",
            top: 2,
            right: 2,
            minWidth: 16,
            height: 16,
            borderRadius: "50%",
            background: "#ef4444",
            color: "#fff",
            fontSize: "10px",
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "0 3px",
          }}>
            {totalUnread > 99 ? "99+" : totalUnread}
          </span>
        )}
      </button>

      {open && (
        <div style={{
          position: "absolute",
          top: "calc(100% + 8px)",
          right: 0,
          width: 340,
          maxHeight: 420,
          background: "var(--card-bg)",
          border: "1px solid var(--border)",
          borderRadius: "12px",
          boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
          zIndex: 1000,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}>
          {/* Header */}
          <div style={{
            padding: "12px 16px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}>
            <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-primary)" }}>
              Notifications
            </span>
            <div style={{ display: "flex", gap: "12px", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              {data && (
                <>
                  <span>{data.new_leads_count} lead{data.new_leads_count !== 1 ? "s" : ""}</span>
                  <span>{data.new_conversations_count} chat{data.new_conversations_count !== 1 ? "s" : ""}</span>
                  <span>{data.todays_appointments_count} appt{data.todays_appointments_count !== 1 ? "s" : ""}</span>
                </>
              )}
            </div>
          </div>

          {/* Items */}
          <div style={{ flex: 1, overflowY: "auto", padding: "4px 0" }}>
            {(!data || data.recent_items.length === 0) ? (
              <div style={{
                padding: "24px 16px",
                textAlign: "center",
                color: "var(--text-muted)",
                fontSize: "0.85rem",
              }}>
                No recent activity
              </div>
            ) : (
              data.recent_items.map((item, i) => (
                <div
                  key={i}
                  onClick={() => handleItemClick(item)}
                  style={{
                    padding: "10px 16px",
                    display: "flex",
                    gap: "10px",
                    alignItems: "flex-start",
                    cursor: "pointer",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--hover-overlay)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <span style={{ fontSize: "1.1rem", flexShrink: 0, marginTop: 2 }}>
                    {typeIcons[item.type] || "\u{1F514}"}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: "0.82rem",
                      fontWeight: 500,
                      color: "var(--text-primary)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}>
                      {item.title}
                    </div>
                    <div style={{
                      fontSize: "0.75rem",
                      color: "var(--text-secondary)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}>
                      {item.description}
                    </div>
                  </div>
                  {item.created_at && (
                    <span style={{
                      fontSize: "0.7rem",
                      color: "var(--text-muted)",
                      flexShrink: 0,
                      whiteSpace: "nowrap",
                    }}>
                      {formatTimeAgo(item.created_at)}
                    </span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function formatTimeAgo(isoStr) {
  try {
    const dt = new Date(isoStr);
    const now = new Date();
    const diffMs = now - dt;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "now";
    if (diffMin < 60) return `${diffMin}m`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h`;
    const diffDay = Math.floor(diffHr / 24);
    return `${diffDay}d`;
  } catch {
    return "";
  }
}
