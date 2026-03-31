import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  fetchWaitlist, fetchWaitlistStats, updateWaitlistEntry,
  deleteWaitlistEntry, notifyWaitlistEntry,
} from "../utils/api/waitlist";

const STATUS_COLORS = {
  waiting:   { color: "#f59e0b", bg: "rgba(245,158,11,0.1)", label: "Waiting" },
  notified:  { color: "#3b82f6", bg: "rgba(59,130,246,0.1)", label: "Notified" },
  booked:    { color: "#22c55e", bg: "rgba(34,197,94,0.1)", label: "Booked" },
  expired:   { color: "#6b7280", bg: "rgba(107,114,128,0.1)", label: "Expired" },
  cancelled: { color: "#ef4444", bg: "rgba(239,68,68,0.1)", label: "Cancelled" },
};

function formatDate(str) {
  if (!str) return "";
  const d = new Date(str + "T00:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

function formatTime(start, end) {
  if (!start && !end) return "";
  if (start && end) return `${start} - ${end}`;
  return start || end;
}

export default function WaitlistPage() {
  const { user, token } = useAuth();
  const tenantId = user?.tenant_id;

  const [entries, setEntries] = useState([]);
  const [stats, setStats] = useState({ total: 0, waiting: 0, notified: 0, booked: 0, expired: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [actionMsg, setActionMsg] = useState(null);
  const [notifyModal, setNotifyModal] = useState(null);
  const [notifyMessage, setNotifyMessage] = useState("");

  const load = useCallback(async () => {
    if (!tenantId) return;
    try {
      const [listRes, statsRes] = await Promise.all([
        fetchWaitlist(tenantId, token, { status: statusFilter || undefined }),
        fetchWaitlistStats(tenantId, token),
      ]);
      setEntries(listRes.entries || []);
      setStats(statsRes);
      setError(null);
    } catch (e) {
      setError(e.message || "Failed to load waitlist");
    } finally {
      setLoading(false);
    }
  }, [tenantId, token, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleStatusChange = async (entryId, newStatus) => {
    try {
      await updateWaitlistEntry(tenantId, entryId, { status: newStatus }, token);
      setActionMsg(`Status updated to ${newStatus}`);
      setTimeout(() => setActionMsg(null), 3000);
      load();
    } catch (e) {
      setActionMsg(`Error: ${e.message}`);
    }
  };

  const handleDelete = async (entryId) => {
    if (!confirm("Remove this waitlist entry?")) return;
    try {
      await deleteWaitlistEntry(tenantId, entryId, token);
      setActionMsg("Entry removed");
      setTimeout(() => setActionMsg(null), 3000);
      load();
    } catch (e) {
      setActionMsg(`Error: ${e.message}`);
    }
  };

  const handleNotify = async () => {
    if (!notifyModal) return;
    try {
      const res = await notifyWaitlistEntry(tenantId, notifyModal, notifyMessage || null, token);
      setActionMsg(res.message || "Customer notified");
      setNotifyModal(null);
      setNotifyMessage("");
      setTimeout(() => setActionMsg(null), 3000);
      load();
    } catch (e) {
      setActionMsg(`Error: ${e.message}`);
    }
  };

  if (loading) return <SkeletonLoader />;

  const statCards = [
    { label: "Total", value: stats.total, color: "#8b5cf6" },
    { label: "Waiting", value: stats.waiting, color: "#f59e0b" },
    { label: "Notified", value: stats.notified, color: "#3b82f6" },
    { label: "Booked", value: stats.booked, color: "#22c55e" },
  ];

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1200 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            Appointment Waitlist
          </h1>
          <p style={{ color: "var(--text-secondary)", margin: "4px 0 0", fontSize: 14 }}>
            Manage customers waiting for available appointment slots
          </p>
        </div>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 8, marginBottom: 16, color: "#ef4444" }}>
          {error}
        </div>
      )}

      {actionMsg && (
        <div style={{ padding: "12px 16px", background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.3)", borderRadius: 8, marginBottom: 16, color: "#22c55e" }}>
          {actionMsg}
        </div>
      )}

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 24 }}>
        {statCards.map(s => (
          <div key={s.label} style={{ background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: 10, padding: "16px 20px" }}>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {["", "waiting", "notified", "booked", "expired", "cancelled"].map(s => (
          <button
            key={s}
            onClick={() => { setStatusFilter(s); setLoading(true); }}
            style={{
              padding: "6px 14px",
              borderRadius: 6,
              border: statusFilter === s ? "1px solid var(--accent)" : "1px solid var(--border)",
              background: statusFilter === s ? "var(--accent-dim)" : "transparent",
              color: statusFilter === s ? "var(--accent)" : "var(--text-secondary)",
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            {s ? STATUS_COLORS[s]?.label || s : "All"}
          </button>
        ))}
      </div>

      {/* Empty state */}
      {entries.length === 0 && !loading && (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-secondary)" }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>&#128203;</div>
          <h3 style={{ color: "var(--text-primary)", marginBottom: 8 }}>No waitlist entries</h3>
          <p style={{ fontSize: 14 }}>
            When appointment slots are full, customers can join the waitlist via the booking page or chat widget.
            You will be able to notify them when a cancellation opens up a slot.
          </p>
        </div>
      )}

      {/* Entries list */}
      {entries.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {entries.map(entry => {
            const sc = STATUS_COLORS[entry.status] || STATUS_COLORS.waiting;
            return (
              <div key={entry.id} style={{
                background: "var(--card-bg)",
                border: "1px solid var(--border)",
                borderRadius: 10,
                padding: "16px 20px",
                display: "flex",
                alignItems: "center",
                gap: 16,
                flexWrap: "wrap",
              }}>
                {/* Name & contact */}
                <div style={{ flex: "1 1 200px", minWidth: 180 }}>
                  <div style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: 15 }}>
                    {entry.customer_name}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
                    {entry.customer_email && <span>{entry.customer_email}</span>}
                    {entry.customer_email && entry.customer_phone && <span> | </span>}
                    {entry.customer_phone && <span>{entry.customer_phone}</span>}
                  </div>
                </div>

                {/* Preferred date & time */}
                <div style={{ flex: "0 0 180px" }}>
                  <div style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 500 }}>
                    {formatDate(entry.preferred_date)}
                  </div>
                  {(entry.preferred_time_start || entry.preferred_time_end) && (
                    <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                      {formatTime(entry.preferred_time_start, entry.preferred_time_end)}
                    </div>
                  )}
                </div>

                {/* Notes */}
                {entry.notes && (
                  <div style={{ flex: "1 1 150px", fontSize: 12, color: "var(--text-secondary)", fontStyle: "italic" }}>
                    {entry.notes.length > 60 ? entry.notes.substring(0, 60) + "..." : entry.notes}
                  </div>
                )}

                {/* Status badge */}
                <div style={{
                  padding: "4px 10px",
                  borderRadius: 12,
                  background: sc.bg,
                  color: sc.color,
                  fontSize: 12,
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                }}>
                  {sc.label}
                </div>

                {/* Actions */}
                <div style={{ display: "flex", gap: 6 }}>
                  {entry.status === "waiting" && (
                    <button
                      onClick={() => { setNotifyModal(entry.id); setNotifyMessage(""); }}
                      title="Notify customer about available slot"
                      style={{
                        padding: "6px 12px",
                        borderRadius: 6,
                        border: "1px solid var(--accent)",
                        background: "var(--accent-dim)",
                        color: "var(--accent)",
                        cursor: "pointer",
                        fontSize: 12,
                        fontWeight: 600,
                      }}
                    >
                      Notify
                    </button>
                  )}
                  {(entry.status === "waiting" || entry.status === "notified") && (
                    <button
                      onClick={() => handleStatusChange(entry.id, "booked")}
                      title="Mark as booked"
                      style={{
                        padding: "6px 12px",
                        borderRadius: 6,
                        border: "1px solid #22c55e",
                        background: "rgba(34,197,94,0.1)",
                        color: "#22c55e",
                        cursor: "pointer",
                        fontSize: 12,
                        fontWeight: 600,
                      }}
                    >
                      Booked
                    </button>
                  )}
                  {entry.status === "waiting" && (
                    <button
                      onClick={() => handleStatusChange(entry.id, "cancelled")}
                      title="Cancel waitlist entry"
                      style={{
                        padding: "6px 10px",
                        borderRadius: 6,
                        border: "1px solid var(--border)",
                        background: "transparent",
                        color: "var(--text-secondary)",
                        cursor: "pointer",
                        fontSize: 12,
                      }}
                    >
                      Cancel
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(entry.id)}
                    title="Delete entry"
                    style={{
                      padding: "6px 10px",
                      borderRadius: 6,
                      border: "1px solid var(--border)",
                      background: "transparent",
                      color: "#ef4444",
                      cursor: "pointer",
                      fontSize: 12,
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Notify modal */}
      {notifyModal && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
        }} onClick={() => setNotifyModal(null)}>
          <div style={{
            background: "var(--card-bg)", borderRadius: 12, padding: 24, maxWidth: 480, width: "90%",
            border: "1px solid var(--border)",
          }} onClick={e => e.stopPropagation()}>
            <h3 style={{ color: "var(--text-primary)", marginBottom: 16, fontSize: 18 }}>Notify Customer</h3>
            <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 12 }}>
              Send a notification that a slot is available. Leave blank for the default message.
            </p>
            <textarea
              value={notifyMessage}
              onChange={e => setNotifyMessage(e.target.value)}
              placeholder="Custom message (optional)..."
              rows={3}
              style={{
                width: "100%", padding: 10, borderRadius: 6, border: "1px solid var(--border)",
                background: "var(--input-bg)", color: "var(--text-primary)", resize: "vertical", fontSize: 14,
                marginBottom: 16,
              }}
            />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button
                onClick={() => setNotifyModal(null)}
                style={{
                  padding: "8px 16px", borderRadius: 6, border: "1px solid var(--border)",
                  background: "transparent", color: "var(--text-secondary)", cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleNotify}
                style={{
                  padding: "8px 16px", borderRadius: 6, border: "none",
                  background: "var(--accent)", color: "#fff", cursor: "pointer", fontWeight: 600,
                }}
              >
                Send Notification
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
