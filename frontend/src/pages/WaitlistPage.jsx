import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchWaitlistEntries, fetchWaitlistStats, updateWaitlistEntry, deleteWaitlistEntry } from "../utils/api/waitlist";

const STATUS_COLORS = {
  waiting: { bg: "var(--accent-dim)", text: "var(--accent)" },
  notified: { bg: "var(--yellow-dim)", text: "var(--yellow)" },
  booked: { bg: "var(--green-dim)", text: "var(--green)" },
  expired: { bg: "var(--hover-overlay)", text: "var(--text-muted)" },
  cancelled: { bg: "var(--hover-overlay)", text: "var(--text-muted)" },
};

export default function WaitlistPage() {
  const { user, token } = useAuth();
  const [entries, setEntries] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("waiting");
  const [error, setError] = useState(null);

  const tenantId = user?.tenant_id;

  const loadData = useCallback(async () => {
    if (!tenantId || !token) return;
    setLoading(true);
    setError(null);
    try {
      const [entriesRes, statsRes] = await Promise.all([
        fetchWaitlistEntries(tenantId, token, { status: filter !== "all" ? filter : undefined }),
        fetchWaitlistStats(tenantId, token),
      ]);
      setEntries(entriesRes.entries || []);
      setStats(statsRes);
    } catch (err) {
      setError(err.message || "Failed to load waitlist");
    } finally {
      setLoading(false);
    }
  }, [tenantId, token, filter]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleStatusChange = async (entryId, newStatus) => {
    try {
      await updateWaitlistEntry(tenantId, token, entryId, { status: newStatus });
      loadData();
    } catch (err) {
      alert(err.message || "Failed to update entry");
    }
  };

  const handleDelete = async (entryId) => {
    if (!confirm("Remove this waitlist entry?")) return;
    try {
      await deleteWaitlistEntry(tenantId, token, entryId);
      loadData();
    } catch (err) {
      alert(err.message || "Failed to delete entry");
    }
  };

  const formatDate = (dateStr) => {
    try {
      const d = new Date(dateStr + "T00:00:00");
      return d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
    } catch {
      return dateStr;
    }
  };

  const formatCreated = (isoStr) => {
    try {
      return new Date(isoStr).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
    } catch {
      return isoStr;
    }
  };

  return (
    <div style={{ padding: "2rem", maxWidth: 1100, margin: "0 auto" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
        Appointment Waitlist
      </h1>
      <p style={{ color: "var(--text-muted)", marginBottom: "1.5rem" }}>
        Manage visitors waiting for appointment slots. They get notified automatically when a cancellation opens a spot.
      </p>

      {/* Stats cards */}
      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
          {[
            { label: "Waiting", value: stats.waiting, color: "var(--accent)" },
            { label: "Notified", value: stats.notified, color: "var(--yellow)" },
            { label: "Booked", value: stats.booked, color: "var(--green)" },
            { label: "Upcoming", value: stats.upcoming, color: "var(--text-primary)" },
            { label: "Conversion", value: `${stats.conversion_rate}%`, color: "var(--accent)" },
          ].map((s) => (
            <div
              key={s.label}
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: "1rem",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: "1.5rem", fontWeight: 700, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: 4 }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filter tabs */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        {["all", "waiting", "notified", "booked", "expired", "cancelled"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: "0.4rem 1rem",
              borderRadius: 20,
              border: filter === f ? "1px solid var(--accent)" : "1px solid var(--border)",
              background: filter === f ? "var(--accent-dim)" : "transparent",
              color: filter === f ? "var(--accent)" : "var(--text-muted)",
              cursor: "pointer",
              fontSize: "0.85rem",
              textTransform: "capitalize",
            }}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: "1rem", background: "var(--red-dim)", borderRadius: 8, color: "var(--red)", marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "3rem", color: "var(--text-muted)" }}>Loading waitlist...</div>
      ) : entries.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: "3rem",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 12,
          }}
        >
          <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>No waitlist entries</div>
          <p style={{ color: "var(--text-muted)" }}>
            {filter === "waiting"
              ? "No one is currently waiting for an appointment slot."
              : `No entries with status "${filter}".`}
          </p>
          <p style={{ color: "var(--text-muted)", marginTop: "0.5rem", fontSize: "0.9rem" }}>
            Visitors can join the waitlist from the booking widget when all slots are taken.
          </p>
        </div>
      ) : (
        /* Entries table */
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Name", "Contact", "Preferred Date", "Time", "Status", "Joined", "Actions"].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: "0.75rem 1rem",
                      textAlign: "left",
                      fontSize: "0.8rem",
                      color: "var(--text-muted)",
                      fontWeight: 600,
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => {
                const sc = STATUS_COLORS[entry.status] || STATUS_COLORS.waiting;
                return (
                  <tr key={entry.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "0.75rem 1rem", color: "var(--text-primary)", fontWeight: 500 }}>
                      {entry.customer_name}
                    </td>
                    <td style={{ padding: "0.75rem 1rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                      {entry.customer_email && <div>{entry.customer_email}</div>}
                      {entry.customer_phone && <div>{entry.customer_phone}</div>}
                    </td>
                    <td style={{ padding: "0.75rem 1rem", color: "var(--text-primary)" }}>
                      {formatDate(entry.preferred_date)}
                    </td>
                    <td style={{ padding: "0.75rem 1rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                      {entry.preferred_time_start
                        ? `${entry.preferred_time_start}${entry.preferred_time_end ? ` - ${entry.preferred_time_end}` : ""}`
                        : "Any time"}
                    </td>
                    <td style={{ padding: "0.75rem 1rem" }}>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "0.2rem 0.6rem",
                          borderRadius: 12,
                          fontSize: "0.75rem",
                          fontWeight: 600,
                          background: sc.bg,
                          color: sc.text,
                          textTransform: "capitalize",
                        }}
                      >
                        {entry.status}
                      </span>
                      {entry.notified_at && (
                        <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>
                          Notified {formatCreated(entry.notified_at)}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: "0.75rem 1rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                      {formatCreated(entry.created_at)}
                    </td>
                    <td style={{ padding: "0.75rem 1rem" }}>
                      <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                        {entry.status === "waiting" && (
                          <>
                            <button
                              onClick={() => handleStatusChange(entry.id, "notified")}
                              style={{
                                padding: "0.3rem 0.6rem",
                                borderRadius: 6,
                                border: "1px solid var(--accent)",
                                background: "transparent",
                                color: "var(--accent)",
                                cursor: "pointer",
                                fontSize: "0.75rem",
                              }}
                            >
                              Notify
                            </button>
                            <button
                              onClick={() => handleStatusChange(entry.id, "cancelled")}
                              style={{
                                padding: "0.3rem 0.6rem",
                                borderRadius: 6,
                                border: "1px solid var(--border)",
                                background: "transparent",
                                color: "var(--text-muted)",
                                cursor: "pointer",
                                fontSize: "0.75rem",
                              }}
                            >
                              Cancel
                            </button>
                          </>
                        )}
                        {entry.status === "notified" && (
                          <button
                            onClick={() => handleStatusChange(entry.id, "booked")}
                            style={{
                              padding: "0.3rem 0.6rem",
                              borderRadius: 6,
                              border: "1px solid var(--green)",
                              background: "transparent",
                              color: "var(--green)",
                              cursor: "pointer",
                              fontSize: "0.75rem",
                            }}
                          >
                            Mark Booked
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(entry.id)}
                          style={{
                            padding: "0.3rem 0.6rem",
                            borderRadius: 6,
                            border: "1px solid var(--red)",
                            background: "transparent",
                            color: "var(--red)",
                            cursor: "pointer",
                            fontSize: "0.75rem",
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
