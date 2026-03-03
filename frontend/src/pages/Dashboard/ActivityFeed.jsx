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

const TYPE_ICONS = {
  new_lead: "\u{1F465}",
  automation_trigger: "\u26A1",
  conversation_summary: "\u{1F4AC}",
  lead_scored: "\u{1F525}",
  appointment: "\u{1F4C5}",
  default: "\u{1F514}",
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
