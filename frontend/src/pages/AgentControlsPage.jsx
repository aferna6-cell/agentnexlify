import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  fetchOsInstructions,
  fetchOsUsageBreakdown,
  putOsInstruction,
} from "../utils/api/os";
import {
  createEvalQuestion,
  deleteEvalQuestion,
  fetchLatestEvalRun,
  listEvalQuestions,
  runEvals,
} from "../utils/api/kb-evals";
import { BASE } from "../utils/api/_client";

// ---------------------------------------------------------------------------
// AgentControlsPage — the owner's control room for the enterprise-audit
// adopt-cheaply surfaces: per-department instructions (topics-lite), this
// cycle's usage by department, the golden-question regression suite, and the
// activity-log CSV export.
// ---------------------------------------------------------------------------

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

const DEPARTMENT_LABELS = {
  sales: "Sales",
  marketing: "Marketing",
  customer_service: "Customer service",
  operations: "Operations",
  invoicing: "Invoicing",
  accounting: "Accounting",
  admin_records: "Admin & records",
  people: "People",
};

function InstructionsCard({ token }) {
  const [departments, setDepartments] = useState([]);
  const [instructions, setInstructions] = useState({});
  const [drafts, setDrafts] = useState({});
  const [savingKey, setSavingKey] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    fetchOsInstructions(token)
      .then((data) => {
        if (!alive) return;
        setDepartments(data.departments || []);
        setInstructions(data.instructions || {});
        setDrafts(data.instructions || {});
      })
      .catch((err) => alive && setError(err.message || "Failed to load"));
    return () => {
      alive = false;
    };
  }, [token]);

  const save = async (department) => {
    setSavingKey(department);
    setError("");
    try {
      const out = await putOsInstruction(token, department, drafts[department] || "");
      setInstructions(out.instructions || {});
    } catch (err) {
      setError(err.message || "Save failed");
    } finally {
      setSavingKey("");
    }
  };

  return (
    <div style={cardStyle}>
      <h3 style={headingStyle}>Department instructions</h3>
      <div style={{ ...mutedStyle, marginBottom: 14 }}>
        Standing preferences each department follows — tone, emphasis, style.
        Approvals and safety rules always apply and cannot be overridden here.
      </div>
      {error && (
        <div style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 10 }}>
          {error}
        </div>
      )}
      {departments.map((department) => {
        const saved = instructions[department] || "";
        const draft = drafts[department] ?? "";
        const dirty = draft !== saved;
        return (
          <div key={department} style={{ marginBottom: 14 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 6,
              }}
            >
              <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>
                {DEPARTMENT_LABELS[department] || department}
              </span>
              <button
                style={dirty ? btnStyle : btnQuiet}
                disabled={!dirty || savingKey === department}
                onClick={() => save(department)}
              >
                {savingKey === department ? "Saving…" : "Save"}
              </button>
            </div>
            <textarea
              style={{ ...inputStyle, minHeight: 54, resize: "vertical" }}
              placeholder={`e.g. Always mention our referral program in ${
                DEPARTMENT_LABELS[department] || department
              } messages`}
              value={draft}
              onChange={(e) =>
                setDrafts((prev) => ({ ...prev, [department]: e.target.value }))
              }
            />
          </div>
        );
      })}
    </div>
  );
}

