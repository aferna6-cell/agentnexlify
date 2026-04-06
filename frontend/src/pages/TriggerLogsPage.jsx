import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

const inputStyle = {
  width: "100%", padding: "10px 14px", borderRadius: 8,
  border: "1px solid var(--border)", background: "var(--bg-primary",
  color: "var(--text-primary)", fontSize: "0.9rem", boxSizing: "border-box",
};

const btnSecondary = {
  background: "var(--bg-primary)", color: "var(--text-secondary)",
  border: "1px solid var(--border)", padding: "8px 16px",
  borderRadius: 8, cursor: "pointer", fontSize: "0.85rem",
};

const overlayStyle = {
  position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
  display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
};

const modalStyle = {
  background: "var(--bg-secondary, var(--card-bg))", borderRadius: 16,
  padding: "28px 32px", width: "90%", maxWidth: 700, maxHeight: "90vh",
  overflowY: "auto", border: "1px solid var(--border)",
};

const API_BASE = "/api/v1";

async function apiFetch(path, token, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

const STATUS_STYLES = {
  success: { label: "Success", color: "var(--green)", bg: "var(--green-dim)" },
  partial: { label: "Partial", color: "var(--yellow, #f59e0b)", bg: "rgba(245,158,11,0.15)" },
  failed: { label: "Failed", color: "#f87171", bg: "rgba(248,113,113,0.15)" },
};

function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.success;
  return (
    <span style={{
      padding: "2px 10px", borderRadius: 12, fontSize: "0.75rem", fontWeight: 600,
      color: s.color, background: s.bg,
    }}>{s.label}</span>
  );
}

function formatDate(d) {
  if (!d) return "\u2014";
  return new Date(d).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "numeric", minute: "2-digit",
  });
}

function LogDetailModal({ log, onClose }) {
  if (!log) return null;
  return (
    <div style={overlayStyle} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={modalStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.2rem", color: "var(--text-primary)" }}>
              Execution Details
            </h2>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", margin: "4px 0 0" }}>
              {formatDate(log.created_at)}
            </p>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "1.2rem" }}>
            &#x2715;
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 20 }}>
          <div style={{ background: "var(--bg-primary)", border: "1px solid var(--border)", borderRadius: 8, padding: "12px 16px" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4 }}>Status</div>
            <StatusBadge status={log.status} />
          </div>
          <div style={{ background: "var(--bg-primary)", border: "1px solid var(--border)", borderRadius: 8, padding: "12px 16px" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4 }}>Execution Time</div>
            <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>
              {log.execution_time_ms != null ? `${log.execution_time_ms}ms` : "--"}
            </div>
          </div>
          <div style={{ background: "var(--bg-primary)", border: "1px solid var(--border)", borderRadius: 8, padding: "12px 16px" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4 }}>Actions Run</div>
            <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>
              {log.actions_run?.length || 0}
            </div>
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: "0.9rem", color: "var(--text-primary)", margin: "0 0 8px" }}>Trigger Event</h3>
          <pre style={{
            background: "var(--bg-primary)", border: "1px solid var(--border)",
            borderRadius: 8, padding: 12, fontSize: "0.8rem", color: "var(--text-secondary)",
            overflow: "auto", maxHeight: 200, margin: 0,
          }}>
            {JSON.stringify(log.trigger_event || {}, null, 2)}
          </pre>
        </div>

        {log.actions_run?.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: "0.9rem", color: "var(--text-primary)", margin: "0 0 8px" }}>Actions Run</h3>
            <pre style={{
              background: "var(--bg-primary)", border: "1px solid var(--border)",
              borderRadius: 8, padding: 12, fontSize: "0.8rem", color: "var(--text-secondary)",
              overflow: "auto", maxHeight: 300, margin: 0,
            }}>
              {JSON.stringify(log.actions_run, null, 2)}
            </pre>
          </div>
        )}

        {log.error_message && (
          <div style={{
            background: "rgba(248,113,113,0.1)", border: "1px solid #f87171",
            borderRadius: 8, padding: "12px 16px", color: "#f87171", fontSize: "0.85rem",
          }}>
            <strong>Error:</strong> {log.error_message}
          </div>
        )}

        <div style={{ marginTop: 20, display: "flex", justifyContent: "flex-end" }}>
          <button onClick={onClose} style={btnSecondary}>Close</button>
        </div>
      </div>
    </div>
  );
}

