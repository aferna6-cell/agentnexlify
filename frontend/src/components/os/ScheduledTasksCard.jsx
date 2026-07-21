import { useCallback, useEffect, useState } from "react";
import {
  createOsTask,
  deleteOsTask,
  fetchOsTaskSuggestions,
  listOsTasks,
  updateOsTask,
} from "../../utils/api/os";

// Recurring department prompts - "your AI workforce shows up on Monday".
// Styles mirror AgentControlsPage's inline card conventions.

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: "18px 22px",
};

const btnStyle = {
  border: "none",
  borderRadius: 8,
  padding: "8px 16px",
  cursor: "pointer",
  fontSize: "0.85rem",
  color: "#fff",
  background: "var(--accent, #6366f1)",
};

const btnQuiet = {
  ...btnStyle,
  background: "var(--bg-primary)",
  color: "var(--text-secondary)",
  border: "1px solid var(--border)",
};

const inputStyle = {
  width: "100%",
  background: "var(--bg-primary)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text-primary, #f1f5f9)",
  padding: "8px 10px",
  fontSize: "0.85rem",
  boxSizing: "border-box",
};

const headingStyle = {
  margin: "0 0 4px",
  fontSize: "1rem",
  fontWeight: 600,
  color: "var(--text-primary, #f1f5f9)",
};

const mutedStyle = { fontSize: "0.8rem", color: "var(--text-muted)" };

export default function ScheduledTasksCard({ token }) {
  const [tasks, setTasks] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [department, setDepartment] = useState("marketing");
  const [prompt, setPrompt] = useState("");
  const [intervalDays, setIntervalDays] = useState(7);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const out = await listOsTasks(token);
      setTasks(out.tasks || []);
      setDepartments(out.departments || []);
      if ((out.tasks || []).length === 0) {
        try {
          const sug = await fetchOsTaskSuggestions(token);
          setSuggestions(sug.suggestions || []);
        } catch {
          setSuggestions([]);
        }
      } else {
        setSuggestions([]);
      }
    } catch {
      setError("Could not load scheduled tasks.");
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const add = async () => {
    if (prompt.trim().length < 5) return;
    setBusy(true);
    setError("");
    try {
      await createOsTask(token, {
        department,
        prompt: prompt.trim(),
        interval_days: Number(intervalDays) || 7,
        enabled: true,
      });
      setPrompt("");
      await load();
    } catch (e) {
      setError(e?.message || "Could not create the task.");
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (task) => {
    try {
      await updateOsTask(token, task.id, { enabled: !task.enabled });
      await load();
    } catch {
      setError("Could not update the task.");
    }
  };

  const remove = async (taskId) => {
    try {
      await deleteOsTask(token, taskId);
      await load();
    } catch {
      setError("Could not delete the task.");
    }
  };

  return (
    <div style={cardStyle}>
      <h3 style={headingStyle}>Recurring tasks</h3>
      <div style={{ ...mutedStyle, marginBottom: 12 }}>
        Standing work your AI departments do on a schedule - a weekly promo
        draft, a Monday business summary. Every result still goes through
        your normal approval queue.
      </div>
      {error && (
        <div style={{ ...mutedStyle, color: "#f87171", marginBottom: 8 }}>
          {error}
        </div>
      )}
      {tasks.length === 0 && (
        <div style={{ ...mutedStyle, marginBottom: 12 }}>
          No recurring tasks yet.
          {suggestions.length === 0 &&
            ' Add one below - for example: "Draft this week\'s promotional social post."'}
        </div>
      )}
      {tasks.length === 0 && suggestions.length > 0 && (
        <div style={{ display: "grid", gap: 8, marginBottom: 12 }}>
          {suggestions.map((s) => (
            <div
              key={s.label}
              style={{ display: "flex", gap: 10, alignItems: "center" }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: "0.85rem",
                    color: "var(--text-primary, #f1f5f9)",
                  }}
                >
                  {s.label}
                </div>
                <div style={mutedStyle}>
                  {s.department} · every {s.interval_days} days
                </div>
              </div>
              <button
                style={btnStyle}
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  setError("");
                  try {
                    await createOsTask(token, {
                      department: s.department,
                      prompt: s.prompt,
                      interval_days: s.interval_days,
                      enabled: true,
                    });
                    await load();
                  } catch (e) {
                    setError(e?.message || "Could not add the task.");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Add
              </button>
            </div>
          ))}
        </div>
      )}
      {tasks.map((task) => (
        <div
          key={task.id}
          style={{
            display: "flex",
            gap: 10,
            alignItems: "center",
            padding: "8px 0",
            borderBottom: "1px solid var(--border)",
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: "0.85rem",
                color: "var(--text-primary, #f1f5f9)",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
              title={task.prompt}
            >
              {task.prompt}
            </div>
            <div style={mutedStyle}>
              {task.department} · every {task.interval_days} day
              {task.interval_days === 1 ? "" : "s"}
              {task.last_run_at
                ? ` · last ran ${String(task.last_run_at).slice(0, 10)}`
                : " · has not run yet"}
            </div>
          </div>
          <button style={btnQuiet} onClick={() => toggle(task)}>
            {task.enabled ? "Pause" : "Resume"}
          </button>
          <button style={btnQuiet} onClick={() => remove(task.id)}>
            Delete
          </button>
        </div>
      ))}
      <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
        <textarea
          style={{ ...inputStyle, minHeight: 60, resize: "vertical" }}
          placeholder="What should the agent do on a schedule?"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <select
            style={{ ...inputStyle, width: "auto" }}
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
          >
            {(departments.length ? departments : ["marketing"]).map((d) => (
              <option key={d} value={d}>
                {d.replace("_", " ")}
              </option>
            ))}
          </select>
          <select
            style={{ ...inputStyle, width: "auto" }}
            value={intervalDays}
            onChange={(e) => setIntervalDays(e.target.value)}
          >
            <option value={1}>Daily</option>
            <option value={7}>Weekly</option>
            <option value={14}>Every 2 weeks</option>
            <option value={30}>Monthly</option>
          </select>
          <button style={btnStyle} onClick={add} disabled={busy}>
            Add task
          </button>
        </div>
      </div>
    </div>
  );
}