function UsageCard({ token }) {
  const [rows, setRows] = useState(null);
  const [cycleStart, setCycleStart] = useState("");

  useEffect(() => {
    let alive = true;
    fetchOsUsageBreakdown(token)
      .then((data) => {
        if (!alive) return;
        setRows(data.departments || []);
        setCycleStart(data.cycle_start || "");
      })
      .catch(() => alive && setRows([]));
    return () => {
      alive = false;
    };
  }, [token]);

  return (
    <div style={cardStyle}>
      <h3 style={headingStyle}>Usage this cycle</h3>
      <div style={{ ...mutedStyle, marginBottom: 14 }}>
        Agent runs and AI tokens by department since {cycleStart || "cycle start"}.
      </div>
      {rows === null ? (
        <div style={mutedStyle}>Loading…</div>
      ) : rows.length === 0 ? (
        <div style={mutedStyle}>
          No agent activity yet this cycle. Ask your Agent OS for something and
          usage will show up here.
        </div>
      ) : (
        <table style={{ width: "100%", fontSize: "0.85rem" }}>
          <thead>
            <tr style={{ color: "var(--text-muted)", textAlign: "left" }}>
              <th style={{ padding: "4px 0" }}>Department</th>
              <th style={{ textAlign: "right" }}>Runs</th>
              <th style={{ textAlign: "right" }}>Tokens in</th>
              <th style={{ textAlign: "right" }}>Tokens out</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.department}>
                <td style={{ padding: "4px 0" }}>
                  {DEPARTMENT_LABELS[row.department] || row.department}
                </td>
                <td style={{ textAlign: "right" }}>{row.runs}</td>
                <td style={{ textAlign: "right" }}>
                  {row.input_tokens.toLocaleString()}
                </td>
                <td style={{ textAlign: "right" }}>
                  {row.output_tokens.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function GoldenQuestionsCard({ token }) {
  const [questions, setQuestions] = useState([]);
  const [latestRun, setLatestRun] = useState(null);
  const [question, setQuestion] = useState("");
  const [phrases, setPhrases] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [list, run] = await Promise.all([
        listEvalQuestions(token),
        fetchLatestEvalRun(token),
      ]);
      setQuestions(list.questions || []);
      setLatestRun(run);
    } catch (err) {
      setError(err.message || "Failed to load");
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const add = async () => {
    const expected = phrases
      .split(",")
      .map((p) => p.trim())
      .filter(Boolean);
    if (!question.trim() || expected.length === 0) {
      setError("Add a question and at least one expected phrase");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await createEvalQuestion(token, {
        question: question.trim(),
        expected_phrases: expected,
      });
      setQuestion("");
      setPhrases("");
      await load();
    } catch (err) {
      setError(err.message || "Add failed");
    } finally {
      setBusy(false);
    }
  };

  const runNow = async () => {
    setBusy(true);
    setError("");
    try {
      await runEvals(token);
      await load();
    } catch (err) {
      setError(err.message || "Run failed");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id) => {
    try {
      await deleteEvalQuestion(token, id);
      await load();
    } catch (err) {
      setError(err.message || "Delete failed");
    }
  };

  return (
    <div style={cardStyle}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
        }}
      >
        <h3 style={headingStyle}>Golden questions</h3>
        <button style={btnQuiet} onClick={runNow} disabled={busy}>
          {busy ? "Working…" : "Run checks now"}
        </button>
      </div>
      <div style={{ ...mutedStyle, marginBottom: 14 }}>
        Questions your customers ask, plus the phrases your knowledge must
        contain to answer them. Checked automatically after every knowledge
        update — you get alerted when an answer breaks.
      </div>
      {latestRun && (
        <div style={{ ...mutedStyle, marginBottom: 12 }}>
          Last run: {latestRun.passed}/{latestRun.total} passing
          {latestRun.regressions > 0 && (
            <span style={{ color: "#f87171" }}>
              {" "}
              — {latestRun.regressions} regression(s)
            </span>
          )}
        </div>
      )}
      {error && (
        <div style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 10 }}>
          {error}
        </div>
      )}
      {questions.length === 0 && (
        <div style={{ ...mutedStyle, marginBottom: 12 }}>
          No golden questions yet. Start with your three most common customer
          questions — hours, pricing, booking.
        </div>
      )}
      {questions.map((q) => (
        <div
          key={q.id}
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 10,
            padding: "6px 0",
            borderBottom: "1px solid var(--border)",
            fontSize: "0.85rem",
          }}
        >
          <div>
            <div>{q.question}</div>
            <div style={mutedStyle}>
              expects: {(q.expected_phrases || []).join(", ")}
            </div>
          </div>
          <button style={btnQuiet} onClick={() => remove(q.id)}>
            Remove
          </button>
        </div>
      ))}
      <div style={{ display: "grid", gap: 8, marginTop: 14 }}>
        <input
          style={inputStyle}
          placeholder="Customer question, e.g. What are your hours?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <input
          style={inputStyle}
          placeholder="Expected phrases, comma-separated, e.g. 8am-5pm, Saturday"
          value={phrases}
          onChange={(e) => setPhrases(e.target.value)}
        />
        <div>
          <button style={btnStyle} onClick={add} disabled={busy}>
            Add question
          </button>
        </div>
      </div>
    </div>
  );
}

function ExportCard() {
  return (
    <div style={cardStyle}>
      <h3 style={headingStyle}>Activity export</h3>
      <div style={{ ...mutedStyle, marginBottom: 12 }}>
        Download everything your agents logged — every send, booking, and
        guardrail hold — as a CSV audit trail.
      </div>
      <a
        href={`${BASE}/api/v1/activity/export`}
        style={{ ...btnQuiet, textDecoration: "none", display: "inline-block" }}
      >
        Download CSV
      </a>
    </div>
  );
}

export default function AgentControlsPage() {
  const { token } = useAuth();

  if (!token) {
    return (
      <div style={{ padding: 24, color: "var(--text-muted)" }}>
        Sign in to manage agent controls.
      </div>
    );
  }

  return (
    <div style={{ padding: 24, display: "grid", gap: 18, maxWidth: 900 }}>
      <div>
        <h2
          style={{
            margin: 0,
            fontSize: "1.4rem",
            color: "var(--text-primary, #f1f5f9)",
          }}
        >
          Agent Controls
        </h2>
        <div style={mutedStyle}>
          Tune how your AI departments behave, watch what they spend, and keep
          their answers honest.
        </div>
      </div>
      <InstructionsCard token={token} />
      <GoldenQuestionsCard token={token} />
      <UsageCard token={token} />
      <ExportCard />
    </div>
  );
}
