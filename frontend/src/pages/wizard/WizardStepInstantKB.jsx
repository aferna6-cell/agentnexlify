// frontend/src/pages/wizard/WizardStepInstantKB.jsx
// Instant KB - read the tenant's website URL, draft FAQ entries with AI, let the
// owner review/confirm, then save them so the chat widget answers on day one.
// Draft (POST /instant-kb/{tenant}/draft) writes nothing; confirm
// (POST /instant-kb/{tenant}/confirm) persists the checked entries.
import { useState } from "react";
import { draftInstantKb, confirmInstantKb } from "../../utils/api/onboarding";

export default function WizardStepInstantKB({
  wizardData,
  onNext,
  onBack,
  token,
  tenantId,
}) {
  const [url, setUrl] = useState(wizardData?.website_url || "");
  const [status, setStatus] = useState("idle"); // idle | drafting | review | saving | error
  const [errorMsg, setErrorMsg] = useState("");
  const [faqs, setFaqs] = useState([]); // [{question, answer, category, keep}]

  async function handleDraft() {
    const trimmed = (url || "").trim();
    if (trimmed.length < 4) {
      setErrorMsg("Enter your website URL");
      setStatus("error");
      return;
    }
    setStatus("drafting");
    setErrorMsg("");
    try {
      const res = await draftInstantKb(tenantId, token, trimmed);
      const drafted = (res.faqs || []).map((f) => ({ ...f, keep: true }));
      if (drafted.length === 0) {
        setErrorMsg("No FAQs could be drafted. You can add them by hand later.");
        setStatus("error");
        return;
      }
      setFaqs(drafted);
      setStatus("review");
    } catch (e) {
      setErrorMsg(e?.message || "Could not read that website. Try again or skip.");
      setStatus("error");
    }
  }

  function toggle(idx) {
    setFaqs((prev) =>
      prev.map((f, i) => (i === idx ? { ...f, keep: !f.keep } : f)),
    );
  }

  async function handleConfirm() {
    const chosen = faqs
      .filter((f) => f.keep)
      .map(({ question, answer, category }) => ({ question, answer, category }));
    if (chosen.length === 0) {
      // Nothing kept - treat as skip rather than an error.
      onNext({ website_url: url, instant_kb_saved: 0 });
      return;
    }
    setStatus("saving");
    setErrorMsg("");
    try {
      const res = await confirmInstantKb(tenantId, token, chosen);
      onNext({ website_url: url, instant_kb_saved: res.saved || 0 });
    } catch (e) {
      setErrorMsg(e?.message || "Could not save the FAQs. Try again.");
      setStatus("error");
    }
  }

  const keptCount = faqs.filter((f) => f.keep).length;

  return (
    <div>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 8 }}>
        Instant FAQs from your website
      </h2>
      <p style={subtitleStyle}>
        Paste your website URL. We read it and draft answers to common customer
        questions so your chat assistant is useful from day one. Nothing is
        saved until you confirm.
      </p>

      {status !== "review" && (
        <div style={{ marginBottom: 20 }}>
          <label style={labelStyle}>Website URL</label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://yourbusiness.com"
            style={inputStyle}
            disabled={status === "drafting"}
          />
        </div>
      )}

      {status === "drafting" && (
        <div style={{ textAlign: "center", padding: "40px 0" }}>
          <div style={spinnerStyle} />
          <style>{"@keyframes spin { to { transform: rotate(360deg); } }"}</style>
          <p style={{ color: "rgba(255,255,255,0.5)", fontSize: "0.9rem" }}>
            Reading your website and drafting FAQs...
          </p>
        </div>
      )}

      {status === "error" && (
        <div style={errorBoxStyle}>
          <p style={{ color: "#f87171", margin: 0, fontSize: "0.9rem" }}>
            {errorMsg}
          </p>
        </div>
      )}

      {status === "review" && (
        <div style={{ marginBottom: 20 }}>
          <div style={previewHeader}>
            Review draft FAQs ({keptCount} of {faqs.length} selected)
          </div>
          <div style={{ maxHeight: 320, overflowY: "auto" }}>
            {faqs.map((f, i) => (
              <label key={i} style={faqRowStyle(f.keep)}>
                <input
                  type="checkbox"
                  checked={f.keep}
                  onChange={() => toggle(i)}
                  style={{ marginTop: 4, accentColor: "#6366f1" }}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ color: "#e2e8f0", fontWeight: 600, fontSize: "0.9rem" }}>
                    {f.question}
                  </div>
                  <div style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.85rem", marginTop: 2 }}>
                    {f.answer}
                  </div>
                  <span style={categoryChip}>{f.category}</span>
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
        <button
          onClick={onBack}
          style={{ ...btnStyle, background: "rgba(255,255,255,0.08)", flex: 1 }}
          disabled={status === "drafting" || status === "saving"}
        >
          Back
        </button>
        {status === "review" ? (
          <button
            onClick={handleConfirm}
            disabled={status === "saving"}
            style={{ ...btnStyle, flex: 2, opacity: status === "saving" ? 0.5 : 1 }}
          >
            {status === "saving" ? "Saving..." : `Save ${keptCount} FAQ${keptCount === 1 ? "" : "s"} and continue`}
          </button>
        ) : (
          <button
            onClick={handleDraft}
            disabled={status === "drafting" || !url}
            style={{ ...btnStyle, flex: 2, opacity: status === "drafting" || !url ? 0.5 : 1 }}
          >
            {status === "drafting" ? "Reading..." : "Read website and draft FAQs"}
          </button>
        )}
      </div>

      {status !== "review" && status !== "drafting" && status !== "saving" && (
        <button onClick={() => onNext({ website_url: url })} style={skipStyle}>
          Skip - I will add FAQs by hand
        </button>
      )}
    </div>
  );
}

const subtitleStyle = {
  color: "rgba(255,255,255,0.5)",
  marginBottom: 24,
  fontSize: "0.9rem",
};

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

const errorBoxStyle = {
  background: "rgba(220,38,38,0.1)",
  border: "1px solid rgba(220,38,38,0.3)",
  borderRadius: 10,
  padding: 16,
  marginBottom: 16,
};

const spinnerStyle = {
  width: 40,
  height: 40,
  border: "3px solid rgba(255,255,255,0.1)",
  borderTopColor: "#6366f1",
  borderRadius: "50%",
  animation: "spin 0.8s linear infinite",
  margin: "0 auto 12px",
};

const previewHeader = {
  fontSize: "0.78rem",
  color: "rgba(255,255,255,0.5)",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  marginBottom: 10,
  fontWeight: 600,
};

const categoryChip = {
  display: "inline-block",
  marginTop: 6,
  background: "rgba(99,102,241,0.15)",
  border: "1px solid rgba(99,102,241,0.35)",
  color: "#c7d2fe",
  borderRadius: 999,
  padding: "2px 10px",
  fontSize: "0.72rem",
};

const skipStyle = {
  marginTop: 12,
  width: "100%",
  background: "transparent",
  color: "rgba(255,255,255,0.5)",
  border: "none",
  fontSize: "0.85rem",
  cursor: "pointer",
  padding: "12px",
  minHeight: 44,
};

function faqRowStyle(keep) {
  return {
    display: "flex",
    gap: 10,
    alignItems: "flex-start",
    background: keep ? "rgba(99,102,241,0.06)" : "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 10,
    padding: 12,
    marginBottom: 10,
    cursor: "pointer",
  };
}
