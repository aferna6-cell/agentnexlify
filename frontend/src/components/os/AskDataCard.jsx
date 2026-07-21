import { useEffect, useState } from "react";
import { askBusinessData, fetchAskDataSupported } from "../../utils/api/os";

// Ask-your-business box - deterministic NL answers over the tenant's own
// data (leads, appointments, invoices, conversations). No LLM in the loop.

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

export default function AskDataCard({ token }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [examples, setExamples] = useState([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    fetchAskDataSupported(token)
      .then((out) => {
        if (alive) setExamples((out.supported_questions || []).slice(0, 4));
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [token]);

  const ask = async (q) => {
    const text = (q || question).trim();
    if (!text) return;
    setBusy(true);
    setAnswer(null);
    try {
      const out = await askBusinessData(token, text);
      setAnswer(out);
    } catch (e) {
      setAnswer({ answer: e?.message || "Could not answer that." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={cardStyle}>
      <h3 style={headingStyle}>Ask your business</h3>
      <div style={{ ...mutedStyle, marginBottom: 12 }}>
        Instant answers from your own records - lead counts, bookings,
        invoices - computed directly, never guessed.
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          style={inputStyle}
          placeholder="How many leads did we get this week?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") ask();
          }}
        />
        <button style={btnStyle} onClick={() => ask()} disabled={busy}>
          Ask
        </button>
      </div>
      {examples.length > 0 && (
        <div
          style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}
        >
          {examples.map((ex) => {
            const text = typeof ex === "string" ? ex : ex.example || ex.question;
            if (!text) return null;
            return (
              <button
                key={text}
                style={{
                  ...mutedStyle,
                  background: "var(--bg-primary)",
                  border: "1px solid var(--border)",
                  borderRadius: 999,
                  padding: "4px 10px",
                  cursor: "pointer",
                }}
                onClick={() => {
                  setQuestion(text);
                  ask(text);
                }}
              >
                {text}
              </button>
            );
          })}
        </div>
      )}
      {answer && (
        <div
          style={{
            marginTop: 12,
            padding: "10px 12px",
            background: "var(--bg-primary)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: "0.9rem",
            color: "var(--text-primary, #f1f5f9)",
            whiteSpace: "pre-wrap",
          }}
        >
          {answer.answer || JSON.stringify(answer)}
        </div>
      )}
    </div>
  );
}
