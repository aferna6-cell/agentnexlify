import { useState, useEffect, useCallback } from "react";
import { fetchActionItemsSummary, fetchActionItems, updateActionItem } from "../../utils/api";

function formatDueDate(dateStr) {
  if (!dateStr) return null;
  const due = new Date(dateStr);
  const now = new Date();
  const isOverdue = due < now;
  const diff = Math.abs(due - now);
  const days = Math.floor(diff / 86400000);

  if (isOverdue) return { text: "Overdue", overdue: true };
  if (days === 0) return { text: "Today", overdue: false };
  if (days === 1) return { text: "Tomorrow", overdue: false };
  return { text: `${days}d`, overdue: false };
}

const PRIORITY_COLORS = {
  high: "var(--red)",
  medium: "var(--yellow)",
  low: "var(--text-muted)",
};

export default function ActionItemsWidget({ tenantId, token, onNavigate }) {
  const [summary, setSummary] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);

  const loadData = useCallback(async () => {
    if (!tenantId || !token) return;
    try {
      const [summaryRes, itemsRes] = await Promise.allSettled([
        fetchActionItemsSummary(tenantId, token),
        fetchActionItems(tenantId, token, { status: "pending", limit: 5 }),
      ]);
      if (summaryRes.status === "fulfilled") setSummary(summaryRes.value);
      if (itemsRes.status === "fulfilled") setItems(itemsRes.value.items || []);
    } catch (err) {
      console.warn("Action items widget load failed:", err.message);
    } finally {
      setLoading(false);
    }
  }, [tenantId, token]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleAction = useCallback(async (itemId, newStatus) => {
    setActionLoading(itemId);
    try {
      await updateActionItem(tenantId, token, itemId, { status: newStatus });
      setItems((cur) => cur.filter((i) => i.id !== itemId));
      setSummary((cur) => {
        if (!cur) return cur;
        return {
          ...cur,
          pending: Math.max(0, (cur.pending || 0) - 1),
          [newStatus]: (cur[newStatus] || 0) + 1,
        };
      });
    } catch (err) {
      console.warn("Action item update failed:", err.message);
    } finally {
      setActionLoading(null);
    }
  }, [tenantId, token]);

  return (
    <div className="action-items-widget">
      <div className="action-items-header">
        <h3>Action Items</h3>
        {summary && (
          <div className="action-items-badges">
            <span className="action-items-badge">{summary.pending || 0} pending</span>
            {(summary.overdue || 0) > 0 && (
              <span className="action-items-badge action-items-badge-overdue">
                {summary.overdue} overdue
              </span>
            )}
          </div>
        )}
      </div>

      {loading ? (
        <p className="action-items-empty">Loading...</p>
      ) : items.length === 0 ? (
        <div className="empty-state empty-state-compact">
          <div className="empty-state-icon">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
          </div>
          <p className="empty-state-text">
            No action items yet. AI will extract tasks from your conversations automatically.
          </p>
        </div>
      ) : (
        <div className="action-items-list">
          {items.map((item) => {
            const due = formatDueDate(item.due_date);
            return (
              <div key={item.id} className="action-item-row">
                <span
                  className="action-item-priority"
                  style={{ background: PRIORITY_COLORS[item.priority] || PRIORITY_COLORS.low }}
                  title={`${item.priority || "low"} priority`}
                />
                <div className="action-item-content">
                  <div className="action-item-desc">{item.description}</div>
                  {due && (
                    <span className={`action-item-due${due.overdue ? " action-item-due-overdue" : ""}`}>
                      {due.text}
                    </span>
                  )}
                </div>
                <div className="action-item-actions">
                  <button
                    className="action-item-btn action-item-btn-done"
                    title="Mark done"
                    disabled={actionLoading === item.id}
                    onClick={() => handleAction(item.id, "done")}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </button>
                  <button
                    className="action-item-btn action-item-btn-dismiss"
                    title="Dismiss"
                    disabled={actionLoading === item.id}
                    onClick={() => handleAction(item.id, "dismissed")}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <button className="action-items-viewall" onClick={() => onNavigate("action-items")}>
        View All Action Items &rarr;
      </button>
    </div>
  );
}
