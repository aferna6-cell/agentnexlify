import { useState, useEffect, useCallback } from "react";
import {
  updateWidgetConfig,
  fetchFaqEntries,
  createFaqEntry,
  deleteFaqEntry,
} from "../../utils/api";

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

const COLOR_SWATCHES = [
  "#00BFFF", "#6366F1", "#8B5CF6", "#EC4899",
  "#EF4444", "#F59E0B", "#10B981", "#14B8A6",
];

const PLATFORM_INSTRUCTIONS = {
  HTML: "Paste this snippet before the closing </body> tag of your website.",
  WordPress:
    "Go to Appearance > Theme Editor > footer.php and paste the snippet before </body>. Or use a plugin like 'Insert Headers and Footers'.",
  Shopify:
    "Go to Online Store > Themes > Edit Code > theme.liquid and paste before </body>.",
  Wix: "Go to Settings > Custom Code > Add Custom Code and paste as Body - End.",
};

function computeSteps(dashData, stored) {
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
      complete: !!stored.installedDone,
    },
    {
      key: "test",
      title: "Test It Out",
      description: "Preview and chat with your widget",
      complete: !!stored.testDone,
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
  const [copied, setCopied] = useState(false);
  const [platform, setPlatform] = useState("HTML");
  const [showPreview, setShowPreview] = useState(false);

  const steps = computeSteps(dashData, stored);
  // "live" step is complete when all previous 5 are complete
  const prevComplete = steps.slice(0, 5).every((s) => s.complete);
  steps[5].complete = prevComplete;

  const completedCount = steps.filter((s) => s.complete).length;
  const allDone = completedCount === 6;

  // Initialize form state from dashData
  useEffect(() => {
    const wc = dashData?.widget_config || {};
    setGreeting(wc.greeting_message || DEFAULT_GREETING);
    setSelectedColor(wc.primary_color || DEFAULT_COLOR);
    setPosition(wc.position || "bottom-right");
  }, [dashData]);

  // Load FAQ entries when agent step opens
  useEffect(() => {
    if (activeStep === "agent" && tenantId && token) {
      fetchFaqEntries(tenantId, token)
        .then(setFaqEntries)
        .catch(() => {});
    }
  }, [activeStep, tenantId, token]);

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
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (stored.dismissed && !allDone) {
    return null;
  }

  const handleSaveAgent = async () => {
    setSaving(true);
    try {
      await updateWidgetConfig(tenantId, token, {
        greeting_message: greeting,
      });
      onStepComplete?.();
    } catch (e) {
      console.error("Failed to save greeting:", e);
    } finally {
      setSaving(false);
    }
  };

  const handleAddFaq = async () => {
    if (!newFaqQ.trim() || !newFaqA.trim()) return;
    setSaving(true);
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
      console.error("Failed to delete FAQ:", e);
    }
  };

  const handleSaveAppearance = async () => {
    setSaving(true);
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
      console.error("Failed to save appearance:", e);
    } finally {
      setSaving(false);
    }
  };

  const embedCode = `<script src="https://app.agentnexlify.com/widget/agentnexlify-widget.js" data-api-key="${dashData?.widget_api_key || "your-api-key"}"></script>`;

  const handleCopyEmbed = () => {
    navigator.clipboard.writeText(embedCode).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleMarkInstalled = () => {
    updateStored({ installedDone: true });
    onStepComplete?.();
  };

  const handleTestPreview = () => {
    setShowPreview(true);
    updateStored({ testDone: true });
    onStepComplete?.();
  };

  const handleDismiss = () => {
    updateStored({ dismissed: true });
    onDismiss?.();
  };

  const handleFinish = () => {
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
                  Add FAQ
                </button>
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
                  </span>
                  <span className="code-tag">&gt;&lt;/script&gt;</span>
                </code>
              </pre>
              <button className="widget-copy-btn" onClick={handleCopyEmbed}>
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <button
              className="onboarding-save-btn"
              onClick={handleMarkInstalled}
            >
              Mark as Installed
            </button>
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
                  srcDoc={`<!DOCTYPE html>
<html>
<head><style>body{margin:0;background:#1a1a2e;height:100vh;font-family:sans-serif;display:flex;align-items:center;justify-content:center;color:#aaa;}p{text-align:center;font-size:14px;}</style></head>
<body>
<p>Widget preview loading...</p>
<script src="https://app.agentnexlify.com/widget/agentnexlify-widget.js" data-api-key="${dashData?.widget_api_key || ""}"></script>
</body>
</html>`}
                />
              </div>
            )}
          </div>
        );

      case "live":
        return (
          <div className="onboarding-step-body onboarding-live">
            <div className="onboarding-celebration">
              <span className="celebration-emoji">&#127881;</span>
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
            {completedCount} of {steps.length} steps complete
          </span>
        </div>
        <div className="onboarding-header-right">
          <div className="onboarding-progress-bar">
            <div
              className="onboarding-progress-fill"
              style={{ width: `${(completedCount / steps.length) * 100}%` }}
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
