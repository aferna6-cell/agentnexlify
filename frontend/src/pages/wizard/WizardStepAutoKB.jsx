// frontend/src/pages/wizard/WizardStepAutoKB.jsx
// Onboarding v2 — auto-fill wizard from existing website URL.
// Calls /api/v1/onboarding/{tenant}/auto-kb, surfaces structured services + hours
// + KB + FAQs for owner review before continuing.
import { useState } from "react";
import { autoGenerateKb } from "../../utils/api/onboarding";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function WizardStepAutoKB({
  wizardData,
  onNext,
  onBack,
  token,
  tenantId,
}) {
  const [url, setUrl] = useState(wizardData.website_url || "");
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [errorMsg, setErrorMsg] = useState("");
  const [result, setResult] = useState(null);

  async function handleAutoFill() {
    if (!url || url.length < 5) {
      setErrorMsg("Enter a website URL");
      setStatus("error");
      return;
    }
    setStatus("loading");
    setErrorMsg("");
    try {
      const res = await autoGenerateKb(tenantId, token, url);
      setResult(res);
      setStatus("done");
    } catch (e) {
      setErrorMsg(e?.message || "Auto-fill failed");
      setStatus("error");
    }
  }

  function handleContinue() {
    if (result) {
      onNext({
        website_url: url,
        services: result.services || [],
        hours: result.hours || {},
        knowledge_base: result.knowledge_base || "",
        custom_instructions: result.custom_instructions || "",
        faqs: result.faqs || [],
      });
    } else {
      onNext({ website_url: url });
    }
  }

  return (
    <div>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 8 }}>
        Auto-fill from your website
      </h2>
      <p
        style={{
          color: "rgba(255,255,255,0.5)",
          marginBottom: 24,
          fontSize: "0.9rem",
        }}
      >
        Paste your business website URL. We'll read it and pre-fill your
        services, hours, and FAQs so you don't type from scratch.
      </p>

      {status !== "done" && (
        <div style={{ marginBottom: 20 }}>
          <label style={labelStyle}>Website URL</label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://yourbusiness.com"
            style={inputStyle}
            disabled={status === "loading"}
          />
        </div>
      )}

      {status === "loading" && (
        <div style={{ textAlign: "center", padding: "40px 0" }}>
          <div
            style={{
              width: 40,
              height: 40,
              border: "3px solid rgba(255,255,255,0.1)",
              borderTopColor: "#6366f1",
              borderRadius: "50%",
              animation: "spin 0.8s linear infinite",
              margin: "0 auto 12px",
            }}
          />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          <p style={{ color: "rgba(255,255,255,0.5)", fontSize: "0.9rem" }}>
            Reading {url}…
          </p>
        </div>
      )}

      {status === "error" && (
        <div
          style={{
            background: "rgba(220,38,38,0.1)",
            border: "1px solid rgba(220,38,38,0.3)",
            borderRadius: 10,
            padding: 16,
            marginBottom: 16,
          }}
        >
          <p style={{ color: "#f87171", margin: 0, fontSize: "0.9rem" }}>
            {errorMsg}
          </p>
        </div>
      )}

      {status === "done" && result && (
        <div style={{ marginBottom: 20 }}>
          <div style={previewBlock}>
            <div style={previewHeader}>
              Services found ({result.services?.length || 0})
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {(result.services || []).map((s, i) => (
                <span key={i} style={chipStyle}>
                  {s}
                </span>
              ))}
              {(!result.services || result.services.length === 0) && (
                <span
                  style={{
                    color: "rgba(255,255,255,0.4)",
                    fontSize: "0.85rem",
                  }}
                >
                  None detected — you can add later.
                </span>
              )}
            </div>
          </div>

          <div style={previewBlock}>
            <div style={previewHeader}>Hours</div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(7, 1fr)",
                gap: 6,
              }}
            >
              {DAYS.map((d) => (
                <div key={d} style={dayCell}>
                  <div
                    style={{
                      fontSize: "0.75rem",
                      color: "rgba(255,255,255,0.5)",
                    }}
                  >
                    {d}
                  </div>
                  <div
                    style={{
                      fontSize: "0.78rem",
                      color: "#e2e8f0",
                      marginTop: 2,
                    }}
                  >
                    {result.hours?.[d] || "—"}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={previewBlock}>
            <div style={previewHeader}>FAQs ({result.faqs?.length || 0})</div>
            <div style={{ maxHeight: 160, overflowY: "auto" }}>
              {(result.faqs || []).slice(0, 6).map((f, i) => (
                <div key={i} style={{ marginBottom: 8, fontSize: "0.85rem" }}>
                  <div style={{ color: "#e2e8f0", fontWeight: 600 }}>
                    {f.question}
                  </div>
                  <div style={{ color: "rgba(255,255,255,0.6)" }}>
                    {f.answer}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ ...previewBlock, maxHeight: 200, overflowY: "auto" }}>
            <div style={previewHeader}>Knowledge base preview</div>
            <pre
              style={{
                margin: 0,
                whiteSpace: "pre-wrap",
                fontSize: "0.8rem",
                color: "rgba(255,255,255,0.7)",
                fontFamily: "monospace",
              }}
            >
              {(result.knowledge_base || "").slice(0, 600)}
              {(result.knowledge_base || "").length > 600 ? "…" : ""}
            </pre>
          </div>
        </div>
      )}

      <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
        <button
          onClick={onBack}
          style={{ ...btnStyle, background: "rgba(255,255,255,0.08)", flex: 1 }}
        >
          ← Back
        </button>
        {status !== "done" ? (
          <button
            onClick={handleAutoFill}
            disabled={status === "loading" || !url}
            style={{
              ...btnStyle,
              flex: 2,
              opacity: status === "loading" || !url ? 0.5 : 1,
            }}
          >
            {status === "loading" ? "Reading…" : "Auto-fill from website"}
          </button>
        ) : (
          <button onClick={handleContinue} style={{ ...btnStyle, flex: 2 }}>
            Use this and continue →
          </button>
        )}
      </div>

      {status !== "done" && status !== "loading" && (
        <button
          onClick={() => onNext({ website_url: url })}
          style={{
            marginTop: 12,
            width: "100%",
            background: "transparent",
            color: "rgba(255,255,255,0.5)",
            border: "none",
            fontSize: "0.85rem",
            cursor: "pointer",
            padding: "12px",
            minHeight: 44,
          }}
        >
          Skip — I'll fill in by hand
        </button>
      )}
    </div>
  );
}

const btnStyle = {
  padding: "14px",
  background: "#6366f1",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  fontSize: "1rem",
  fontWeight: 600,
  cursor: "pointer",
};

const inputStyle = {
  width: "100%",
  padding: "12px 14px",
  background: "rgba(255,255,255,0.06)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 10,
  color: "#e2e8f0",
  fontSize: "0.95rem",
  boxSizing: "border-box",
};

const labelStyle = {
  display: "block",
  fontSize: "0.85rem",
  color: "rgba(255,255,255,0.7)",
  marginBottom: 6,
};

const previewBlock = {
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 10,
  padding: 14,
  marginBottom: 12,
};

const previewHeader = {
  fontSize: "0.78rem",
  color: "rgba(255,255,255,0.5)",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  marginBottom: 10,
  fontWeight: 600,
};

const chipStyle = {
  background: "rgba(99,102,241,0.15)",
  border: "1px solid rgba(99,102,241,0.35)",
  color: "#c7d2fe",
  borderRadius: 999,
  padding: "5px 12px",
  fontSize: "0.82rem",
};

const dayCell = {
  background: "rgba(255,255,255,0.03)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 6,
  padding: "8px 4px",
  textAlign: "center",
};
