import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { getCalls, getCallStats, getCall } from "../utils/api/calls";
import SkeletonLoader from "../components/SkeletonLoader";

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

const overlayStyle = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
};

const modalStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  borderRadius: 16,
  padding: "28px 32px",
  width: "90%",
  maxWidth: 700,
  maxHeight: "90vh",
  overflowY: "auto",
  border: "1px solid var(--border)",
};

const selectStyle = {
  padding: "8px 12px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--bg-primary)",
  color: "var(--text-primary)",
  fontSize: "0.85rem",
};

const STATUS_STYLES = {
  completed: { label: "Completed", color: "var(--green)", bg: "var(--green-dim)" },
  "in-progress": {
    label: "In progress",
    color: "var(--yellow, #f59e0b)",
    bg: "rgba(245,158,11,0.15)",
  },
  "no-answer": { label: "Missed", color: "#f87171", bg: "rgba(248,113,113,0.15)" },
  busy: { label: "Busy", color: "#f87171", bg: "rgba(248,113,113,0.15)" },
  failed: { label: "Failed", color: "#f87171", bg: "rgba(248,113,113,0.15)" },
};

function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] || {
    label: status || "Unknown",
    color: "var(--text-muted)",
    bg: "var(--bg-primary)",
  };
  return (
    <span
      style={{
        padding: "2px 10px",
        borderRadius: 12,
        fontSize: "0.75rem",
        fontWeight: 600,
        color: s.color,
        background: s.bg,
        whiteSpace: "nowrap",
      }}
    >
      {s.label}
    </span>
  );
}

function formatDate(d) {
  if (!d) return "\u2014";
  return new Date(d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return "\u2014";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function StatCard({ label, value }) {
  return (
    <div style={{ ...cardStyle, padding: "18px 24px", flex: 1, minWidth: 150 }}>
      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{label}</div>
      <div
        style={{
          fontSize: "1.6rem",
          fontWeight: 700,
          color: "var(--text-primary)",
          marginTop: 4,
        }}
      >
        {value}
      </div>
    </div>
  );
}

function TranscriptTurn({ turn }) {
  const isCaller = (turn.role || turn.speaker) === "user" || turn.speaker === "caller";
  return (
    <div style={{ marginBottom: 10 }}>
      <span
        style={{
          fontSize: "0.72rem",
          fontWeight: 700,
          color: isCaller ? "var(--accent, #6366f1)" : "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
        }}
      >
        {isCaller ? "Caller" : "AI"}
      </span>
      <p
        style={{
          margin: "2px 0 0",
          fontSize: "0.88rem",
          color: "var(--text-primary)",
          whiteSpace: "pre-wrap",
        }}
      >
        {turn.content || turn.text || ""}
      </p>
    </div>
  );
}

function CallDetailModal({ call, onClose }) {
  if (!call) return null;
  const transcript = Array.isArray(call.transcript) ? call.transcript : [];
  return (
    <div style={overlayStyle} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={modalStyle}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: 16,
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: "1.2rem", color: "var(--text-primary)" }}>
              Call from {call.caller_phone}
            </h2>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", margin: "4px 0 0" }}>
              {formatDate(call.created_at)} · {formatDuration(call.duration_seconds)}
              {call.sentiment ? ` · ${call.sentiment}` : ""}
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              fontSize: "1.3rem",
              cursor: "pointer",
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        {call.summary && (
          <div style={{ marginBottom: 18 }}>
            <h3 style={{ fontSize: "0.85rem", color: "var(--text-muted)", margin: "0 0 6px" }}>
              Summary
            </h3>
            <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--text-primary)" }}>
              {call.summary}
            </p>
          </div>
        )}

        {call.action_taken && (
          <div style={{ marginBottom: 18 }}>
            <h3 style={{ fontSize: "0.85rem", color: "var(--text-muted)", margin: "0 0 6px" }}>
              Action taken
            </h3>
            <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--text-primary)" }}>
              {call.action_taken}
            </p>
          </div>
        )}

        {call.recording_url && (
          <div style={{ marginBottom: 18 }}>
            <h3 style={{ fontSize: "0.85rem", color: "var(--text-muted)", margin: "0 0 6px" }}>
              Recording
            </h3>
            <audio controls src={call.recording_url} style={{ width: "100%" }} />
          </div>
        )}

        <div>
          <h3 style={{ fontSize: "0.85rem", color: "var(--text-muted)", margin: "0 0 10px" }}>
            Transcript
          </h3>
          {transcript.length === 0 ? (
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", margin: 0 }}>
              No transcript available for this call.
            </p>
          ) : (
            transcript.map((turn, i) => <TranscriptTurn key={i} turn={turn} />)
          )}
        </div>
      </div>
    </div>
  );
}

