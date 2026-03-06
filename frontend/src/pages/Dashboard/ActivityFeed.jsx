import React from "react";

function formatTimeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "Yesterday";
  return `${days}d ago`;
}

const Ico = ({ d }) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>
);

const TYPE_ICONS = {
  new_lead: <Ico d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />,
  automation_trigger: <Ico d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />,
  conversation_summary: <Ico d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />,
  lead_scored: <Ico d="M12 2L15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26z" />,
  appointment: <Ico d="M19 4H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zM16 2v4M8 2v4M3 10h18" />,
  default: <Ico d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0" />,
};

export default function ActivityFeed({ activity }) {
  if (!activity || activity.length === 0) {
    return (
      <div className="activity-feed">
        <div className="activity-feed-title">Recent Activity</div>
        <div className="empty-state empty-state-compact">
          <div className="empty-state-icon">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <p className="empty-state-text">
            Activity from conversations and leads will show here once your widget is live
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="activity-feed">
      <div className="activity-feed-title">Recent Activity</div>
      {activity.map((item) => (
        <div className="activity-item" key={item.id}>
          <span className="activity-icon">
            {TYPE_ICONS[item.type] || TYPE_ICONS.default}
          </span>
          <span className="activity-text">{item.message}</span>
          <span className="activity-time">
            {formatTimeAgo(item.created_at)}
          </span>
        </div>
      ))}
    </div>
  );
}
