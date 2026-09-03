import { useState, useEffect, useCallback } from "react";
import { updateWidgetConfig } from "../../utils/api/widget-config";
import { fetchFaqEntries, createFaqEntry, deleteFaqEntry } from "../../utils/api/faq";
import { fetchAvailability, updateAvailability } from "../../utils/api/appointments";
import { updateTenantSettings } from "../../utils/api/dashboard";
import { createFromTemplate, fetchSequences } from "../../utils/api/automations";
import { trackEvent } from "../../utils/analytics";
import { getWebsiteConnection, verifyWebsiteConnection } from "../../utils/api/websiteConnect";

const STORAGE_KEY_PREFIX = "anx_onboarding_";

function getStoredState(tenantId) {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${tenantId}`);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function setStoredState(tenantId, state) {
  localStorage.setItem(
    `${STORAGE_KEY_PREFIX}${tenantId}`,
    JSON.stringify(state)
  );
}

const DEFAULT_GREETING = "Hi! How can I help you today?";
const DEFAULT_COLOR = "#00BFFF";

const DAYS_OF_WEEK = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
const DEFAULT_HOURS = Object.fromEntries(
  DAYS_OF_WEEK.map((d) => [d, { enabled: ["monday", "tuesday", "wednesday", "thursday", "friday"].includes(d), start: "09:00", end: "17:00" }])
);

const COLOR_SWATCHES = [
  "#00BFFF", "#6366F1", "#8B5CF6", "#EC4899",
  "#EF4444", "#F59E0B", "#10B981", "#14B8A6",
];

const PLATFORM_INSTRUCTIONS = {
  WordPress:
    "Download the AgentNexLiFy plugin, activate it, then paste your public widget key under Settings → AgentNexLiFy. Theme-file paste is the fallback only.",
  Wix: "Go to Settings > Custom Code > Add Custom Code and paste as Body - End.",
  Squarespace:
    "Go to Settings → Developer Tools → Code Injection and paste the snippet in Footer.",
  GoDaddy:
    "In GoDaddy Website Builder, add an HTML section and paste the snippet.",
  Custom: "Paste this snippet before the closing </body> tag of your website.",
};

function computeSteps(dashData, stored, websiteConnected) {
  const wc = dashData?.widget_config || {};
  const defaultBotSuffix = " Assistant";
  const businessName = dashData?.business_name || "";
  const defaultBotName = `${businessName}${defaultBotSuffix}`;

  return [
    {
      key: "business",
      title: "Welcome & Business Info",
      description: "Confirm your business details",
      complete: !!businessName && businessName !== "My Business",
    },
    {
      key: "hours",
      title: "Set Business Hours",
      description: "Tell customers when you're available",
      complete: !!stored.hoursDone,
    },
    {
      key: "agent",
      title: "Configure AI Agent",
      description: "Set up greeting message and FAQ answers",
      complete:
        (wc.greeting_message && wc.greeting_message !== DEFAULT_GREETING) ||
        (dashData?.faq_count || 0) > 0,
    },
    {
      key: "appearance",
      title: "Customize Appearance",
      description: "Choose your brand color and widget position",
      complete:
        (wc.primary_color && wc.primary_color !== DEFAULT_COLOR) ||
        (wc.bot_name && wc.bot_name !== defaultBotName),
    },
    {
      key: "install",
      title: "Install Widget",
      description: "Add the embed code to your website",
      complete: !!websiteConnected,
    },
    {
      key: "test",
      title: "Test It Out",
      description: "Preview and chat with your widget",
      complete: !!stored.testDone,
    },
    {
      key: "automations",
      title: "Set Up Automations",
      description: "Auto-follow-up with new leads",
      complete: !!stored.automationsDone || (dashData?.sequence_count || 0) > 0,
    },
    {
      key: "live",
      title: "You're Live!",
      description: "Your AI assistant is ready",
      complete: false, // Computed below from all others
    },
  ];
}

export default function OnboardingChecklist({
  dashData,
  tenantId,
  token,
  onNavigate,
  onDismiss,
  onStepComplete,
  onboardingStatus,
}) {
  const [stored, setStored] = useState(() => getStoredState(tenantId));
  const [expanded, setExpanded] = useState(true);
  const [activeStep, setActiveStep] = useState(null);

  // Step-specific state
  const [greeting, setGreeting] = useState("");
  const [faqEntries, setFaqEntries] = useState([]);
  const [newFaqQ, setNewFaqQ] = useState("");
  const [newFaqA, setNewFaqA] = useState("");
  const [selectedColor, setSelectedColor] = useState(DEFAULT_COLOR);
  const [customColor, setCustomColor] = useState("");
  const [position, setPosition] = useState("bottom-right");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [faqError, setFaqError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [platform, setPlatform] = useState("WordPress");
  const [websiteConnected, setWebsiteConnected] = useState(false);
  const [verifyingInstall, setVerifyingInstall] = useState(false);
  const [verifyInstallError, setVerifyInstallError] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const [creatingSequence, setCreatingSequence] = useState(false);
  const [sequenceCreated, setSequenceCreated] = useState(false);
  const [sequenceError, setSequenceError] = useState(null);
  const [existingSequences, setExistingSequences] = useState(null);
  const [textbackEnabled, setTextbackEnabled] = useState(false);
  const [savingTextback, setSavingTextback] = useState(false);
  const [businessHours, setBusinessHours] = useState(DEFAULT_HOURS);
  const [hoursLoaded, setHoursLoaded] = useState(false);
  const [newService, setNewService] = useState("");
  const [services, setServices] = useState([]);
  const [addingService, setAddingService] = useState(false);

  const steps = computeSteps(dashData, stored, websiteConnected);

  // Merge API-driven onboarding status into steps if available
  if (onboardingStatus?.steps) {
    const apiSteps = onboardingStatus.steps;
    for (const step of steps) {
      if (apiSteps[step.key] !== undefined) {
        // API says done? Override to true. Local already true? Keep it.
        step.complete = step.complete || apiSteps[step.key];
      }
    }
  }

  // "live" step is complete when all previous 6 are complete
  const liveIdx = steps.findIndex((s) => s.key === "live");
  const prevComplete = steps.slice(0, liveIdx).every((s) => s.complete);
  steps[liveIdx].complete = prevComplete;

  const completedCount = steps.filter((s) => s.complete).length;
  const totalSteps = steps.length;

  // Always compute percentage from frontend steps to match the displayed count
  const completionPct = Math.round((completedCount / totalSteps) * 100);

  const allDone = completedCount === totalSteps;

  // Initialize form state from dashData
  useEffect(() => {
    const wc = dashData?.widget_config || {};
    setGreeting(wc.greeting_message || DEFAULT_GREETING);
    setSelectedColor(wc.primary_color || DEFAULT_COLOR);
    setPosition(wc.position || "bottom-right");
  }, [dashData]);

  useEffect(() => {
    if (!token) return;
    getWebsiteConnection(token)
      .then((payload) => {
        const status = payload?.connection?.status || payload?.status;
        setWebsiteConnected(status === "connected");
      })
      .catch(() => setWebsiteConnected(false));
  }, [token]);

  // Load FAQ entries when agent step opens
  useEffect(() => {
    if (activeStep === "agent" && tenantId && token) {
      fetchFaqEntries(tenantId, token)
        .then(setFaqEntries)
        .catch((err) => {
          console.warn("Failed to load FAQ entries:", err.message || err);
          setFaqError("Could not load FAQ entries. Try again later.");
        });
    }
  }, [activeStep, tenantId, token]);

  // Load business hours when hours step opens
  useEffect(() => {
    if (activeStep === "hours" && tenantId && token && !hoursLoaded) {
      fetchAvailability(tenantId, token)
        .then((data) => {
          if (data?.hours) {
            setBusinessHours((prev) => ({ ...prev, ...data.hours }));
          }
          setHoursLoaded(true);
        })
        .catch((err) => { console.warn("Business hours fetch failed:", err?.message); setHoursLoaded(true); });
    }
  }, [activeStep, tenantId, token, hoursLoaded]);

  // Load existing sequences + textback state when automations step opens
  useEffect(() => {
    if (activeStep === "automations" && tenantId && token) {
      fetchSequences(tenantId, token)
        .then((data) => {
          const seqs = data.sequences || data || [];
          setExistingSequences(seqs);
          if (seqs.length > 0) {
            setSequenceCreated(true);
          }
        })
        .catch((err) => {
          console.warn("Failed to load sequences:", err.message || err);
          setExistingSequences([]);
        });
      // Load textback state from dashData
      if (dashData?.textback_enabled !== undefined) {
        setTextbackEnabled(!!dashData.textback_enabled);
      }
    }
  }, [activeStep, tenantId, token, dashData?.textback_enabled]);

  const updateStored = useCallback(
    (patch) => {
      setStored((prev) => {
        const next = { ...prev, ...patch };
        setStoredState(tenantId, next);
        return next;
      });
    },
    [tenantId]
  );

  // Find first incomplete step to auto-open
  useEffect(() => {
    if (activeStep === null && !allDone) {
      const first = steps.find((s) => !s.complete);
      if (first) setActiveStep(first.key);
    }
  }, [steps, allDone, activeStep]);

  if (stored.dismissed && !allDone) {
    return null;
  }

  const handleSaveAgent = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      await updateWidgetConfig(tenantId, token, {
        greeting_message: greeting,
      });
      onStepComplete?.();
    } catch (e) {
      console.warn("Failed to save greeting:", e.message || e);
      setSaveError(e.body?.detail || e.message || "Failed to save greeting. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveHours = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      await updateAvailability(tenantId, token, { hours: businessHours });
      updateStored({ hoursDone: true });
      onStepComplete?.();
    } catch (e) {
      console.warn("Failed to save hours:", e.message || e);
      setSaveError(e.body?.detail || e.message || "Failed to save business hours.");
    } finally {
      setSaving(false);
    }
  };

  const handleToggleTextback = async (enabled) => {
    setTextbackEnabled(enabled);
    setSavingTextback(true);
    try {
      await updateTenantSettings(tenantId, token, { textback_enabled: enabled });
    } catch (e) {
      setTextbackEnabled(!enabled);
      console.warn("Failed to toggle textback:", e.message || e);
    } finally {
      setSavingTextback(false);
    }
  };

  const handleAddService = async () => {
    if (!newService.trim()) return;
    setAddingService(true);
    setFaqError(null);
    try {
      const entry = await createFaqEntry(tenantId, token, {
        question: `Do you offer ${newService.trim()}?`,
        answer: `Yes, we offer ${newService.trim()}. Contact us for more details or to schedule an appointment.`,
        category: "services",
      });
      setFaqEntries((prev) => [...prev, entry]);
      setServices((prev) => [...prev, newService.trim()]);
      setNewService("");
      onStepComplete?.();
    } catch (e) {
      setFaqError(e.body?.detail || e.message || "Failed to add service");
    } finally {
      setAddingService(false);
    }
  };

  const handleAddFaq = async () => {
    if (!newFaqQ.trim() || !newFaqA.trim()) return;
    setSaving(true);
    setFaqError(null);
    try {
      const entry = await createFaqEntry(tenantId, token, {
        question: newFaqQ.trim(),
        answer: newFaqA.trim(),
      });
      setFaqEntries((prev) => [...prev, entry]);
      setNewFaqQ("");
      setNewFaqA("");
      onStepComplete?.();
    } catch (e) {
      console.error("Failed to create FAQ:", e);
      setFaqError(e.body?.detail || e.message || "Failed to save FAQ entry");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteFaq = async (faqId) => {
    try {
      await deleteFaqEntry(tenantId, token, faqId);
      setFaqEntries((prev) => prev.filter((f) => f.id !== faqId));
      onStepComplete?.();
    } catch (e) {
      console.warn("Failed to delete FAQ:", e.message || e);
      setFaqError(e.body?.detail || e.message || "Failed to delete FAQ entry. Please try again.");
    }
  };

  const handleSaveAppearance = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const color = customColor.match(/^#[0-9a-fA-F]{6}$/)
        ? customColor
        : selectedColor;
      await updateWidgetConfig(tenantId, token, {
        primary_color: color,
        position,
      });
      setSelectedColor(color);
      setCustomColor("");
      onStepComplete?.();
    } catch (e) {
      console.warn("Failed to save appearance:", e.message || e);
      setSaveError(e.body?.detail || e.message || "Failed to save appearance. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const apiBase = import.meta.env.VITE_API_BASE_URL || "https://agentnexlify-production.up.railway.app";
  const embedCode = `<script async src="https://app.agentnexlify.com/widget/agentnexlify-widget.js" data-api-key="${dashData?.widget_api_key || "your-api-key"}" data-api-base="${apiBase}"></script>`;

  const handleCopyEmbed = () => {
    navigator.clipboard.writeText(embedCode).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleVerifyInstalled = async () => {
    if (!token) {
      onNavigate?.("website_connect");
      return;
    }
    setVerifyingInstall(true);
    setVerifyInstallError(null);
    try {
      const payload = await verifyWebsiteConnection(token);
      const connected = (payload?.status || payload?.connection?.status) === "connected";
      setWebsiteConnected(connected);
      if (connected) onStepComplete?.();
      else setVerifyInstallError(payload?.verification_detail || "Widget not found on the live site yet.");
    } catch (e) {
      setVerifyInstallError(e.body?.detail || e.message || "Connect your website first, then verify.");
    } finally {
      setVerifyingInstall(false);
    }
  };

  const handleTestPreview = () => {
    setShowPreview(true);
    updateStored({ testDone: true });
    onStepComplete?.();
  };

  const handleCreateDefaultSequence = async () => {
    setCreatingSequence(true);
    setSequenceError(null);
    try {
      await createFromTemplate(tenantId, token, "welcome");
      setSequenceCreated(true);
      updateStored({ automationsDone: true });
      onStepComplete?.();
    } catch (e) {
      console.warn("Failed to create default sequence:", e.message || e);
      setSequenceError(e.body?.detail || e.message || "Failed to create automation sequence. Please try again.");
    } finally {
      setCreatingSequence(false);
    }
  };

  const handleDismiss = () => {
    updateStored({ dismissed: true });
    onDismiss?.();
  };

  const handleFinish = () => {
    trackEvent("onboarding_complete");
    updateStored({ dismissed: true });
    onDismiss?.();
  };

  const renderStepContent = (step) => {
    switch (step.key) {
      case "business":
        return (
          <div className="onboarding-step-body">
            <div className="onboarding-info-row">
              <span className="onboarding-info-label">Business Name</span>
              <span className="onboarding-info-value">
                {dashData?.business_name || "Not set"}
              </span>
            </div>
            <div className="onboarding-info-row">
              <span className="onboarding-info-label">Plan</span>
              <span className="onboarding-info-value">
                {(dashData?.plan || "free").charAt(0).toUpperCase() +
                  (dashData?.plan || "free").slice(1)}
              </span>
            </div>
            <p className="onboarding-hint">
              Business info was set during signup. You can update it from
              Settings.
            </p>
          </div>
        );

      case "hours":
        return (
          <div className="onboarding-step-body">
            <p className="onboarding-hint">
              Set your business hours so the AI knows when you're available and can inform visitors.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {DAYS_OF_WEEK.map((day) => {
                const cfg = businessHours[day] || { enabled: false, start: "09:00", end: "17:00" };
                return (
                  <div key={day} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0", borderBottom: "1px solid var(--border, #2a2a3e)" }}>
                    <label style={{ display: "flex", alignItems: "center", gap: 6, width: 120, cursor: "pointer", fontSize: "0.85rem", color: cfg.enabled ? "var(--text-primary)" : "var(--text-muted)" }}>
                      <input
                        type="checkbox"
                        checked={cfg.enabled}
                        onChange={(e) => setBusinessHours((prev) => ({ ...prev, [day]: { ...prev[day], enabled: e.target.checked } }))}
                        style={{ width: "auto" }}
                      />
                      {day.charAt(0).toUpperCase() + day.slice(1)}
                    </label>
                    {cfg.enabled && (
                      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem" }}>
                        <input
                          type="time"
                          value={cfg.start}
                          onChange={(e) => setBusinessHours((prev) => ({ ...prev, [day]: { ...prev[day], start: e.target.value } }))}
                          className="onboarding-input"
                          style={{ width: 110, padding: "4px 6px", fontSize: "0.82rem" }}
                        />
                        <span style={{ color: "var(--text-muted)" }}>to</span>
                        <input
                          type="time"
                          value={cfg.end}
                          onChange={(e) => setBusinessHours((prev) => ({ ...prev, [day]: { ...prev[day], end: e.target.value } }))}
                          className="onboarding-input"
                          style={{ width: 110, padding: "4px 6px", fontSize: "0.82rem" }}
                        />
                      </div>
                    )}
                    {!cfg.enabled && (
                      <span style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>Closed</span>
                    )}
                  </div>
                );
              })}
            </div>
            <button
              className="onboarding-save-btn"
              onClick={handleSaveHours}
              disabled={saving}
              style={{ marginTop: 12 }}
            >
              {saving ? "Saving..." : "Save Business Hours"}
            </button>
            {saveError && <div className="onboarding-error">{saveError}</div>}
          </div>
        );

      case "agent":
        return (
          <div className="onboarding-step-body">
            <label className="onboarding-field-label">Greeting Message</label>
            <textarea
              className="onboarding-textarea"
              value={greeting}
              onChange={(e) => setGreeting(e.target.value)}
              rows={3}
              placeholder="Hi! How can I help you today?"
            />
            <button
              className="onboarding-save-btn"
              onClick={handleSaveAgent}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save Greeting"}
            </button>
            {saveError && (
              <div className="onboarding-error">{saveError}</div>
            )}

            <div className="onboarding-faq-section" style={{ marginTop: 12 }}>
              <label className="onboarding-field-label">Your Services</label>
              <p className="onboarding-hint" style={{ marginBottom: 6, fontSize: "0.82rem" }}>
                Add your services so the AI can answer questions about what you offer.
              </p>
              {services.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
                  {services.map((s, i) => (
                    <span key={i} style={{ display: "inline-block", padding: "4px 10px", borderRadius: 14, fontSize: "0.78rem", background: "var(--accent-dim, rgba(0,191,255,0.15))", color: "var(--accent, #00BFFF)", border: "1px solid var(--accent-dim, rgba(0,191,255,0.25))" }}>
                      {s}
                    </span>
                  ))}
                </div>
              )}
              <div style={{ display: "flex", gap: 6 }}>
                <input
                  className="onboarding-input"
                  placeholder="e.g. Plumbing Repair, Drain Cleaning"
                  value={newService}
                  onChange={(e) => setNewService(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddService()}
                  style={{ flex: 1 }}
                />
                <button
                  className="onboarding-add-btn"
                  onClick={handleAddService}
                  disabled={addingService || !newService.trim()}
                >
                  {addingService ? "Adding..." : "Add"}
                </button>
              </div>
            </div>

            <div className="onboarding-faq-section">
              <label className="onboarding-field-label">
                FAQ Entries ({faqEntries.length})
              </label>
              {faqEntries.map((faq) => (
                <div className="onboarding-faq-item" key={faq.id}>
                  <div className="onboarding-faq-q">Q: {faq.question}</div>
                  <div className="onboarding-faq-a">A: {faq.answer}</div>
                  <button
                    className="onboarding-faq-delete"
                    onClick={() => handleDeleteFaq(faq.id)}
                  >
                    Remove
                  </button>
                </div>
              ))}
              <div className="onboarding-faq-form">
                <input
                  className="onboarding-input"
                  placeholder="Question"
                  value={newFaqQ}
                  onChange={(e) => setNewFaqQ(e.target.value)}
                />
                <input
                  className="onboarding-input"
                  placeholder="Answer"
                  value={newFaqA}
                  onChange={(e) => setNewFaqA(e.target.value)}
                />
                <button
                  className="onboarding-add-btn"
                  onClick={handleAddFaq}
                  disabled={saving || !newFaqQ.trim() || !newFaqA.trim()}
                >
                  {saving ? "Adding..." : "Add FAQ"}
                </button>
                {faqError && (
                  <div className="onboarding-error">{faqError}</div>
                )}
              </div>
            </div>
          </div>
        );

      case "appearance":
        return (
          <div className="onboarding-step-body">
            <label className="onboarding-field-label">Brand Color</label>
            <div className="color-swatches">
              {COLOR_SWATCHES.map((c) => (
                <button
                  key={c}
                  className={`color-swatch${selectedColor === c ? " active" : ""}`}
                  style={{ background: c }}
                  onClick={() => {
                    setSelectedColor(c);
                    setCustomColor("");
                  }}
                />
              ))}
              <input
                className="onboarding-color-input"
                type="text"
                placeholder="#hex"
                value={customColor}
                onChange={(e) => setCustomColor(e.target.value)}
                maxLength={7}
              />
            </div>

            <label className="onboarding-field-label">Widget Position</label>
            <div className="onboarding-radio-group">
              <label className="onboarding-radio">
                <input
                  type="radio"
                  name="position"
                  value="bottom-right"
                  checked={position === "bottom-right"}
                  onChange={() => setPosition("bottom-right")}
                />
                Bottom Right
              </label>
              <label className="onboarding-radio">
                <input
                  type="radio"
                  name="position"
                  value="bottom-left"
                  checked={position === "bottom-left"}
                  onChange={() => setPosition("bottom-left")}
                />
                Bottom Left
              </label>
            </div>

            <div className="onboarding-mini-preview">
              <div className="mini-preview-window">
                <div
                  className={`mini-preview-bubble ${position}`}
                  style={{
                    background:
                      customColor.match(/^#[0-9a-fA-F]{6}$/)
                        ? customColor
                        : selectedColor,
                  }}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
                    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
                  </svg>
                </div>
              </div>
            </div>

            <button
              className="onboarding-save-btn"
              onClick={handleSaveAppearance}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save Appearance"}
            </button>
            {saveError && (
              <div className="onboarding-error">{saveError}</div>
            )}
          </div>
        );

      case "install":
        return (
          <div className="onboarding-step-body">
            <div className="platform-tabs">
              {Object.keys(PLATFORM_INSTRUCTIONS).map((p) => (
                <button
                  key={p}
                  className={`platform-tab${platform === p ? " active" : ""}`}
                  onClick={() => setPlatform(p)}
                >
                  {p}
                </button>
              ))}
            </div>
            <p className="onboarding-hint">{PLATFORM_INSTRUCTIONS[platform]}</p>
            <div className="widget-code-block">
              <pre>
                <code>
                  <span className="code-tag">&lt;script</span>{" "}
                  <span className="code-attr">src</span>=
                  <span className="code-string">
                    "https://app.agentnexlify.com/widget/agentnexlify-widget.js"
                  </span>{" "}
                  <span className="code-attr">data-api-key</span>=
                  <span className="code-string">
                    "{dashData?.widget_api_key || "your-api-key"}"
                  </span>{" "}
                  <span className="code-attr">data-api-base</span>=
                  <span className="code-string">
                    "{apiBase}"
                  </span>
                  <span className="code-tag">&gt;&lt;/script&gt;</span>
                </code>
              </pre>
              <button className="widget-copy-btn" onClick={handleCopyEmbed}>
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            {verifyInstallError && (
              <div className="onboarding-error">{verifyInstallError}</div>
            )}
            {websiteConnected ? (
              <p className="onboarding-hint">Verified on your live website.</p>
            ) : (
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button
                  className="onboarding-save-btn"
                  onClick={handleVerifyInstalled}
                  disabled={verifyingInstall}
                >
                  {verifyingInstall ? "Verifying…" : "Verify on my website"}
                </button>
                <button
                  className="onboarding-save-btn"
                  type="button"
                  onClick={() => onNavigate?.("website_connect")}
                >
                  Open Connect website
                </button>
              </div>
            )}
          </div>
        );

      case "test":
        return (
          <div className="onboarding-step-body">
            <p className="onboarding-hint">
              Click below to preview your widget and try chatting with your AI
              assistant.
            </p>
            {!showPreview ? (
              <button
                className="onboarding-save-btn"
                onClick={handleTestPreview}
              >
                Preview Widget
              </button>
            ) : (
              <div className="onboarding-preview-container">
                <iframe
                  title="Widget Preview"
                  className="onboarding-preview-iframe"
                  src={`https://app.agentnexlify.com/widget/preview.html?key=${encodeURIComponent(dashData?.widget_api_key || "")}&base=${encodeURIComponent(apiBase)}`}
                />
              </div>
            )}
          </div>
        );

      case "automations":
        return (
          <div className="onboarding-step-body">
            <p className="onboarding-hint">
              Automations let your AI follow up with new leads automatically.
              Create a welcome email sequence so every lead hears from you
              within minutes - no manual work needed.
            </p>
            {existingSequences === null ? (
              <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-muted)", fontSize: "0.85rem" }}>
                <span className="onboarding-spinner" /> Loading sequences...
              </div>
            ) : sequenceCreated || (existingSequences && existingSequences.length > 0) ? (
              <div className="onboarding-automation-done">
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <circle cx="10" cy="10" r="10" fill="var(--green)" />
                    <path d="M6 10l3 3 5-6" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--green)" }}>
                    {existingSequences && existingSequences.length > 0
                      ? `${existingSequences.length} automation sequence${existingSequences.length > 1 ? "s" : ""} active`
                      : "Welcome sequence created"}
                  </span>
                </div>
                <button
                  className="onboarding-add-btn"
                  onClick={() => onNavigate?.("automations")}
                >
                  View Automations
                </button>
              </div>
            ) : (
              <>
                <div className="onboarding-automation-preview">
                  <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: 8 }}>
                    Welcome Email Sequence
                  </div>
                  <div className="automation-preview-steps">
                    <div className="automation-preview-step">
                      <span className="automation-step-badge">1</span>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                        Instant welcome email when a new lead arrives
                      </span>
                    </div>
                    <div className="automation-preview-connector" />
                    <div className="automation-preview-step">
                      <span className="automation-step-badge">2</span>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                        Follow-up email after 24 hours if no reply
                      </span>
                    </div>
                    <div className="automation-preview-connector" />
                    <div className="automation-preview-step">
                      <span className="automation-step-badge">3</span>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                        Final check-in after 3 days
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  className="onboarding-save-btn"
                  onClick={handleCreateDefaultSequence}
                  disabled={creatingSequence}
                >
                  {creatingSequence ? "Creating..." : "Create Default Sequences"}
                </button>
                {sequenceError && (
                  <div className="onboarding-error">{sequenceError}</div>
                )}
                <button
                  className="onboarding-add-btn"
                  onClick={() => {
                    updateStored({ automationsDone: true });
                    onStepComplete?.();
                    onNavigate?.("automations");
                  }}
                  style={{ marginTop: 4 }}
                >
                  Skip - I'll set up my own
                </button>
              </>
            )}

            {/* Missed Call Text-Back */}
            <div style={{ marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--border, #2a2a3e)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>Missed Call Text-Back</div>
                  <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 2 }}>Auto-text callers when you miss their call</div>
                </div>
                <button
                  className={textbackEnabled ? "btn-sm" : "btn-sm"}
                  onClick={() => handleToggleTextback(!textbackEnabled)}
                  disabled={savingTextback}
                  style={{
                    background: textbackEnabled ? "var(--green, #22c55e)" : "var(--bg-darker, #1a1a2e)",
                    minWidth: 60,
                    fontSize: "0.78rem",
                  }}
                >
                  {savingTextback ? "..." : textbackEnabled ? "On" : "Off"}
                </button>
              </div>
            </div>
          </div>
        );

      case "live":
        return (
          <div className="onboarding-step-body onboarding-live">
            <div className="onboarding-celebration">
              <span className="celebration-emoji">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>
              </span>
              <h3>Congratulations!</h3>
              <p>Your AI assistant is live and ready to capture leads.</p>
            </div>
            <div className="onboarding-next-steps">
              <button
                className="onboarding-next-btn"
                onClick={() => onNavigate?.("automations")}
              >
                Set up Automations
              </button>
              <button
                className="onboarding-next-btn"
                onClick={() => onNavigate?.("leads")}
              >
                View Leads
              </button>
              <button
                className="onboarding-next-btn"
                onClick={() => onNavigate?.("billing")}
              >
                Manage Billing
              </button>
            </div>
            <button className="onboarding-finish-btn" onClick={handleFinish}>
              Close Setup
            </button>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="onboarding-checklist">
      <div className="onboarding-header">
        <div className="onboarding-header-left">
          <h3 className="onboarding-title">
            {allDone ? "Setup Complete" : "Get Started"}
          </h3>
          <span className="onboarding-progress-text">
            {completedCount} of {totalSteps} steps complete ({completionPct}%)
          </span>
        </div>
        <div className="onboarding-header-right">
          <div className="onboarding-progress-bar">
            <div
              className="onboarding-progress-fill"
              style={{ width: `${completionPct}%` }}
            />
          </div>
          <button
            className="onboarding-toggle"
            onClick={() => setExpanded((e) => !e)}
          >
            {expanded ? "Collapse" : "Expand"}
          </button>
          {!allDone && (
            <button className="onboarding-dismiss" onClick={handleDismiss}>
              Dismiss
            </button>
          )}
        </div>
      </div>

      {expanded && (
        <div className="onboarding-steps">
          {steps.map((step, i) => {
            const isActive = activeStep === step.key;
            const isClickable =
              step.key === "live" ? prevComplete : true;

            return (
              <div
                className={`onboarding-step${step.complete ? " complete" : ""}${isActive ? " active" : ""}`}
                key={step.key}
              >
                <div
                  className="onboarding-step-header"
                  onClick={() =>
                    isClickable &&
                    setActiveStep(isActive ? null : step.key)
                  }
                  style={{ cursor: isClickable ? "pointer" : "default" }}
                >
                  <div className="onboarding-step-icon">
                    {step.complete ? (
                      <svg
                        width="20"
                        height="20"
                        viewBox="0 0 20 20"
                        fill="none"
                      >
                        <circle cx="10" cy="10" r="10" fill="var(--green)" />
                        <path
                          d="M6 10l3 3 5-6"
                          stroke="white"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    ) : (
                      <span className="onboarding-step-number">{i + 1}</span>
                    )}
                  </div>
                  <div className="onboarding-step-info">
                    <div className="onboarding-step-title">{step.title}</div>
                    <div className="onboarding-step-desc">
                      {step.description}
                    </div>
                  </div>
                  <span className="onboarding-step-chevron">
                    {isActive ? "\u25B2" : "\u25BC"}
                  </span>
                </div>
                {isActive && (
                  <div className="onboarding-step-content">
                    {renderStepContent(step)}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
