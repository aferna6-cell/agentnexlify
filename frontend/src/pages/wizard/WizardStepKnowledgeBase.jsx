// frontend/src/pages/wizard/WizardStepKnowledgeBase.jsx
import { useState, useEffect } from "react";
import { generateKb } from "../../utils/api/onboarding";

export default function WizardStepKnowledgeBase({ wizardData, onNext, onBack, token, tenantId }) {
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [kb, setKb] = useState(wizardData.knowledge_base || null);
  const [editing, setEditing] = useState(false);
  const [editedKb, setEditedKb] = useState("");

  useEffect(() => {
    // Auto-trigger generation if we don't already have a KB
    if (!kb && status === "idle") {
      generate();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function generate() {
    setStatus("loading");
    try {
      const payload = {
        business_name: wizardData.business_name,
        business_type: wizardData.business_type,
        city: wizardData.city,
        phone: wizardData.phone || null,
        website_url: wizardData.website_url || null,
        services: wizardData.services || [],
        faqs: wizardData.faqs || [],
        hours: wizardData.hours || null,
      };
      const res = await generateKb(tenantId, token, payload);
      if (res.generated && res.knowledge_base) {
        setKb(res.knowledge_base);
        setEditedKb(res.knowledge_base);
        setStatus("done");
      } else {
        setStatus("error");
      }
    } catch {
      setStatus("error");
    }
  }

  function handleNext() {
    const finalKb = editing ? editedKb : kb;
    onNext({ knowledge_base: finalKb });
  }

  return (
    <div>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 8 }}>Generating your AI knowledge base</h2>
      <p style={{ color: "rgba(255,255,255,0.5)", marginBottom: 32, fontSize: "0.9rem" }}>
        Your answers are being turned into a knowledge base your AI assistant will use to answer customer questions.
      </p>

      {status === "loading" && (
        <div style={{ textAlign: "center", padding: "60px 0" }}>
          <div style={{ width: 48, height: 48, border: "3px solid rgba(255,255,255,0.1)", borderTopColor: "#6366f1", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 16px" }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          <p style={{ color: "rgba(255,255,255,0.5)" }}>Building knowledge base…</p>
        </div>
      )}

      {status === "error" && (
        <div style={{ background: "rgba(220,38,38,0.1)", border: "1px solid rgba(220,38,38,0.3)", borderRadius: 10, padding: 20, marginBottom: 24 }}>
          <p style={{ color: "#f87171", margin: 0, marginBottom: 12 }}>Generation failed. You can retry or skip and continue.</p>
          <button onClick={generate} style={btnSecondary}>Retry</button>
        </div>
      )}

      {status === "done" && kb && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <span style={{ fontWeight: 600, color: "#86efac" }}>✓ Knowledge base ready</span>
            <button onClick={() => { setEditing(!editing); setEditedKb(kb); }} style={btnSecondary}>
              {editing ? "Done editing" : "Edit"}
            </button>
          </div>
          {editing ? (
            <textarea
              value={editedKb}
              onChange={e => setEditedKb(e.target.value)}
              rows={16}
              style={{ ...textareaStyle, fontFamily: "monospace", fontSize: "0.82rem" }}
            />
          ) : (
            <div style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, padding: 20, maxHeight: 320, overflowY: "auto" }}>
              <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: "0.85rem", color: "rgba(255,255,255,0.8)", fontFamily: "monospace" }}>{kb}</pre>
            </div>
          )}
        </div>
      )}

      <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
        <button onClick={onBack} style={{ ...btnStyle, background: "rgba(255,255,255,0.08)", flex: 1 }}>← Back</button>
        <button
          onClick={handleNext}
          disabled={status === "loading"}
          style={{ ...btnStyle, flex: 2, opacity: status === "loading" ? 0.5 : 1 }}
        >
          {status === "idle" || status === "error" ? "Skip →" : "Continue →"}
        </button>
      </div>
    </div>
  );
}

const btnStyle = { padding: "14px", background: "#6366f1", color: "#fff", border: "none", borderRadius: 10, fontSize: "1rem", fontWeight: 600, cursor: "pointer" };
const btnSecondary = { padding: "8px 14px", background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.7)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 8, fontSize: "0.85rem", cursor: "pointer", minHeight: 36 };
const textareaStyle = { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: "12px", color: "#e2e8f0", fontSize: "0.9rem", width: "100%", boxSizing: "border-box", resize: "vertical" };
