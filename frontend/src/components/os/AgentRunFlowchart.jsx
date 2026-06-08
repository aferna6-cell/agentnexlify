/**
 * Agent OS run flowchart - P0.
 *
 * Renders an os_agent_runs row's thought_process array as a vertical
 * step timeline so the owner can watch the worker agent reason through
 * a task.
 *
 * Tolerates two trace shapes:
 *   v1 (legacy worker): {step, label, status: "done"|"running", detail, at}
 *   v2 (agent-service):  {ordinal, step, status: "work"|"completed", description, dataSnapshot}
 * Primary text prefers `description` (v2) then `label` (v1); status colors
 * cover both vocabularies so old and new runs both render.
 */
import React from "react";

const STEP_COLORS = {
  done: "#22c55e",
  completed: "#22c55e",
  running: "var(--accent)",
  work: "var(--accent)",
  failed: "#ef4444",
  fallback: "#f59e0b",
  pending: "var(--text-muted)",
};

const RUN_STATUS = {
  queued: {
    label: "Queued",
    color: "var(--text-muted)",
    bg: "var(--hover-overlay)",
  },
  running: {
    label: "Running",
    color: "var(--accent)",
    bg: "var(--accent-dim)",
  },
  succeeded: {
    label: "Completed",
    color: "#22c55e",
    bg: "rgba(34,197,94,0.12)",
  },
  failed: { label: "Failed", color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
};

function stepTime(at) {
  if (!at) return "";
  const d = new Date(at);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function AgentRunFlowchart({ run }) {
  if (!run) return null;

  const steps = Array.isArray(run.thought_process) ? run.thought_process : [];
  const status = run.status || "queued";
  const meta = RUN_STATUS[status] || RUN_STATUS.queued;
  const inFlight = status === "queued" || status === "running";

  // F-03/F-06: routing transparency. confidence is 0..1 from the engine; show
  // it as a percent next to the chosen agent and the routing model.
  const routing = run.routing || null;
  const confPct =
    routing && routing.confidence != null
      ? Math.round(routing.confidence <= 1 ? routing.confidence * 100 : routing.confidence)
      : null;
  const routingBits = routing
    ? [
        `Routed to ${routing.chosen_agent || routing.decision || "agent"}`,
        confPct != null ? `${confPct}%` : null,
        routing.model || null,
      ].filter(Boolean)
    : [];

  return (
    <div
      style={{
        background: "var(--bg-secondary)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        padding: 14,
        marginTop: 8,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          marginBottom: steps.length ? 12 : 0,
        }}
      >
        <span
          style={{
            fontSize: "0.8rem",
            fontWeight: 600,
            color: "var(--text-secondary)",
          }}
        >
          {run.agent_name || "Worker agent"}
        </span>
        <span
          style={{
            padding: "2px 9px",
            borderRadius: 999,
            fontSize: "0.7rem",
            fontWeight: 600,
            color: meta.color,
            background: meta.bg,
          }}
        >
          {meta.label}
        </span>
      </div>

      {routing && (
        <div
          style={{
            fontSize: "0.72rem",
            color: "var(--text-muted)",
            marginBottom: steps.length ? 10 : 0,
          }}
        >
          {routingBits.join(" · ")}
        </div>
      )}

      {steps.length === 0 && inFlight && (
        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
          Agent is starting up...
        </div>
      )}

      {steps.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column" }}>
          {steps.map((step, idx) => {
            const dot = STEP_COLORS[step.status] || STEP_COLORS.pending;
            const last = idx === steps.length - 1;
            return (
              <div key={step.ordinal ?? idx} style={{ display: "flex", gap: 10 }}>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      width: 11,
                      height: 11,
                      borderRadius: "50%",
                      background: dot,
                      flexShrink: 0,
                      marginTop: 3,
                    }}
                  />
                  {!last && (
                    <span
                      style={{
                        width: 2,
                        flex: 1,
                        minHeight: 16,
                        background: "var(--border)",
                      }}
                    />
                  )}
                </div>
                <div style={{ paddingBottom: last ? 0 : 14, minWidth: 0 }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "baseline",
                      gap: 8,
                      flexWrap: "wrap",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "0.82rem",
                        fontWeight: 600,
                        color: "var(--text-primary)",
                      }}
                    >
                      {step.description || step.label || `Step ${idx + 1}`}
                    </span>
                    {step.at && (
                      <span
                        style={{
                          fontSize: "0.7rem",
                          color: "var(--text-muted)",
                        }}
                      >
                        {stepTime(step.at)}
                      </span>
                    )}
                  </div>
                  {step.detail && (
                    <div
                      style={{
                        fontSize: "0.78rem",
                        color: "var(--text-secondary)",
                        lineHeight: 1.5,
                        marginTop: 2,
                      }}
                    >
                      {step.detail}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {status === "failed" && run.error_detail && (
        <div
          style={{
            marginTop: 10,
            padding: "8px 12px",
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 8,
            fontSize: "0.78rem",
            color: "#ef4444",
          }}
        >
          {run.error_detail}
        </div>
      )}
    </div>
  );
}
