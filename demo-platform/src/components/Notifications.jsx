import { notifications, formatTimeAgo } from '../data/mockData';

export default function Notifications() {
  const groups = {
    today: notifications.filter((n) => n.group === 'today'),
    yesterday: notifications.filter((n) => n.group === 'yesterday'),
    older: notifications.filter((n) => n.group === 'older'),
  };

  const totalThisWeek = notifications.length;
  const unread = notifications.filter((n) => n.minutesAgo < 360).length;

  return (
    <>
      <div className="page-header">
        <h1>Notifications</h1>
        <p>Real-time alerts and system events</p>
      </div>

      <div className="notif-header-stats">
        {totalThisWeek} notifications this week &middot; {unread} unread
      </div>

      {groups.today.length > 0 && (
        <>
          <div className="notif-group-label">Today</div>
          {groups.today.map((n) => (
            <div
              key={n.id}
              className="notif-card"
              style={{ borderLeftColor: n.borderColor }}
            >
              <span className="notif-icon">{n.icon}</span>
              <div className="notif-body">
                <div className="notif-message">{n.message}</div>
                <div className="notif-time">{formatTimeAgo(n.minutesAgo)}</div>
              </div>
              <button className="notif-action">{n.action}</button>
            </div>
          ))}
        </>
      )}

      {groups.yesterday.length > 0 && (
        <>
          <div className="notif-group-label">Yesterday</div>
          {groups.yesterday.map((n) => (
            <div
              key={n.id}
              className="notif-card"
              style={{ borderLeftColor: n.borderColor }}
            >
              <span className="notif-icon">{n.icon}</span>
              <div className="notif-body">
                <div className="notif-message">{n.message}</div>
                <div className="notif-time">{formatTimeAgo(n.minutesAgo)}</div>
              </div>
              <button className="notif-action">{n.action}</button>
            </div>
          ))}
        </>
      )}

      {groups.older.length > 0 && (
        <>
          <div className="notif-group-label">Older</div>
          {groups.older.map((n) => (
            <div
              key={n.id}
              className="notif-card"
              style={{ borderLeftColor: n.borderColor }}
            >
              <span className="notif-icon">{n.icon}</span>
              <div className="notif-body">
                <div className="notif-message">{n.message}</div>
                <div className="notif-time">{formatTimeAgo(n.minutesAgo)}</div>
              </div>
              <button className="notif-action">{n.action}</button>
            </div>
          ))}
        </>
      )}
    </>
  );
}
