import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  fetchActionItems,
  fetchActionItemsSummary,
  createActionItem,
  updateActionItem,
  deleteActionItem,
} from "../utils/api";

const PRIORITY_COLORS = {
  high: { dot: "#ef4444", bg: "rgba(239,68,68,0.1)", text: "#ef4444" },
  medium: { dot: "#f59e0b", bg: "rgba(245,158,11,0.1)", text: "#f59e0b" },
  low: { dot: "#6b7280", bg: "rgba(107,114,128,0.1)", text: "#9ca3af" },
};

const STATUS_COLORS = {
  pending: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  done: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  dismissed: { color: "#6b7280", bg: "rgba(107,114,128,0.1)" },
};

function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function isOverdue(dueDateStr) {
  if (!dueDateStr) return false;
  const due = new Date(dueDateStr);
  const now = new Date();
  // Compare date-only (strip time)
  due.setHours(23, 59, 59, 999);
  return due < now;
}

const emptyForm = {
  description: "",
  priority: "medium",
  due_date: "",
  lead_id: "",
};

export default function ActionItemsPage() {
  const { user, token } = useAuth();
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState({ pending: 0, overdue: 0, done: 0, dismissed: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");

  // Create modal
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);

  // Track in-progress actions per item
  const [updatingIds, setUpdatingIds] = useState(new Set());

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (priorityFilter) params.priority = priorityFilter;
      const [itemsRes, summaryRes] = await Promise.all([
        fetchActionItems(user.tenantId, token, params),
        fetchActionItemsSummary(user.tenantId, token),
      ]);
      setItems(itemsRes.items || itemsRes || []);
      setSummary(summaryRes || { pending: 0, overdue: 0, done: 0, dismissed: 0 });
      setError(null);
    } catch (err) {
      console.warn("Failed to load action items:", err.message);
      setError(err.message || "Failed to load action items");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, statusFilter, priorityFilter]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  const handleCreate = async () => {
    if (!form.description.trim()) return;
    setSaving(true);
    try {
      const body = {
        description: form.description.trim(),
        priority: form.priority,
      };
      if (form.due_date) body.due_date = form.due_date;
      if (form.lead_id) body.lead_id = form.lead_id;
      await createActionItem(user.tenantId, token, body);
      setShowModal(false);
      setForm({ ...emptyForm });
      loadData();
    } catch (err) {
      console.warn("Create action item failed:", err.message);
      setError(err.message || "Failed to create action item");
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (itemId, newStatus) => {
    setUpdatingIds((prev) => new Set(prev).add(itemId));
    try {
      await updateActionItem(user.tenantId, token, itemId, { status: newStatus });
      // Optimistic update in list
      setItems((prev) =>
        prev.map((item) => (item.id === itemId ? { ...item, status: newStatus } : item))
      );
      // Refresh summary counts
      const summaryRes = await fetchActionItemsSummary(user.tenantId, token);
      setSummary(summaryRes || summary);
      setError(null);
    } catch (err) {
      console.warn("Update action item failed:", err.message);
      setError(err.message || "Failed to update action item");
    } finally {
      setUpdatingIds((prev) => {
        const next = new Set(prev);
        next.delete(itemId);
        return next;
      });
    }
  };

  const handleDelete = async (itemId) => {
    if (!window.confirm("Delete this action item? This cannot be undone.")) return;
    setUpdatingIds((prev) => new Set(prev).add(itemId));
    try {
      await deleteActionItem(user.tenantId, token, itemId);
      setItems((prev) => prev.filter((item) => item.id !== itemId));
      const summaryRes = await fetchActionItemsSummary(user.tenantId, token);
      setSummary(summaryRes || summary);
      setError(null);
    } catch (err) {
      console.warn("Delete action item failed:", err.message);
      setError(err.message || "Failed to delete action item");
    } finally {
      setUpdatingIds((prev) => {
        const next = new Set(prev);
        next.delete(itemId);
        return next;
      });
    }
  };

  if (loading) return <SkeletonLoader />;

  const summaryCards = [
    { label: "Pending", value: summary.pending ?? 0, color: "#3b82f6" },
    { label: "Overdue", value: summary.overdue ?? 0, color: "#ef4444" },
    { label: "Done", value: summary.done ?? 0, color: "#22c55e" },
    { label: "Dismissed", value: summary.dismissed ?? 0, color: "var(--text-muted)" },
  ];

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Action Items</h1>
          <p>Track follow-ups, tasks, and reminders for your leads</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            className="btn-primary"
            onClick={() => {
              setLoading(true);
              loadData();
            }}
            style={{
              background: "transparent",
              border: "1px solid var(--border-color)",
              color: "var(--text-primary)",
            }}
          >
            Refresh
          </button>
          <button
            className="btn-primary"
            onClick={() => {
              setForm({ ...emptyForm });
              setShowModal(true);
            }}
          >
            + New Action Item
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 12,
          marginBottom: 24,
        }}
      >
        {summaryCards.map((card) => (
          <div
            key={card.label}
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-color)",
              borderRadius: 12,
              padding: "16px 20px",
            }}
          >
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4 }}>
              {card.label}
            </div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: card.color }}>
              {card.value}
            </div>
          </div>
        ))}
      </div>

      {/* Filter Bar */}
      <div
        style={{
          display: "flex",
          gap: 12,
          marginBottom: 20,
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid var(--border-color)",
            background: "var(--bg-secondary)",
            color: "var(--text-primary)",
            fontSize: "0.85rem",
            cursor: "pointer",
          }}
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="done">Done</option>
          <option value="dismissed">Dismissed</option>
        </select>
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid var(--border-color)",
            background: "var(--bg-secondary)",
            color: "var(--text-primary)",
            fontSize: "0.85rem",
            cursor: "pointer",
          }}
        >
          <option value="">All Priorities</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
        {(statusFilter || priorityFilter) && (
          <button
            onClick={() => {
              setStatusFilter("");
              setPriorityFilter("");
            }}
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: "0.8rem",
              textDecoration: "underline",
            }}
          >
            Clear filters
          </button>
        )}
      </div>

      {error && (
        <div
          style={{
            marginBottom: 16,
            padding: "10px 16px",
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 8,
            color: "#ef4444",
            fontSize: "0.85rem",
          }}
        >
          {error}
          <button
            onClick={() => setError(null)}
            style={{
              marginLeft: 12,
              background: "none",
              border: "none",
              color: "#ef4444",
              cursor: "pointer",
              fontSize: "0.8rem",
              textDecoration: "underline",
            }}
          >
            dismiss
          </button>
        </div>
      )}

      {/* Action Items List */}
      {items.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>
            {statusFilter || priorityFilter
              ? "No action items match your filters"
              : "No action items yet"}
          </div>
          <p style={{ maxWidth: 440, margin: "0 auto 20px" }}>
            {statusFilter || priorityFilter
              ? "Try adjusting your filters or clear them to see all action items."
              : "Action items help you track follow-ups and tasks for your leads. Create your first one to stay organized and never miss a follow-up."}
          </p>
          {statusFilter || priorityFilter ? (
            <button
              className="btn-primary"
              onClick={() => {
                setStatusFilter("");
                setPriorityFilter("");
              }}
              style={{
                background: "transparent",
                border: "1px solid var(--border-color)",
                color: "var(--text-primary)",
              }}
            >
              Clear Filters
            </button>
          ) : (
            <button
              className="btn-primary"
              onClick={() => {
                setForm({ ...emptyForm });
                setShowModal(true);
              }}
            >
              Create Your First Action Item
            </button>
          )}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {items.map((item) => {
            const priorityInfo = PRIORITY_COLORS[item.priority] || PRIORITY_COLORS.medium;
            const statusInfo = STATUS_COLORS[item.status] || STATUS_COLORS.pending;
            const overdue = item.status === "pending" && isOverdue(item.due_date);
            const isUpdating = updatingIds.has(item.id);

            return (
              <div
                key={item.id}
                style={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 12,
                  padding: 16,
                  borderLeft: `4px solid ${priorityInfo.dot}`,
                  opacity: item.status === "done" || item.status === "dismissed" ? 0.65 : 1,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                    gap: 12,
                  }}
                >
                  {/* Left: priority dot + description + meta */}
                  <div style={{ flex: 1, minWidth: 220 }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        marginBottom: 6,
                      }}
                    >
                      {/* Priority dot */}
                      <span
                        style={{
                          display: "inline-block",
                          width: 10,
                          height: 10,
                          borderRadius: "50%",
                          background: priorityInfo.dot,
                          flexShrink: 0,
                        }}
                        title={`${item.priority} priority`}
                      />
                      {/* Description */}
                      <span
                        style={{
                          fontWeight: 600,
                          fontSize: "0.95rem",
                          textDecoration: item.status === "done" ? "line-through" : "none",
                          color:
                            item.status === "done" || item.status === "dismissed"
                              ? "var(--text-muted)"
                              : "var(--text-primary)",
                        }}
                      >
                        {item.description}
                      </span>
                    </div>

                    {/* Meta row: due date, lead name, priority badge, status badge */}
                    <div
                      style={{
                        display: "flex",
                        flexWrap: "wrap",
                        gap: 10,
                        alignItems: "center",
                        marginLeft: 20,
                      }}
                    >
                      {/* Priority badge */}
                      <span
                        style={{
                          display: "inline-block",
                          padding: "2px 8px",
                          borderRadius: 4,
                          fontSize: "0.7rem",
                          fontWeight: 600,
                          color: priorityInfo.text,
                          background: priorityInfo.bg,
                          textTransform: "capitalize",
                        }}
                      >
                        {item.priority}
                      </span>

                      {/* Status badge */}
                      <span
                        style={{
                          display: "inline-block",
                          padding: "2px 8px",
                          borderRadius: 4,
                          fontSize: "0.7rem",
                          fontWeight: 600,
                          color: statusInfo.color,
                          background: statusInfo.bg,
                          textTransform: "capitalize",
                        }}
                      >
                        {item.status}
                      </span>

                      {/* Due date */}
                      {item.due_date && (
                        <span
                          style={{
                            fontSize: "0.8rem",
                            color: overdue ? "#ef4444" : "var(--text-muted)",
                            fontWeight: overdue ? 600 : 400,
                          }}
                        >
                          {overdue ? "Overdue" : `Due ${formatDate(item.due_date)}`}
                        </span>
                      )}

                      {/* Lead name */}
                      {item.lead_name && (
                        <span
                          style={{
                            fontSize: "0.8rem",
                            color: "var(--text-secondary)",
                          }}
                        >
                          Lead: {item.lead_name}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Right: action buttons */}
                  <div
                    style={{
                      display: "flex",
                      gap: 6,
                      alignItems: "center",
                      flexShrink: 0,
                    }}
                  >
                    {item.status === "pending" && (
                      <>
                        <button
                          onClick={() => handleStatusChange(item.id, "done")}
                          disabled={isUpdating}
                          style={{
                            background: "none",
                            border: "1px solid var(--border-color)",
                            borderRadius: 6,
                            padding: "6px 10px",
                            color: "#22c55e",
                            cursor: "pointer",
                            fontSize: "0.8rem",
                            opacity: isUpdating ? 0.5 : 1,
                          }}
                        >
                          {isUpdating ? "..." : "Done"}
                        </button>
                        <button
                          onClick={() => handleStatusChange(item.id, "dismissed")}
                          disabled={isUpdating}
                          style={{
                            background: "none",
                            border: "1px solid var(--border-color)",
                            borderRadius: 6,
                            padding: "6px 10px",
                            color: "var(--text-muted)",
                            cursor: "pointer",
                            fontSize: "0.8rem",
                            opacity: isUpdating ? 0.5 : 1,
                          }}
                        >
                          {isUpdating ? "..." : "Dismiss"}
                        </button>
                      </>
                    )}
                    {item.status !== "pending" && (
                      <button
                        onClick={() => handleStatusChange(item.id, "pending")}
                        disabled={isUpdating}
                        style={{
                          background: "none",
                          border: "1px solid var(--border-color)",
                          borderRadius: 6,
                          padding: "6px 10px",
                          color: "#3b82f6",
                          cursor: "pointer",
                          fontSize: "0.8rem",
                          opacity: isUpdating ? 0.5 : 1,
                        }}
                      >
                        {isUpdating ? "..." : "Reopen"}
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(item.id)}
                      disabled={isUpdating}
                      style={{
                        background: "none",
                        border: "1px solid var(--border-color)",
                        borderRadius: 6,
                        padding: "6px 10px",
                        color: "var(--red, #ef4444)",
                        cursor: "pointer",
                        fontSize: "0.8rem",
                        opacity: isUpdating ? 0.5 : 1,
                      }}
                    >
                      {isUpdating ? "..." : "Delete"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Action Item Modal */}
      {showModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setShowModal(false)}
        >
          <div
            style={{
              background: "var(--bg-primary)",
              borderRadius: 12,
              padding: 24,
              width: "90%",
              maxWidth: 480,
              border: "1px solid var(--border-color)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 16 }}>New Action Item</h3>

            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.8rem",
                    marginBottom: 4,
                    color: "var(--text-secondary)",
                  }}
                >
                  Description *
                </label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="e.g. Follow up with John about the kitchen remodel quote"
                  rows={3}
                  style={{ width: "100%", resize: "vertical" }}
                />
              </div>
              <div style={{ display: "flex", gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "0.8rem",
                      marginBottom: 4,
                      color: "var(--text-secondary)",
                    }}
                  >
                    Priority
                  </label>
                  <select
                    value={form.priority}
                    onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontSize: "0.85rem",
                      cursor: "pointer",
                    }}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "0.8rem",
                      marginBottom: 4,
                      color: "var(--text-secondary)",
                    }}
                  >
                    Due Date
                  </label>
                  <input
                    type="date"
                    value={form.due_date}
                    onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontSize: "0.85rem",
                    }}
                  />
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowModal(false)}
                style={{
                  background: "transparent",
                  border: "1px solid var(--border-color)",
                  borderRadius: 8,
                  padding: "8px 16px",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleCreate}
                disabled={!form.description.trim() || saving}
              >
                {saving ? "Creating..." : "Create Action Item"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