export default function CallsPage() {
  const { user, token } = useAuth();
  const tenantId = user?.tenantId;

  const [stats, setStats] = useState(null);
  const [calls, setCalls] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [detail, setDetail] = useState(null);

  const PER_PAGE = 25;

  const load = useCallback(async () => {
    if (!tenantId || !token) return;
    setLoading(true);
    setError(null);
    try {
      const [listRes, statsRes] = await Promise.all([
        getCalls(tenantId, token, {
          status: statusFilter || undefined,
          page,
          perPage: PER_PAGE,
        }),
        getCallStats(tenantId, token),
      ]);
      setCalls(listRes.calls || []);
      setTotal(listRes.total || 0);
      setStats(statsRes);
    } catch (err) {
      setError(err.message || "Failed to load calls");
    } finally {
      setLoading(false);
    }
  }, [tenantId, token, statusFilter, page]);

  useEffect(() => {
    load();
  }, [load]);

  const openDetail = async (call) => {
    setDetail(call);
    // Refresh full record - list rows can lag summary/transcript enrichment
    try {
      const full = await getCall(tenantId, call.id, token);
      setDetail(full);
    } catch {
      // keep the list-row version
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));

  return (
    <div style={{ padding: "24px 28px", maxWidth: 1100, margin: "0 auto" }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ margin: 0, fontSize: "1.5rem", color: "var(--text-primary)" }}>Calls</h1>
        <p style={{ margin: "6px 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>
          Every call your AI staff answered or transcribed, with summaries and transcripts.
        </p>
      </div>

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 20 }}>
        <StatCard label="Total calls" value={stats ? stats.total_calls : "\u2014"} />
        <StatCard label="Missed calls" value={stats ? stats.missed_calls : "\u2014"} />
        <StatCard
          label="Avg duration"
          value={stats ? formatDuration(stats.avg_duration_seconds) : "\u2014"}
        />
        <StatCard label="Calls today" value={stats ? stats.calls_today : "\u2014"} />
        {stats && stats.included_minutes > 0 && (
          <StatCard
            label="AI minutes this month"
            value={`${stats.minutes_this_month} / ${stats.included_minutes}`}
          />
        )}
      </div>

      <div style={cardStyle}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 16,
          }}
        >
          <h2 style={{ margin: 0, fontSize: "1.05rem", color: "var(--text-primary)" }}>
            Call history
          </h2>
          <select
            aria-label="Filter by status"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            style={selectStyle}
          >
            <option value="">All statuses</option>
            <option value="completed">Completed</option>
            <option value="in-progress">In progress</option>
            <option value="no-answer">Missed</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        {error && (
          <p style={{ color: "#f87171", fontSize: "0.85rem" }}>
            {error}{" "}
            <button
              onClick={load}
              style={{
                background: "none",
                border: "none",
                color: "var(--accent, #6366f1)",
                cursor: "pointer",
                textDecoration: "underline",
                fontSize: "0.85rem",
              }}
            >
              Retry
            </button>
          </p>
        )}

        {loading ? (
          <SkeletonLoader />
        ) : calls.length === 0 && !error ? (
          <div style={{ textAlign: "center", padding: "40px 20px" }}>
            <p style={{ color: "var(--text-primary)", fontWeight: 600, margin: "0 0 6px" }}>
              No calls yet
            </p>
            <p
              style={{
                color: "var(--text-muted)",
                fontSize: "0.88rem",
                margin: 0,
                maxWidth: 420,
                marginInline: "auto",
              }}
            >
              When customers call your business number, your AI staff answers (or takes a
              voicemail), and every call shows up here with a transcript and summary. Turn on AI
              phone answering under Settings → Messaging.
            </p>
          </div>
        ) : (
          <>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
                <thead>
                  <tr
                    style={{
                      textAlign: "left",
                      color: "var(--text-muted)",
                      fontSize: "0.78rem",
                    }}
                  >
                    <th style={{ padding: "8px 10px" }}>Caller</th>
                    <th style={{ padding: "8px 10px" }}>Status</th>
                    <th style={{ padding: "8px 10px" }}>Duration</th>
                    <th style={{ padding: "8px 10px" }}>Summary</th>
                    <th style={{ padding: "8px 10px" }}>When</th>
                  </tr>
                </thead>
                <tbody>
                  {calls.map((call) => (
                    <tr
                      key={call.id}
                      onClick={() => openDetail(call)}
                      style={{
                        borderTop: "1px solid var(--border)",
                        cursor: "pointer",
                      }}
                    >
                      <td
                        style={{
                          padding: "10px",
                          color: "var(--text-primary)",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {call.caller_phone}
                      </td>
                      <td style={{ padding: "10px" }}>
                        <StatusBadge status={call.status} />
                      </td>
                      <td style={{ padding: "10px", color: "var(--text-secondary)" }}>
                        {formatDuration(call.duration_seconds)}
                      </td>
                      <td
                        style={{
                          padding: "10px",
                          color: "var(--text-secondary)",
                          maxWidth: 340,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {call.summary || "\u2014"}
                      </td>
                      <td
                        style={{
                          padding: "10px",
                          color: "var(--text-muted)",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {formatDate(call.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  alignItems: "center",
                  gap: 12,
                  marginTop: 14,
                  fontSize: "0.85rem",
                  color: "var(--text-muted)",
                }}
              >
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  style={{ ...selectStyle, cursor: page <= 1 ? "default" : "pointer" }}
                >
                  Prev
                </button>
                <span>
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  style={{ ...selectStyle, cursor: page >= totalPages ? "default" : "pointer" }}
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>

      <CallDetailModal call={detail} onClose={() => setDetail(null)} />
    </div>
  );
}