export default function TriggerLogsPage() {
  const { user, token } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);
  const [detailLog, setDetailLog] = useState(null);
  const [ruleFilter, setRuleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [rules, setRules] = useState([]);

  const loadLogs = useCallback(async () => {
    if (!user?.tenantId || !token) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (ruleFilter) params.set("rule_id", ruleFilter);
      if (statusFilter) params.set("status", statusFilter);
      const query = params.toString() ? `?${params.toString()}` : "";
      const res = await apiFetch(`/automation-rules/${user.tenantId}/logs${query}`, token);
      setLogs(Array.isArray(res) ? res : (res.logs || res.executions || []));
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, ruleFilter, statusFilter]);

  const loadRules = useCallback(async () => {
    if (!user?.tenantId || !token) return;
    try {
      const res = await apiFetch(`/automation-rules/${user.tenantId}`, token);
      setRules(Array.isArray(res) ? res : (res.rules || []));
    } catch {
      setRules([]);
    }
  }, [user?.tenantId, token]);

  useEffect(() => { loadLogs(); }, [loadLogs]);
  useEffect(() => { loadRules(); }, [loadRules]);

  const toggleExpand = (id) => setExpandedId((prev) => prev === id ? null : id);

  if (loading && logs.length === 0) return <SkeletonLoader />;

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1200 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
            Trigger Logs
          </h1>
          <p style={{ color: "var(--text-secondary)", margin: "4px 0 0", fontSize: "0.9rem" }}>
            Automation rule execution history
          </p>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20, alignItems: "center" }}>
        <select value={ruleFilter} onChange={(e) => setRuleFilter(e.target.value)}
          style={{ ...inputStyle, width: "auto", maxWidth: 220 }}>
          <option value="">All rules</option>
          {rules.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          style={{ ...inputStyle, width: "auto", maxWidth: 160 }}>
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="partial">Partial</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Stats Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 24 }}>
        {[
          { label: "Total Executions", value: logs.length },
          { label: "Successful", value: logs.filter((l) => l.status === "success").length },
          { label: "Failed", value: logs.filter((l) => l.status === "failed").length },
        ].map((s) => (
          <div key={s.label} style={cardStyle}>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--accent)" }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Logs Table */}
      {logs.length === 0 ? (
        <div style={{ ...cardStyle, textAlign: "center", padding: "60px 20px" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>\ud83d\udd14</div>
          <h3 style={{ margin: "0 0 8px", color: "var(--text-primary)" }}>No execution logs yet</h3>
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>
            Trigger logs will appear when automation rules are executed
          </p>
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{
            width: "100%", borderCollapse: "separate", borderSpacing: 0,
            background: "var(--bg-secondary, var(--card-bg))", border: "1px solid var(--border)",
            borderRadius: 12, overflow: "hidden",
          }}>
            <thead>
              <tr>
                {["Rule", "Trigger Event", "Status", "Execution Time", "Timestamp", ""].map((h) => (
                  <th key={h} style={{
                    textAlign: "left", padding: "12px 16px", fontSize: "0.8rem",
                    color: "var(--text-muted)", fontWeight: 600, borderBottom: "1px solid var(--border)",
                    textTransform: "uppercase", letterSpacing: "0.05em",
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => {
                const isExpanded = expandedId === log.id;
                const rule = rules.find((r) => r.id === log.automation_rule_id);
                const triggerEvent = log.trigger_event || {};
                const triggerLabel = triggerEvent.trigger_type
                  ? triggerEvent.trigger_type.replace(/_/g, " ")
                  : triggerEvent.type || "—";
                return (
                  <>
                    <tr key={log.id} style={{ cursor: "pointer", transition: "background 0.15s" }}
                      onClick={() => toggleExpand(log.id)}
                      onMouseEnter={(e) => e.currentTarget.style.background = "var(--hover-overlay)"}
                      onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}>
                      <td style={{ padding: "12px 16px", color: "var(--text-primary)", fontWeight: 600 }}>
                        {rule?.name || log.rule_name || "—"}
                      </td>
                      <td style={{ padding: "12px 16px", color: "var(--text-secondary)", fontSize: "0.85rem", textTransform: "capitalize" }}>
                        {triggerLabel}
                      </td>
                      <td style={{ padding: "12px 16px" }}><StatusBadge status={log.status} /></td>
                      <td style={{ padding: "12px 16px", color: "var(--text-secondary)" }}>
                        {log.execution_time_ms != null ? `${log.execution_time_ms}ms` : "--"}
                      </td>
                      <td style={{ padding: "12px 16px", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                        {formatDate(log.created_at)}
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <button
                          onClick={(e) => { e.stopPropagation(); setDetailLog(log); }}
                          style={{ ...btnSecondary, padding: "4px 10px", fontSize: "0.75rem" }}
                        >
                          Details
                        </button>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr key={`${log.id}-expanded`}>
                        <td colSpan={6} style={{ padding: "16px", background: "var(--bg-primary)", borderBottom: "1px solid var(--border)" }}>
                          <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                            <strong>Trigger event:</strong>
                            <pre style={{
                              background: "var(--hover-overlay)", borderRadius: 6, padding: 8,
                              marginTop: 6, fontSize: "0.8rem", overflow: "auto", maxHeight: 150,
                            }}>
                              {JSON.stringify(log.trigger_event || {}, null, 2)}
                            </pre>
                          </div>
                          {log.error_message && (
                            <div style={{
                              marginTop: 8, color: "#f87171", fontSize: "0.85rem",
                              padding: "8px 12px", background: "rgba(248,113,113,0.1)", borderRadius: 6,
                            }}>
                              <strong>Error:</strong> {log.error_message}
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail Modal */}
      {detailLog && <LogDetailModal log={detailLog} onClose={() => setDetailLog(null)} />}
    </div>
  );
}