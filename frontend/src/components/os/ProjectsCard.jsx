import { useCallback, useEffect, useState } from "react";
import {
  approveOsDeliverable,
  approveOsProject,
  cancelOsProject,
  createOsProject,
  fetchOsProject,
  listOsProjects,
  rejectOsDeliverable,
} from "../../utils/api/os";

// Multi-department projects: one big ask becomes an approvable plan of
// department steps (specs/os-projects_spec.md). Hidden until the
// os_projects_enabled flag is on (the list call 404s while off).

import {
  cardStyle,
  btnStyle,
  btnQuiet,
  inputBaseStyle,
  headingStyle,
  mutedStyle,
} from "./osStyles";

const inputStyle = { ...inputBaseStyle, width: "100%" };


const STATUS_COLORS = {
  draft: "#94a3b8",
  approved: "#38bdf8",
  running: "#facc15",
  awaiting_approval: "#facc15",
  done: "#4ade80",
  pending: "#94a3b8",
  failed: "#f87171",
  canceled: "#94a3b8",
};

function StatusPill({ status }) {
  return (
    <span
      style={{
        fontSize: "0.72rem",
        color: STATUS_COLORS[status] || "var(--text-muted)",
        border: `1px solid ${STATUS_COLORS[status] || "var(--border)"}`,
        borderRadius: 999,
        padding: "1px 8px",
        whiteSpace: "nowrap",
      }}
    >
      {String(status || "").replace("_", " ")}
    </span>
  );
}

export default function ProjectsCard({ token }) {
  const [available, setAvailable] = useState(true);
  const [projects, setProjects] = useState([]);
  const [openSteps, setOpenSteps] = useState({});
  const [ask, setAsk] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const out = await listOsProjects(token);
      setProjects(out.projects || []);
      setAvailable(true);
    } catch {
      // Feature flag off - hide the card entirely.
      setAvailable(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const create = async () => {
    if (ask.trim().length < 10) return;
    setBusy(true);
    setError("");
    try {
      await createOsProject(token, ask.trim());
      setAsk("");
      await load();
    } catch (e) {
      setError(e?.message || "Could not plan the project.");
    } finally {
      setBusy(false);
    }
  };

  const refreshSteps = async (projectId) => {
    const out = await fetchOsProject(token, projectId);
    setOpenSteps((prev) => ({ ...prev, [projectId]: out.steps || [] }));
  };

  const toggleSteps = async (projectId) => {
    if (openSteps[projectId]) {
      setOpenSteps((prev) => ({ ...prev, [projectId]: null }));
      return;
    }
    try {
      await refreshSteps(projectId);
    } catch {
      setError("Could not load project steps.");
    }
  };

  // Inline step-deliverable decision: a running project waits on the exact
  // same approval as the Pending approvals queue - deciding it here keeps
  // the whole loop on one screen. The runner picks the outcome up on its
  // next tick.
  const decideStep = async (projectId, runId, decision) => {
    setError("");
    try {
      if (decision === "approve") {
        await approveOsDeliverable(token, runId);
      } else {
        await rejectOsDeliverable(token, runId);
      }
      await refreshSteps(projectId);
      await load();
    } catch (e) {
      setError(e?.message || "Could not update the step's draft.");
    }
  };

  const approve = async (projectId) => {
    try {
      await approveOsProject(token, projectId);
      await load();
    } catch (e) {
      setError(e?.message || "Could not approve the project.");
    }
  };

  const cancel = async (projectId) => {
    try {
      await cancelOsProject(token, projectId);
      await load();
    } catch (e) {
      setError(e?.message || "Could not cancel the project.");
    }
  };

  if (!available) return null;

  return (
    <div style={cardStyle}>
      <h3 style={headingStyle}>Projects</h3>
      <div style={{ ...mutedStyle, marginBottom: 12 }}>
        Give your whole AI workforce one big goal. It plans department steps,
        you approve the plan, and every outbound draft still stops at your
        approval queue.
      </div>
      {error && (
        <div style={{ ...mutedStyle, color: "#f87171", marginBottom: 8 }}>
          {error}
        </div>
      )}
      {projects.length === 0 && (
        <div style={{ ...mutedStyle, marginBottom: 12 }}>
          No projects yet. Try: "Launch a spring promotion for our best
          service."
        </div>
      )}
      {projects.map((project) => (
        <div
          key={project.id}
          style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}
        >
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: "0.9rem",
                  color: "var(--text-primary, #f1f5f9)",
                }}
              >
                {project.title}
              </div>
              {project.error && (
                <div style={{ ...mutedStyle, color: "#f87171" }}>
                  {project.error}
                </div>
              )}
            </div>
            <StatusPill status={project.status} />
            <button style={btnQuiet} onClick={() => toggleSteps(project.id)}>
              {openSteps[project.id] ? "Hide steps" : "Steps"}
            </button>
            {project.status === "draft" && !project.error && (
              <button style={btnStyle} onClick={() => approve(project.id)}>
                Approve plan
              </button>
            )}
            {["draft", "approved", "running"].includes(project.status) && (
              <button style={btnQuiet} onClick={() => cancel(project.id)}>
                Cancel
              </button>
            )}
          </div>
          {openSteps[project.id] && (
            <div style={{ marginTop: 8, display: "grid", gap: 4 }}>
              {openSteps[project.id].map((step) => {
                const needsDecision =
                  step.status === "awaiting_approval" &&
                  step.deliverable_status === "pending_approval" &&
                  step.agent_run_id;
                return (
                  <div key={step.id}>
                    <div
                      style={{ display: "flex", gap: 8, alignItems: "center" }}
                    >
                      <span style={mutedStyle}>
                        {step.position}. {step.department.replace("_", " ")}
                      </span>
                      <span
                        style={{
                          ...mutedStyle,
                          flex: 1,
                          color: "var(--text-secondary)",
                        }}
                      >
                        {step.objective}
                      </span>
                      <StatusPill status={step.status} />
                    </div>
                    {step.deliverable_title && (
                      <div style={{ ...mutedStyle, paddingLeft: 16 }}>
                        Produced: {step.deliverable_title}
                      </div>
                    )}
                    {needsDecision && (
                      <div
                        style={{
                          display: "flex",
                          gap: 8,
                          paddingLeft: 16,
                          marginTop: 4,
                        }}
                      >
                        <button
                          style={btnStyle}
                          onClick={() =>
                            decideStep(project.id, step.agent_run_id, "approve")
                          }
                        >
                          Approve draft
                        </button>
                        <button
                          style={btnQuiet}
                          onClick={() =>
                            decideStep(project.id, step.agent_run_id, "reject")
                          }
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ))}
      <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
        <textarea
          style={{ ...inputStyle, minHeight: 60, resize: "vertical" }}
          placeholder="What should the team accomplish together?"
          value={ask}
          onChange={(e) => setAsk(e.target.value)}
        />
        <div>
          <button style={btnStyle} onClick={create} disabled={busy}>
            {busy ? "Planning..." : "Plan project"}
          </button>
        </div>
      </div>
    </div>
  );
}
