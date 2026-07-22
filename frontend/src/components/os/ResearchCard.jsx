import { useState } from "react";
import { createProjectFromResearch, runOsResearch } from "../../utils/api/os";

// Deep research card - the research pillar's dashboard surface. A topic
// becomes a propose-only brief synthesized ONLY from sources the tenant
// already owns (knowledge base, FAQs, department instructions, learned
// memory, connected tools). The brief parks at the normal approval gate,
// and "Act on this brief" seeds a multi-department project from it.

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
  flex: 1,
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

export default function ResearchCard({ token }) {
  const [topic, setTopic] = useState("");
  const [urlsText, setUrlsText] = useState("");
  const [run, setRun] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [projectBusy, setProjectBusy] = useState(false);
  const [projectNote, setProjectNote] = useState("");

  const research = async () => {
    const text = topic.trim();
    if (text.length < 10) {
      setError("Give the research a real topic - at least 10 characters.");
      return;
    }
    const urls = urlsText
      .split(",")
      .map((u) => u.trim())
      .filter(Boolean)
      .slice(0, 3);
    setBusy(true);
    setError("");
    setRun(null);
    setProjectNote("");
    try {
      const out = await runOsResearch(token, text, urls);
      setRun(out.run || null);
    } catch (e) {
      setError(e?.message || "Research failed.");
    } finally {
      setBusy(false);
    }
  };

  const actOnBrief = async () => {
    if (!run?.id) return;
    setProjectBusy(true);
    setError("");
    try {
      const out = await createProjectFromResearch(token, run.id);
      const title = out?.project?.title || "your new project";
      if (out?.project?.error) {
        setProjectNote(
          "Project created, but planning hit a snag - open the Projects card to retry.",
        );
      } else {
        setProjectNote(
          `Project drafted: "${title}". Review and approve its plan in the Projects card.`,
        );
      }
    } catch (e) {
      setError(e?.message || "Could not start a project from this brief.");
    } finally {
      setProjectBusy(false);
    }
  };

  const deliverable = run?.deliverable || {};

  return (
    <div style={cardStyle}>
      <h3 style={headingStyle}>Deep research</h3>
      <div style={{ ...mutedStyle, marginBottom: 12 }}>
        A research brief built only from your own knowledge - your Second
        Brain, FAQs, department instructions, learned memory, and connected
        tools. Gaps are named, never papered over.
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          style={inputStyle}
          placeholder="e.g. What do our regulars ask about most, and where do we lose them?"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") research();
          }}
        />
        <button style={btnStyle} onClick={research} disabled={busy}>
          {busy ? "Researching..." : "Research"}
        </button>
      </div>
      <input
        style={{ ...inputStyle, width: "100%", marginTop: 8 }}
        placeholder="Optional: web pages to include, comma-separated (up to 3 URLs - e.g. a competitor's pricing page)"
        value={urlsText}
        onChange={(e) => setUrlsText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") research();
        }}
      />
      {error && (
        <div style={{ color: "#f87171", fontSize: "0.85rem", marginTop: 10 }}>
          {error}
        </div>
      )}
      {run && (
        <div style={{ marginTop: 12 }}>
          <div
            style={{
              fontSize: "0.9rem",
              fontWeight: 600,
              color: "var(--text-primary, #f1f5f9)",
              marginBottom: 6,
            }}
          >
            {deliverable.title || "Research brief"}
          </div>
          <div
            style={{
              padding: "10px 12px",
              background: "var(--bg-primary)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: "0.85rem",
              color: "var(--text-primary, #f1f5f9)",
              whiteSpace: "pre-wrap",
              maxHeight: 320,
              overflowY: "auto",
            }}
          >
            {deliverable.body || ""}
          </div>
          <div style={{ ...mutedStyle, marginTop: 8 }}>
            Saved to Pending approvals - approve it there to keep it on
            record.
          </div>
          <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
            <button
              style={btnQuiet}
              onClick={actOnBrief}
              disabled={projectBusy}
            >
              {projectBusy ? "Starting project..." : "Act on this brief"}
            </button>
          </div>
          {projectNote && (
            <div
              style={{
                marginTop: 8,
                fontSize: "0.85rem",
                color: "var(--text-primary, #f1f5f9)",
              }}
            >
              {projectNote}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
