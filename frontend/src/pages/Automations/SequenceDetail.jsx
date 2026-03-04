const triggerLabels = {
  new_lead: "New Lead",
  lead_stage_change: "Stage Change",
  no_response_24h: "No Response",
};

const actionLabels = {
  email_sent: "Email Sent",
  email_failed: "Email Failed",
  skipped: "Skipped",
};

const actionColors = {
  email_sent: "var(--green)",
  email_failed: "var(--red)",
  skipped: "var(--yellow)",
};

function formatDelay(minutes) {
  if (minutes === 0) return "Immediately";
  if (minutes < 60) return `${minutes}m`;
  if (minutes < 1440) return `${Math.round(minutes / 60)}h`;
  return `${Math.round(minutes / 1440)}d`;
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
  return `${days}d ago`;
}

const overlayStyle = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
  animation: "fadeIn 0.2s ease",
};

const drawerStyle = {
  background: "var(--bg-card)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  width: "560px",
  maxHeight: "85vh",
  overflowY: "auto",
  padding: "28px",
  display: "flex",
  flexDirection: "column",
  gap: "24px",
};

export default function SequenceDetail({ detail, onClose }) {
  if (!detail) return null;

  const { sequence, steps, stats, recent_logs } = detail;

  return (
    <div style={overlayStyle} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={drawerStyle}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ color: "var(--text-primary)", margin: "0 0 4px", fontSize: "18px" }}>{sequence.name}</h2>
            <span style={{
              padding: "2px 8px",
              background: "var(--accent-dim)",
              color: "var(--accent)",
              borderRadius: "var(--radius-sm)",
              fontSize: "11px",
              fontWeight: 600,
            }}>
              {triggerLabels[sequence.trigger_event] || sequence.trigger_event}
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text-secondary)",
              borderRadius: "var(--radius-sm)",
              padding: "4px 10px",
              cursor: "pointer",
              fontSize: "16px",
            }}
          >
            &times;
          </button>
        </div>

        {/* Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
          {[
            { label: "Enrolled", value: stats.total_enrolled, color: "var(--text-primary)" },
            { label: "Active", value: stats.active, color: "var(--accent)" },
            { label: "Completed", value: stats.completed, color: "var(--green)" },
            { label: "Failed", value: stats.failed, color: "var(--red)" },
          ].map((s) => (
            <div key={s.label} style={{
              background: "var(--bg-primary)",
              borderRadius: "var(--radius-sm)",
              padding: "12px",
              textAlign: "center",
            }}>
              <div style={{ color: s.color, fontSize: "20px", fontWeight: 700 }}>{s.value}</div>
              <div style={{ color: "var(--text-muted)", fontSize: "11px", marginTop: "4px" }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* Steps Timeline */}
        <div>
          <h3 style={{ color: "var(--text-primary)", margin: "0 0 12px", fontSize: "14px" }}>Steps</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0" }}>
            {steps.map((step, idx) => (
              <div key={step.id || idx}>
                {/* Delay indicator */}
                {idx > 0 && (
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "8px 0 8px 20px",
                  }}>
                    <div style={{ width: "2px", height: "20px", background: "var(--border)" }} />
                    <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>
                      Wait {formatDelay(step.delay_minutes)}
                    </span>
                  </div>
                )}
                {/* Step card */}
                <div style={{
                  background: "var(--bg-primary)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-sm)",
                  padding: "14px",
                  display: "flex",
                  gap: "12px",
                  alignItems: "flex-start",
                }}>
                  <div style={{
                    width: "28px",
                    height: "28px",
                    borderRadius: "50%",
                    background: "var(--accent-dim)",
                    color: "var(--accent)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 700,
                    fontSize: "12px",
                    flexShrink: 0,
                  }}>
                    {idx + 1}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ color: "var(--text-primary)", fontWeight: 600, fontSize: "13px" }}>
                      {step.subject_template}
                    </div>
                    <div style={{
                      color: "var(--text-muted)",
                      fontSize: "12px",
                      marginTop: "4px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}>
                      {step.body_template.replace(/<[^>]*>/g, "").slice(0, 100)}
                    </div>
                    {idx === 0 && step.delay_minutes > 0 && (
                      <div style={{ color: "var(--text-muted)", fontSize: "11px", marginTop: "4px" }}>
                        Delay: {formatDelay(step.delay_minutes)}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Logs */}
        <div>
          <h3 style={{ color: "var(--text-primary)", margin: "0 0 12px", fontSize: "14px" }}>Recent Activity</h3>
          {(!recent_logs || recent_logs.length === 0) ? (
            <div style={{ color: "var(--text-muted)", fontSize: "13px", textAlign: "center", padding: "20px" }}>
              No activity yet
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "200px", overflowY: "auto" }}>
              {recent_logs.map((log) => (
                <div key={log.id} style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 12px",
                  background: "var(--bg-primary)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "12px",
                }}>
                  <span style={{ color: actionColors[log.action] || "var(--text-secondary)" }}>
                    {actionLabels[log.action] || log.action}
                  </span>
                  <span style={{ color: "var(--text-muted)" }}>{timeAgo(log.created_at)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
