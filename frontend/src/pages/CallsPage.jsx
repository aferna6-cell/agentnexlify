import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  fetchCalls,
  fetchCallDetail,
  fetchCallStats,
} from "../utils/api/calls";

const STATUS_FILTERS = ["all", "completed", "missed", "voicemail", "in_progress"];

const STATUS_COLORS = {
  completed: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  missed: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
  voicemail: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  in_progress: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
};

const STATUS_LABELS = {
  completed: "Completed",
  missed: "Missed",
  voicemail: "Voicemail",
  in_progress: "In Progress",
};

const SENTIMENT_COLORS = {
  positive: { color: "#22c55e", bg: "rgba(34,197,94,0.1)", label: "Positive" },
  neutral: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)", label: "Neutral" },
  negative: { color: "#ef4444", bg: "rgba(239,68,68,0.1)", label: "Negative" },
};

const SPEAKER_COLORS = {
  caller: "#3b82f6",
  assistant: "#22c55e",
};

function formatTranscriptTimestamp(seconds) {
  if (seconds === null || seconds === undefined) return "";
  const s = Number(seconds);
  if (isNaN(s)) return "";
  const m = Math.floor(s / 60);
  const rem = Math.floor(s % 60);
  return `${String(m).padStart(2, "0")}:${String(rem).padStart(2, "0")}`;
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function formatTime(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return "--";
  const s = Number(seconds);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  if (m < 60) return `${m}m ${rem}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function CallsPage() {
  const { user, token } = useAuth();
  const [calls, setCalls] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter
  const [activeFilter, setActiveFilter] = useState("all");

  // Detail modal
  const [detailCall, setDetailCall] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const params = {};
      if (activeFilter !== "all") params.status = activeFilter;
      const [callsData, statsData] = await Promise.all([
        fetchCalls(user.tenantId, token, params),
        fetchCallStats(user.tenantId, token),
      ]);
      setCalls(callsData.calls || callsData || []);
      setStats(statsData);
      setError(null);
    } catch (err) {
      console.warn("Failed to load calls:", err.message);
      setError(err.message || "Failed to load calls");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, activeFilter]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  const openDetail = async (call) => {
    setDetailCall(call);
    // Try to load full detail
    setDetailLoading(true);
    try {
      const detail = await fetchCallDetail(user.tenantId, token, call.id);
      setDetailCall(detail);
    } catch (err) {
      // If detail fetch fails, keep the list data
      console.warn("Failed to load call detail:", err.message);
    } finally {
      setDetailLoading(false);
    }
  };

  if (loading) return <SkeletonLoader />;

  const totalCalls = stats?.total_calls ?? calls.length;
  const missedCalls = stats?.missed_calls ?? calls.filter((c) => c.status === "missed").length;
  const avgDuration = stats?.avg_duration ?? 0;
  const callsToday = stats?.calls_today ?? 0;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Calls</h1>
          <p>Track and review incoming and outgoing phone calls</p>
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
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
            }}
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 12,
          marginBottom: 24,
        }}
      >
        {[
          { label: "Total Calls", value: totalCalls, color: "var(--text-secondary)" },
          { label: "Missed Calls", value: missedCalls, color: "#ef4444" },
          { label: "Avg Duration", value: formatDuration(avgDuration), color: "#3b82f6" },
          { label: "Calls Today", value: callsToday, color: "#22c55e" },
        ].map((card) => (
          <div
            key={card.label}
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
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

      {/* Status Filter Tabs */}
      <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
        {STATUS_FILTERS.map((s) => {
          const isActive = activeFilter === s;
          return (
            <button
              key={s}
              onClick={() => setActiveFilter(s)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border: isActive
                  ? "1px solid var(--accent)"
                  : "1px solid var(--border)",
                background: isActive ? "var(--accent-dim)" : "var(--bg-secondary)",
                color: isActive ? "var(--accent)" : "var(--text-secondary)",
                cursor: "pointer",
                fontSize: "0.85rem",
                fontWeight: isActive ? 600 : 400,
                transition: "all 0.15s ease",
              }}
            >
              {s === "all" ? "All" : STATUS_LABELS[s] || s}
            </button>
          );
        })}
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

      {/* Call List */}
      {calls.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>
            {activeFilter !== "all" ? "No calls match this filter" : "No calls yet"}
          </div>
          <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
            {activeFilter !== "all"
              ? "Try selecting a different status filter to see other calls."
              : "When your AI answering service is set up, incoming and outgoing calls will appear here with transcripts, summaries, and call details."}
          </p>
          {activeFilter !== "all" && (
            <button
              className="btn-primary"
              onClick={() => setActiveFilter("all")}
              style={{
                background: "transparent",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
              }}
            >
              Clear Filter
            </button>
          )}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {calls.map((call) => {
            const statusColor = STATUS_COLORS[call.status] || STATUS_COLORS.completed;

            return (
              <div
                key={call.id}
                style={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  padding: 16,
                  borderLeft: `4px solid ${statusColor.color}`,
                  cursor: "pointer",
                  transition: "background 0.15s ease",
                }}
                onClick={() => openDetail(call)}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: 8,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1, minWidth: 200 }}>
                    {/* Phone icon placeholder */}
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: "50%",
                        background: statusColor.bg,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={statusColor.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                      </svg>
                    </div>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                        <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>
                          {call.caller_name || call.caller_phone || call.phone || "Unknown Caller"}
                        </span>
                        <span
                          style={{
                            display: "inline-block",
                            padding: "2px 8px",
                            borderRadius: 4,
                            fontSize: "0.7rem",
                            fontWeight: 600,
                            color: statusColor.color,
                            background: statusColor.bg,
                          }}
                        >
                          {STATUS_LABELS[call.status] || call.status}
                        </span>
                      </div>
                      {call.summary && (
                        <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: 1.3 }}>
                          {call.summary.length > 100 ? call.summary.slice(0, 100) + "..." : call.summary}
                        </div>
                      )}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    <span>{formatDuration(call.duration || call.duration_seconds)}</span>
                    <span>{call.created_at ? `${formatTime(call.created_at)} ${formatDate(call.created_at)}` : ""}</span>
                    <span style={{ fontSize: "0.75rem" }}>{timeAgo(call.created_at)}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detail Modal */}
      {detailCall && (
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
          onClick={() => setDetailCall(null)}
        >
          <div
            style={{
              background: "var(--bg-primary)",
              borderRadius: 12,
              padding: 24,
              width: "90%",
              maxWidth: 640,
              maxHeight: "80vh",
              overflowY: "auto",
              border: "1px solid var(--border)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {detailLoading ? (
              <div style={{ textAlign: "center", padding: "30px 0", color: "var(--text-muted)" }}>
                Loading call details...
              </div>
            ) : (
              <>
                {/* Header with caller name, status badge, and sentiment badge */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
                  <div>
                    <h3 style={{ marginBottom: 6 }}>
                      {detailCall.caller_name || detailCall.caller_phone || detailCall.phone || "Unknown Caller"}
                    </h3>
                    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "3px 10px",
                          borderRadius: 4,
                          fontSize: "0.75rem",
                          fontWeight: 600,
                          color: (STATUS_COLORS[detailCall.status] || STATUS_COLORS.completed).color,
                          background: (STATUS_COLORS[detailCall.status] || STATUS_COLORS.completed).bg,
                        }}
                      >
                        {STATUS_LABELS[detailCall.status] || detailCall.status}
                      </span>
                      {detailCall.sentiment && SENTIMENT_COLORS[detailCall.sentiment] && (
                        <span
                          style={{
                            display: "inline-block",
                            padding: "3px 10px",
                            borderRadius: 4,
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            color: SENTIMENT_COLORS[detailCall.sentiment].color,
                            background: SENTIMENT_COLORS[detailCall.sentiment].bg,
                          }}
                        >
                          {SENTIMENT_COLORS[detailCall.sentiment].label}
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => setDetailCall(null)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                      fontSize: "1.2rem",
                    }}
                  >
                    x
                  </button>
                </div>

                {/* Call info grid */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 12,
                    marginBottom: 16,
                  }}
                >
                  {[
                    { label: "Phone", value: detailCall.caller_phone || detailCall.phone || "--" },
                    { label: "Duration", value: formatDuration(detailCall.duration || detailCall.duration_seconds) },
                    { label: "Date", value: detailCall.created_at ? formatDate(detailCall.created_at) : "--" },
                    { label: "Time", value: detailCall.created_at ? formatTime(detailCall.created_at) : "--" },
                    { label: "Direction", value: detailCall.direction || "--" },
                    { label: "Status", value: STATUS_LABELS[detailCall.status] || detailCall.status || "--" },
                  ].map((item) => (
                    <div key={item.label}>
                      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", marginBottom: 2 }}>
                        {item.label}
                      </div>
                      <div style={{ fontSize: "0.9rem", color: "var(--text-primary)" }}>{item.value}</div>
                    </div>
                  ))}
                </div>

                {/* Summary */}
                {detailCall.summary ? (
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", marginBottom: 4 }}>
                      Summary
                    </div>
                    <div
                      style={{
                        fontSize: "0.9rem",
                        color: "var(--text-secondary)",
                        lineHeight: 1.5,
                        background: "var(--bg-secondary)",
                        border: "1px solid var(--border)",
                        borderRadius: 8,
                        padding: 12,
                      }}
                    >
                      {detailCall.summary}
                    </div>
                  </div>
                ) : null}

                {/* Transcript - chat log style */}
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", marginBottom: 4 }}>
                    Transcript
                  </div>
                  {(() => {
                    const transcript = detailCall.transcript;
                    // Handle JSONB array transcript
                    if (Array.isArray(transcript) && transcript.length > 0) {
                      return (
                        <div
                          style={{
                            background: "var(--bg-secondary)",
                            border: "1px solid var(--border)",
                            borderRadius: 8,
                            padding: 16,
                            maxHeight: 320,
                            overflowY: "auto",
                            display: "flex",
                            flexDirection: "column",
                            gap: 12,
                          }}
                        >
                          {transcript.map((entry, idx) => {
                            const speaker = (entry.speaker || entry.role || "unknown").toLowerCase();
                            const isCaller = speaker === "caller" || speaker === "user" || speaker === "customer";
                            const speakerColor = isCaller ? SPEAKER_COLORS.caller : SPEAKER_COLORS.assistant;
                            const speakerLabel = isCaller ? "Caller" : "Assistant";
                            const timestamp = formatTranscriptTimestamp(entry.timestamp ?? entry.time ?? entry.start);
                            const text = entry.text || entry.content || entry.message || "";

                            return (
                              <div
                                key={idx}
                                style={{
                                  display: "flex",
                                  flexDirection: "column",
                                  alignItems: isCaller ? "flex-start" : "flex-end",
                                  maxWidth: "85%",
                                  alignSelf: isCaller ? "flex-start" : "flex-end",
                                }}
                              >
                                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                                  <span
                                    style={{
                                      fontSize: "0.7rem",
                                      fontWeight: 600,
                                      color: speakerColor,
                                    }}
                                  >
                                    {speakerLabel}
                                  </span>
                                  {timestamp && (
                                    <span style={{ fontSize: "0.65rem", color: "var(--text-muted)" }}>
                                      {timestamp}
                                    </span>
                                  )}
                                </div>
                                <div
                                  style={{
                                    background: isCaller
                                      ? "rgba(59,130,246,0.1)"
                                      : "rgba(34,197,94,0.1)",
                                    border: `1px solid ${isCaller ? "rgba(59,130,246,0.2)" : "rgba(34,197,94,0.2)"}`,
                                    borderRadius: isCaller ? "2px 12px 12px 12px" : "12px 2px 12px 12px",
                                    padding: "8px 12px",
                                    fontSize: "0.85rem",
                                    color: "var(--text-primary)",
                                    lineHeight: 1.5,
                                  }}
                                >
                                  {text}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      );
                    }

                    // Handle plain string transcript (legacy format)
                    if (typeof transcript === "string" && transcript.trim()) {
                      return (
                        <div
                          style={{
                            fontSize: "0.85rem",
                            color: "var(--text-secondary)",
                            lineHeight: 1.6,
                            background: "var(--bg-secondary)",
                            border: "1px solid var(--border)",
                            borderRadius: 8,
                            padding: 12,
                            maxHeight: 240,
                            overflowY: "auto",
                            whiteSpace: "pre-wrap",
                          }}
                        >
                          {transcript}
                        </div>
                      );
                    }

                    // Empty / null transcript
                    return (
                      <div
                        style={{
                          background: "var(--bg-secondary)",
                          border: "1px solid var(--border)",
                          borderRadius: 8,
                          padding: "20px 16px",
                          textAlign: "center",
                          color: "var(--text-muted)",
                          fontSize: "0.85rem",
                        }}
                      >
                        Transcript not yet available.
                        {detailCall.status === "in_progress" && " The call is still in progress."}
                        {detailCall.status === "missed" && " Missed calls do not have transcripts."}
                      </div>
                    );
                  })()}
                </div>

                {/* Action Taken */}
                {detailCall.action_taken && (
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", marginBottom: 4 }}>
                      Action Taken
                    </div>
                    <div
                      style={{
                        fontSize: "0.9rem",
                        color: "var(--text-secondary)",
                        lineHeight: 1.5,
                        background: "rgba(139,92,246,0.06)",
                        border: "1px solid rgba(139,92,246,0.15)",
                        borderRadius: 8,
                        padding: 12,
                      }}
                    >
                      {detailCall.action_taken}
                    </div>
                  </div>
                )}

                {/* Recording link */}
                {detailCall.recording_url && (
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", marginBottom: 4 }}>
                      Recording
                    </div>
                    <a
                      href={detailCall.recording_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "8px 16px",
                        background: "var(--accent-dim)",
                        border: "1px solid var(--accent)",
                        borderRadius: 6,
                        color: "var(--accent)",
                        textDecoration: "none",
                        fontSize: "0.85rem",
                        fontWeight: 600,
                      }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polygon points="5 3 19 12 5 21 5 3" />
                      </svg>
                      Play Recording
                    </a>
                  </div>
                )}

                <div style={{ display: "flex", justifyContent: "flex-end", borderTop: "1px solid var(--border)", paddingTop: 16 }}>
                  <button onClick={() => setDetailCall(null)} className="btn-primary">
                    Close
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
