import { useState } from "react";
import { saveStep } from "../../utils/api/onboardingV2";
import VisualHoursPicker from "../../components/onboarding-v2/VisualHoursPicker";
import FaqBulkImport from "../../components/onboarding-v2/FaqBulkImport";
import ReadyToLaunchBadge from "../../components/onboarding-v2/ReadyToLaunchBadge";

function defaultHoursFromAutoKb(autoKbResult) {
  if (autoKbResult?.hours && typeof autoKbResult.hours === "object") {
    return autoKbResult.hours;
  }
  return null;
}

export default function WizardStepHoursFaqV2({
  wizardData,
  token,
  onNext,
  onBack,
}) {
  const [hours, setHours] = useState(
    wizardData.hours || defaultHoursFromAutoKb(wizardData.autoKbResult),
  );
  const [faqs, setFaqs] = useState(() => {
    const existing = wizardData.faqs || [];
    const fromKb = wizardData.autoKbResult?.faqs || [];
    return existing.length > 0 ? existing : fromKb;
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function handleImport(imported) {
    setFaqs((prev) => {
      const existingQs = new Set(prev.map((f) => f.q));
      const deduped = imported.filter((f) => !existingQs.has(f.q));
      return [...prev, ...deduped];
    });
  }

  function removeFaq(idx) {
    setFaqs((prev) => prev.filter((_, i) => i !== idx));
  }

  const hoursFilled =
    hours !== null && Object.values(hours).some((v) => v !== null);
  const criteria = {
    services_count: wizardData.services?.length || 0,
    hours_filled: hoursFilled,
    faqs_count: faqs.length,
    logo_uploaded: false,
  };

  async function handleNext() {
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      await saveStep(token, 4, {
        hours,
        timezone: wizardData.timezone,
        faqs,
      });
      onNext({ hours, faqs });
    } catch (err) {
      setError(err.message || "Failed to save. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h2 style={headingStyle}>Confirm your hours and FAQs</h2>
      <p style={subStyle}>
        Your AI assistant uses these to answer questions accurately 24/7.
      </p>

      {error && <div style={errorStyle}>{error}</div>}

      {/* Hours section */}
      <div style={sectionStyle}>
        <p style={sectionLabelStyle}>Business hours</p>
        <VisualHoursPicker value={hours} onChange={setHours} />
      </div>

      {/* FAQs section */}
      <div style={sectionStyle}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 12,
          }}
        >
          <p style={{ ...sectionLabelStyle, marginBottom: 0 }}>FAQs</p>
          <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.35)" }}>
            {faqs.length} added
          </span>
        </div>

        {faqs.length === 0 && (
          <div style={emptyFaqStyle}>
            No FAQs yet — import some below or add them after launch. Your AI
            will still work without them.
          </div>
        )}

        {faqs.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            {faqs.map((faq, i) => (
              <div key={i} style={faqRowStyle}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: "0.85rem",
                      fontWeight: 600,
                      color: "rgba(255,255,255,0.85)",
                      marginBottom: 2,
                    }}
                  >
                    {faq.q}
                  </div>
                  <div
                    style={{
                      fontSize: "0.8rem",
                      color: "rgba(255,255,255,0.45)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {faq.a}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => removeFaq(i)}
                  aria-label="Remove FAQ"
                  style={faqRemoveBtnStyle}
                >
                  x
                </button>
              </div>
            ))}
          </div>
        )}

        <div
          style={{
            borderTop:
              faqs.length > 0 ? "1px solid rgba(255,255,255,0.06)" : "none",
            paddingTop: faqs.length > 0 ? 16 : 0,
          }}
        >
          <p
            style={{
              fontSize: "0.82rem",
              color: "rgba(255,255,255,0.4)",
              marginTop: 0,
              marginBottom: 10,
            }}
          >
            Import more FAQs
          </p>
          <FaqBulkImport onImport={handleImport} />
        </div>
      </div>

      {/* Readiness badge */}
      <div style={{ marginBottom: 24 }}>
        <ReadyToLaunchBadge criteria={criteria} />
      </div>

      <div style={{ display: "flex", gap: 12 }}>
        <button type="button" onClick={onBack} style={backBtnStyle}>
          Back
        </button>
        <button
          type="button"
          onClick={handleNext}
          disabled={saving}
          style={nextBtnStyle(saving)}
        >
          {saving ? "Saving..." : "Continue"}
        </button>
      </div>
    </div>
  );
}

const headingStyle = {
  fontSize: "1.4rem",
  fontWeight: 700,
  marginBottom: 8,
  marginTop: 0,
};
const subStyle = {
  color: "rgba(255,255,255,0.5)",
  marginBottom: 24,
  fontSize: "0.9rem",
  marginTop: 0,
};
const sectionStyle = {
  background: "rgba(255,255,255,0.02)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 10,
  padding: "16px",
  marginBottom: 16,
};
const sectionLabelStyle = {
  fontSize: "0.82rem",
  fontWeight: 600,
  color: "rgba(255,255,255,0.45)",
  marginBottom: 12,
  marginTop: 0,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};
const errorStyle = {
  background: "rgba(220,38,38,0.15)",
  border: "1px solid rgba(220,38,38,0.3)",
  color: "#fca5a5",
  padding: "10px 14px",
  borderRadius: 8,
  marginBottom: 16,
  fontSize: "0.9rem",
};
const emptyFaqStyle = {
  background: "rgba(255,255,255,0.03)",
  border: "1px dashed rgba(255,255,255,0.1)",
  borderRadius: 8,
  padding: "14px",
  fontSize: "0.82rem",
  color: "rgba(255,255,255,0.4)",
  textAlign: "center",
  marginBottom: 14,
};
const faqRowStyle = {
  display: "flex",
  alignItems: "center",
  gap: 10,
  padding: "10px 0",
  borderBottom: "1px solid rgba(255,255,255,0.05)",
};
const faqRemoveBtnStyle = {
  background: "none",
  border: "none",
  color: "rgba(255,255,255,0.25)",
  cursor: "pointer",
  fontSize: "0.9rem",
  padding: "4px",
  minWidth: 28,
  minHeight: 28,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  flexShrink: 0,
  borderRadius: 4,
};
const backBtnStyle = {
  flex: "0 0 auto",
  padding: "16px 20px",
  minHeight: 52,
  background: "rgba(255,255,255,0.05)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 10,
  color: "rgba(255,255,255,0.6)",
  fontSize: "1rem",
  cursor: "pointer",
};
const nextBtnStyle = (disabled) => ({
  flex: 1,
  padding: "16px",
  minHeight: 52,
  background: disabled ? "rgba(99,102,241,0.4)" : "#6366f1",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  fontSize: "1rem",
  fontWeight: 600,
  cursor: disabled ? "not-allowed" : "pointer",
});
