import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import {
  fetchEscalations,
  resolveEscalation,
  assignEscalation,
} from "../utils/api/escalations";
import { fetchTeamMembers } from "../utils/api/team";
import { notify } from "../utils/notify";
import SkeletonLoader from "../components/SkeletonLoader";

const STATUS_TABS = [
  { key: "open", label: "Open" },
  { key: "in_progress", label: "In Progress" },
  { key: "resolved", label: "Resolved" },
  { key: "dismissed", label: "Dismissed" },
  { key: "", label: "All" },
];

const SOURCE_BADGE = {
  widget: { label: "Widget", color: "#3b82f6", bg: "rgba(59,130,246,0.12)" },
  email: { label: "Email", color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
  sms: { label: "SMS", color: "#10b981", bg: "rgba(16,185,129,0.12)" },
  os: { label: "Agent OS", color: "#8b5cf6", bg: "rgba(139,92,246,0.12)" },
};

const PRIORITY_STYLES = {
  urgent: { label: "Urgent", color: "#ef4444", bg: "rgba(239,68,68,0.14)" },
  high: { label: "High", color: "#f97316", bg: "rgba(249,115,22,0.14)" },
  normal: { label: "Normal", color: "#3b82f6", bg: "rgba(59,130,246,0.12)" },
  low: {
    label: "Low",
    color: "var(--text-muted)",
    bg: "var(--hover-overlay)",
  },
};

function badgeStyle(cfg) {
  return {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: 10,
    fontSize: "0.7rem",
    fontWeight: 600,
    color: cfg.color,
    background: cfg.bg,
    whiteSpace: "nowrap",
  };
}

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export default function EscalationsPage({ onNavigate }) {
  const { user, token } = useAuth();
  const [escalations, setEscalations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [statusFilter, setStatusFilter] = useState("open");
  const [teamMembers, setTeamMembers] = useState([]);
  const [teamMemberMap, setTeamMemberMap] = useState({});
  const [resolvingId, setResolvingId] = useState(null);
  const [assigningId, setAssigningId] = useState(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [escRes, teamRes] = await Promise.all([
        fetchEscalations(token, statusFilter || undefined),
        user?.tenantId
          ? fetchTeamMembers(user.tenantId, token).catch(() => ({
              members: [],
            }))
          : Promise.resolve({ members: [] }),
      ]);
      const list = Array.isArray(escRes) ? escRes : escRes?.escalations || [];
      setEscalations(list);

      const members = teamRes.members || teamRes || [];
      const memberList = Array.isArray(members) ? members : [];
      setTeamMembers(memberList);
      const map = {};
      memberList.forEach((m) => {
        const id = m.id || m.team_member_id;
        if (id) map[id] = { name: m.name || m.email, email: m.email };
      });
      setTeamMemberMap(map);
      setLoadError(null);
    } catch (err) {
      console.error("Failed to load escalations", err);
      setLoadError(
        err?.message || "Couldn't load escalations. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [token, user?.tenantId, statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const handleResolve = async (id) => {
    setResolvingId(id);
    try {
      await resolveEscalation(token, id);
      setEscalations((prev) =>
        statusFilter && statusFilter !== "resolved"
          ? prev.filter((e) => e.id !== id)
          : prev.map((e) => (e.id === id ? { ...e, status: "resolved" } : e)),
      );
      notify.success("Escalation resolved.");
    } catch (err) {
      notify.error(err?.message || "Failed to resolve escalation.");
    } finally {
      setResolvingId(null);
    }
  };

  const handleAssign = async (id, assignedTo) => {
    setAssigningId(id);
    try {
      await assignEscalation(token, id, assignedTo || null);
      setEscalations((prev) =>
        prev.map((e) =>
          e.id === id ? { ...e, assigned_to: assignedTo || null } : e,
        ),
      );
    } catch (err) {
      notify.error(err?.message || "Failed to assign escalation.");
    } finally {
      setAssigningId(null);
    }
  };

  if (loading) return <SkeletonLoader />;

  const activeTabLabel =
    STATUS_TABS.find((t) => t.key === statusFilter)?.label || statusFilter;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Escalations</h1>
          <p>
            {escalations.length} escalation
            {escalations.length !== 1 ? "s" : ""}
            {statusFilter ? `: ${activeTabLabel}` : ""}
          </p>
        </div>
        <button className="btn-secondary" onClick={load}>
          Refresh
        </button>
      </div>

      <div
        style={{
          display: "flex",
          gap: 6,
          marginBottom: 16,
          flexWrap: "wrap",
        }}
      >
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.key || "all"}
            onClick={() => setStatusFilter(tab.key)}
            style={{
              padding: "6px 14px",
              borderRadius: 8,
              fontSize: "0.8rem",
              fontWeight: 600,
              cursor: "pointer",
              border:
                statusFilter === tab.key
                  ? "2px solid var(--accent)"
                  : "1px solid var(--border)",
              background:
                statusFilter === tab.key
                  ? "var(--accent-dim)"
                  : "var(--bg-secondary)",
              color:
                statusFilter === tab.key
                  ? "var(--accent)"
                  : "var(--text-secondary)",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {escalations.length === 0 ? (
        <div className="empty-card">
          <p
            style={{
              fontWeight: 600,
              color: "var(--text-primary)",
              marginBottom: 8,
            }}
          >
            {loadError
              ? "Couldn't load escalations"
              : statusFilter === "open" || !statusFilter
                ? "No open escalations: your agent is handling everything"
                : `No ${activeTabLabel.toLowerCase()} escalations`}
          </p>
          <p>
            {loadError
              ? loadError
              : "Escalations show up here when the AI agent flags a conversation for a human: a frustrated visitor, an unanswerable question, or a request outside what it can safely handle on its own."}
          </p>
          {loadError && (
            <button
              className="btn-primary"
              onClick={load}
              style={{ marginTop: 12 }}
            >
              Retry
            </button>
          )}
        </div>
      ) : (
        <div className="leads-table-wrapper">
          <table className="leads-table">
            <thead>
              <tr>
                <th>Priority</th>
                <th>Source</th>
                <th>Reason</th>
                <th>Assigned</th>
                <th>Created</th>
                <th>First Response</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {escalations.map((esc) => {
                const priority =
                  PRIORITY_STYLES[esc.priority] || PRIORITY_STYLES.normal;
                const source = SOURCE_BADGE[esc.source] || SOURCE_BADGE.widget;
                const isDone =
                  esc.status === "resolved" || esc.status === "dismissed";
                return (
                  <tr key={esc.id}>
                    <td>
                      <span style={badgeStyle(priority)}>
                        {priority.label}
                      </span>
                    </td>
                    <td>
                      <span style={badgeStyle(source)}>{source.label}</span>
                    </td>
                    <td style={{ whiteSpace: "normal", maxWidth: 320 }}>
                      {esc.reason || "-"}
                      {esc.conversation_id && onNavigate && (
                        <div>
                          <button
                            onClick={() =>
                              onNavigate("conversations", {
                                sessionId: esc.conversation_id,
                              })
                            }
                            style={{
                              background: "none",
                              border: "none",
                              color: "var(--accent)",
                              cursor: "pointer",
                              fontSize: "0.75rem",
                              padding: 0,
                              marginTop: 4,
                            }}
                          >
                            View conversation &rarr;
                          </button>
                        </div>
                      )}
                    </td>
                    <td>
                      <select
                        value={esc.assigned_to || ""}
                        onChange={(e) => handleAssign(esc.id, e.target.value)}
                        disabled={assigningId === esc.id}
                        style={{
                          padding: "4px 8px",
                          fontSize: "0.75rem",
                          borderRadius: 6,
                          border: "1px solid var(--border)",
                          background: "var(--bg-secondary)",
                          color: "var(--text-primary)",
                          cursor: assigningId === esc.id ? "wait" : "pointer",
                        }}
                      >
                        <option value="">Unassigned</option>
                        {teamMembers.map((m) => {
                          const id = m.id || m.team_member_id;
                          return (
                            <option key={id} value={id}>
                              {m.name || m.email}
                            </option>
                          );
                        })}
                      </select>
                    </td>
                    <td>{timeAgo(esc.created_at)}</td>
                    <td>
                      {esc.first_response_at
                        ? timeAgo(esc.first_response_at)
                        : "-"}
                    </td>
                    <td>
                      {isDone ? (
                        <span
                          style={{
                            color: "var(--text-muted)",
                            fontSize: "0.75rem",
                            textTransform: "capitalize",
                          }}
                        >
                          {esc.status}
                        </span>
                      ) : (
                        <button
                          className="btn-sm"
                          onClick={() => handleResolve(esc.id)}
                          disabled={resolvingId === esc.id}
                        >
                          {resolvingId === esc.id ? "Resolving..." : "Resolve"}
                        </button>
                      )}
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
