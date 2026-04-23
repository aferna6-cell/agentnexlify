import { useState, useEffect } from "react";
import { saveStep, getPreset } from "../../utils/api/onboardingV2";
import VerticalPresetPicker from "../../components/onboarding-v2/VerticalPresetPicker";

export default function WizardStepServicesV2({
  wizardData,
  token,
  onNext,
  onBack,
}) {
  const [vertical, setVertical] = useState(wizardData.vertical || "");
  const [services, setServices] = useState(wizardData.services || []);
  const [avgTicket, setAvgTicket] = useState(wizardData.avgTicket || null);
  const [newService, setNewService] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Fetch preset when vertical is chosen or changes
  useEffect(() => {
    if (!vertical) return;
    let cancelled = false;
    setLoading(true);
    getPreset(token, vertical)
      .then((data) => {
        if (cancelled) return;
        // Only seed services if the user hasn't manually customized yet
        if (services.length === 0 && data.services?.length) {
          setServices(data.services);
        }
        if (data.avg_ticket) setAvgTicket(data.avg_ticket);
      })
      .catch(() => {
        // Preset fetch failure is non-blocking — user can add services manually
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // Only re-fetch when vertical changes, not when services change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vertical, token]);

  function removeService(idx) {
    setServices((prev) => prev.filter((_, i) => i !== idx));
  }

  function addService() {
    const trimmed = newService.trim();
    if (!trimmed || services.includes(trimmed)) return;
    setServices((prev) => [...prev, trimmed]);
    setNewService("");
  }

  function handleKeyDown(e) {
    if (e.key === "Enter") {
      e.preventDefault();
      addService();
    }
  }

  async function handleNext() {
    if (!vertical) {
      setError("Choose your trade to continue.");
      return;
    }
    if (services.length === 0) {
      setError("Add at least one service.");
      return;
    }
    setError("");
    setSaving(true);
    try {
      await saveStep(token, 2, { vertical, services, avg_ticket: avgTicket });
      onNext({ vertical, services, avgTicket });
    } catch (err) {
      setError(err.message || "Failed to save. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h2 style={headingStyle}>Pick your services</h2>
      <p style={subStyle}>
        We pre-fill services for your trade. Remove ones you don't offer and add
        your own.
      </p>

      {error && <div style={errorStyle}>{error}</div>}

      <div style={{ marginBottom: 24 }}>
        <p style={sectionLabelStyle}>Your trade</p>
        <VerticalPresetPicker value={vertical} onChange={setVertical} />
      </div>

      {loading && <div style={loadingStyle}>Loading preset services...</div>}

      {!loading && vertical && (
        <>
          <div style={{ marginBottom: 24 }}>
            <p style={sectionLabelStyle}>Services offered</p>

            {services.length === 0 && (
              <div style={emptyStateStyle}>
                No services yet — add some below, or we auto-fill when you pick
                a trade above.
              </div>
            )}

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 8,
                marginBottom: 12,
              }}
            >
              {services.map((s, i) => (
                <div key={i} style={chipStyle}>
                  <span style={{ fontSize: "0.85rem" }}>{s}</span>
                  <button
                    type="button"
                    onClick={() => removeService(i)}
                    aria-label={`Remove ${s}`}
                    style={chipRemoveStyle}
                  >
                    x
                  </button>
                </div>
              ))}
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <input
                style={{ ...inputStyle, flex: 1 }}
                value={newService}
                onChange={(e) => setNewService(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Add a service (e.g. Water heater install)"
              />
              <button
                type="button"
                onClick={addService}
                disabled={!newService.trim()}
                style={addBtnStyle(!newService.trim())}
              >
                Add
              </button>
            </div>
          </div>

          {avgTicket && (
            <div style={avgTicketStyle}>
              Average job value: ${avgTicket.toLocaleString()}
            </div>
          )}
        </>
      )}

      {!vertical && (
        <div style={emptyStateStyle}>
          Pick your trade above to see pre-filled services for your industry.
        </div>
      )}

      <div style={{ display: "flex", gap: 12, marginTop: 32 }}>
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
const sectionLabelStyle = {
  fontSize: "0.85rem",
  fontWeight: 600,
  color: "rgba(255,255,255,0.5)",
  marginBottom: 10,
  marginTop: 0,
  textTransform: "uppercase",
  letterSpacing: "0.04em",
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
const loadingStyle = {
  textAlign: "center",
  color: "rgba(255,255,255,0.4)",
  fontSize: "0.9rem",
  padding: "20px 0",
};
const emptyStateStyle = {
  background: "rgba(255,255,255,0.03)",
  border: "1px dashed rgba(255,255,255,0.1)",
  borderRadius: 8,
  padding: "16px",
  fontSize: "0.85rem",
  color: "rgba(255,255,255,0.4)",
  textAlign: "center",
  marginBottom: 12,
};
const chipStyle = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  background: "rgba(99,102,241,0.15)",
  border: "1px solid rgba(99,102,241,0.3)",
  borderRadius: 20,
  padding: "6px 12px",
  color: "#a5b4fc",
};
const chipRemoveStyle = {
  background: "none",
  border: "none",
  color: "rgba(165,180,252,0.6)",
  cursor: "pointer",
  padding: "0 0 0 2px",
  fontSize: "0.85rem",
  lineHeight: 1,
  minWidth: 20,
  minHeight: 20,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};
const inputStyle = {
  background: "rgba(255,255,255,0.06)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 8,
  padding: "12px 14px",
  color: "#e2e8f0",
  fontSize: "1rem",
  boxSizing: "border-box",
  minHeight: 48,
  outline: "none",
};
const addBtnStyle = (disabled) => ({
  padding: "12px 20px",
  minHeight: 48,
  background: disabled ? "rgba(255,255,255,0.05)" : "rgba(99,102,241,0.25)",
  border: "1px solid rgba(99,102,241,0.3)",
  borderRadius: 8,
  color: disabled ? "rgba(255,255,255,0.3)" : "#a5b4fc",
  fontWeight: 600,
  fontSize: "0.9rem",
  cursor: disabled ? "not-allowed" : "pointer",
  whiteSpace: "nowrap",
  flexShrink: 0,
});
const avgTicketStyle = {
  fontSize: "0.85rem",
  color: "rgba(255,255,255,0.35)",
  marginBottom: 8,
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
