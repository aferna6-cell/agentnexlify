import { useState } from "react";
import { fetchOsRunTrace } from "../../utils/api/os";

// ---------------------------------------------------------------------------
// RunTraceDrawer — "why did the agent do that?" (enterprise-audit item 1).
// Self-contained link + overlay: renders a small "View run trace" affordance;
// on click fetches GET /agent-runs/{id}/trace and shows the run timeline —
// routing decision, thought process, model calls, guardrail flags, action
// outcomes. Kept self-contained so DeliverablePanel only adds two lines.
// ---------------------------------------------------------------------------

const overlayStyle = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.55)",
  zIndex: 90,
  display: "flex",
  justifyContent: "flex-end",
};

const panelStyle = {
  width: 420,
  maxWidth: "100%",
  height: "100%",
  overflowY: "auto",
  background: "var(--bg-primary)",
  borderLeft: "1px solid var(--border)",
  padding: 20,
  boxSizing: "border-box",
};

const sectionTitleStyle = {
  fontSize: "0.72rem",
  color: "var(--text-muted)",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  margin: "16px 0 6px",
};

const rowStyle = {
  fontSize: "0.82rem",
  color: "var(--text-secondary)",
  padding: "4px 0",
  borderBottom: "1px solid var(--border)",
  overflowWrap: "anywhere",
};

function Section({ title, children }) {
  return (
    <div>
      <div style={sectionTitleStyle}>{title}</div>
      {children}
    </div>
  );
}

function Empty({ label }) {
  return (
    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{label}</div>
  );
}

export default function RunTraceDrawer({ token, runId }) {
  const [open, setOpen] = useState(false);
  const [trace, setTrace] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const show = async () => {
    setOpen(true);
    setLoading(true);
    setError("");
    try {
      setTrace(await fetchOsRunTrace(token, runId));
    } catch (err) {
      setError(err.message || "Failed to load trace");
    } finally {
      setLoading(false);
    }
  };

  if (!runId) return null;

  const run = trace?.run || {};
  const guardFlags = run?.deliverable?.guard_flags || [];
  const thought = Array.isArray(run.thought_process) ? run.thought_process : [];

  return (
    <>
      <button
        onClick={show}
        style={{
          background: "none",
          border: "none",
          color: "var(--text-secondary)",
          cursor: "pointer",
          fontSize: "0.78rem",
          textDecoration: "underline",
          alignSelf: "flex-start",
          padding: 0,
        }}
      >
        View run trace
      </button>
      {open && (
        <div style={overlayStyle} onClick={() => setOpen(false)}>
          <div style={panelStyle} onClick={(e) => e.stopPropagation()}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <h3
                style={{
                  margin: 0,
                  fontSize: "1rem",
                  color: "var(--text-primary, #f1f5f9)",
                }}
              >
                Run trace
              </h3>
              <button
                onClick={() => setOpen(false)}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  fontSize: "1rem",
                }}
              >
                Close
              </button>
            </div>

            {loading && <Empty label="Loading trace…" />}
            {error && (
              <div style={{ color: "#f87171", fontSize: "0.85rem" }}>{error}</div>
            )}

            {trace && !loading && (
              <>
                <Section title="Run">
                  <div style={rowStyle}>
                    {run.agent_name || "unknown"} — {run.status || "?"}
                    {run.deliverable_status ? ` · draft ${run.deliverable_status}` : ""}
                  </div>
                  {guardFlags.length > 0 && (
                    <div style={{ ...rowStyle, color: "#fbbf24" }}>
                      Held by outbound guard: {guardFlags.join(", ")}
                    </div>
                  )}
                </Section>

                <Section title="Routing">
                  {(trace.routing_decisions || []).length === 0 ? (
                    <Empty label="No routing decisions recorded" />
                  ) : (
                    trace.routing_decisions.map((d, i) => (
                      <div key={i} style={rowStyle}>
                        {d.classifier}: chose {d.chosen_agent || d.decision}
                        {typeof d.confidence === "number"
                          ? ` (confidence ${d.confidence})`
                          : ""}
                      </div>
                    ))
                  )}
                </Section>

                <Section title="Thinking">
                  {thought.length === 0 ? (
                    <Empty label="No trace steps recorded" />
                  ) : (
                    thought.map((step, i) => (
                      <div key={i} style={rowStyle}>
                        {typeof step === "string"
                          ? step
                          : step?.summary || step?.step || JSON.stringify(step)}
                      </div>
                    ))
                  )}
                </Section>

                <Section title="Model calls">
                  {(trace.model_calls || []).length === 0 ? (
                    <Empty label="No model calls recorded" />
                  ) : (
                    trace.model_calls.map((c, i) => (
                      <div key={i} style={rowStyle}>
                        {c.purpose} · {c.model} · {c.input_tokens || 0} in /{" "}
                        {c.output_tokens || 0} out{c.ok === false ? " · FAILED" : ""}
                      </div>
                    ))
                  )}
                </Section>

                <Section title="Actions">
                  {(trace.action_runs || []).length === 0 ? (
                    <Empty label="No actions fired" />
                  ) : (
                    trace.action_runs.map((a, i) => (
                      <div key={i} style={rowStyle}>
                        {a.action_type} — {a.status}
                      </div>
                    ))
                  )}
                </Section>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
