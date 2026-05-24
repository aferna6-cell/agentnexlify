import { useState, useEffect, useCallback } from "react";
import { updateWidgetConfig } from "../../../utils/api/widget-config";
import {
  fetchFaqEntries,
  createFaqEntry,
  deleteFaqEntry,
} from "../../../utils/api/faq";
import {
  fetchAvailability,
  updateAvailability,
} from "../../../utils/api/appointments";
import { updateTenantSettings } from "../../../utils/api/dashboard";
import {
  createFromTemplate,
  fetchSequences,
} from "../../../utils/api/automations";
import { trackEvent } from "../../../utils/analytics";
import { DEFAULT_GREETING, DEFAULT_COLOR, DEFAULT_HOURS } from "./constants";
import { getStoredState, setStoredState } from "./storage";
import { computeSteps } from "./steps";
import BusinessStep from "./BusinessStep";
import HoursStep from "./HoursStep";
import AgentStep from "./AgentStep";
import AppearanceStep from "./AppearanceStep";
import InstallStep from "./InstallStep";
import TestStep from "./TestStep";
import AutomationsStep from "./AutomationsStep";
import LiveStep from "./LiveStep";
import StepRow from "./StepRow";

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
  const [platform, setPlatform] = useState("HTML");
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

  const steps = computeSteps(dashData, stored);

  if (onboardingStatus?.steps) {
    const apiSteps = onboardingStatus.steps;
    for (const step of steps) {
      if (apiSteps[step.key] !== undefined) {
        step.complete = step.complete || apiSteps[step.key];
      }
    }
  }

  const liveIdx = steps.findIndex((s) => s.key === "live");
  const prevComplete = steps.slice(0, liveIdx).every((s) => s.complete);
  steps[liveIdx].complete = prevComplete;

  const completedCount = steps.filter((s) => s.complete).length;
  const totalSteps = steps.length;
  const completionPct = Math.round((completedCount / totalSteps) * 100);
  const allDone = completedCount === totalSteps;

  useEffect(() => {
    const wc = dashData?.widget_config || {};
    setGreeting(wc.greeting_message || DEFAULT_GREETING);
    setSelectedColor(wc.primary_color || DEFAULT_COLOR);
    setPosition(wc.position || "bottom-right");
  }, [dashData]);

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

  useEffect(() => {
    if (activeStep === "hours" && tenantId && token && !hoursLoaded) {
      fetchAvailability(tenantId, token)
        .then((data) => {
          if (data?.hours) {
            setBusinessHours((prev) => ({ ...prev, ...data.hours }));
          }
          setHoursLoaded(true);
        })
        .catch((err) => {
          console.warn("Business hours fetch failed:", err?.message);
          setHoursLoaded(true);
        });
    }
  }, [activeStep, tenantId, token, hoursLoaded]);

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
    [tenantId],
  );

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
      setSaveError(
        e.body?.detail ||
          e.message ||
          "Failed to save greeting. Please try again.",
      );
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
      setSaveError(
        e.body?.detail || e.message || "Failed to save business hours.",
      );
    } finally {
      setSaving(false);
    }
  };

  const handleToggleTextback = async (enabled) => {
    setTextbackEnabled(enabled);
    setSavingTextback(true);
    try {
      await updateTenantSettings(tenantId, token, {
        textback_enabled: enabled,
      });
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
      setFaqError(
        e.body?.detail ||
          e.message ||
          "Failed to delete FAQ entry. Please try again.",
      );
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
      setSaveError(
        e.body?.detail ||
          e.message ||
          "Failed to save appearance. Please try again.",
      );
    } finally {
      setSaving(false);
    }
  };

  const apiBase =
    import.meta.env.VITE_API_BASE_URL ||
    "https://agentnexlify-production.up.railway.app";
  const apiKey = dashData?.widget_api_key || "your-api-key";
  const embedCode = `<script async src="https://app.agentnexlify.com/widget/agentnexlify-widget.js" data-api-key="${apiKey}" data-api-base="${apiBase}"></script>`;

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
      setSequenceError(
        e.body?.detail ||
          e.message ||
          "Failed to create automation sequence. Please try again.",
      );
    } finally {
      setCreatingSequence(false);
    }
  };

  const handleSkipAutomations = () => {
    updateStored({ automationsDone: true });
    onStepComplete?.();
    onNavigate?.("automations");
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
        return <BusinessStep dashData={dashData} />;
      case "hours":
        return (
          <HoursStep
            businessHours={businessHours}
            setBusinessHours={setBusinessHours}
            saving={saving}
            saveError={saveError}
            onSave={handleSaveHours}
          />
        );
      case "agent":
        return (
          <AgentStep
            greeting={greeting}
            setGreeting={setGreeting}
            saving={saving}
            saveError={saveError}
            onSaveGreeting={handleSaveAgent}
            services={services}
            newService={newService}
            setNewService={setNewService}
            addingService={addingService}
            onAddService={handleAddService}
            faqEntries={faqEntries}
            newFaqQ={newFaqQ}
            setNewFaqQ={setNewFaqQ}
            newFaqA={newFaqA}
            setNewFaqA={setNewFaqA}
            onAddFaq={handleAddFaq}
            onDeleteFaq={handleDeleteFaq}
            faqError={faqError}
          />
        );
      case "appearance":
        return (
          <AppearanceStep
            selectedColor={selectedColor}
            setSelectedColor={setSelectedColor}
            customColor={customColor}
            setCustomColor={setCustomColor}
            position={position}
            setPosition={setPosition}
            saving={saving}
            saveError={saveError}
            onSave={handleSaveAppearance}
          />
        );
      case "install":
        return (
          <InstallStep
            platform={platform}
            setPlatform={setPlatform}
            apiKey={apiKey}
            apiBase={apiBase}
            copied={copied}
            onCopyEmbed={handleCopyEmbed}
            onMarkInstalled={handleMarkInstalled}
          />
        );
      case "test":
        return (
          <TestStep
            showPreview={showPreview}
            onTestPreview={handleTestPreview}
            apiKey={apiKey}
            apiBase={apiBase}
          />
        );
      case "automations":
        return (
          <AutomationsStep
            existingSequences={existingSequences}
            sequenceCreated={sequenceCreated}
            creatingSequence={creatingSequence}
            sequenceError={sequenceError}
            textbackEnabled={textbackEnabled}
            savingTextback={savingTextback}
            onCreateDefaultSequence={handleCreateDefaultSequence}
            onToggleTextback={handleToggleTextback}
            onSkipAutomations={handleSkipAutomations}
            onNavigate={onNavigate}
          />
        );
      case "live":
        return <LiveStep onNavigate={onNavigate} onFinish={handleFinish} />;
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
            const isClickable = step.key === "live" ? prevComplete : true;
            return (
              <StepRow
                key={step.key}
                step={step}
                index={i}
                isActive={isActive}
                isClickable={isClickable}
                onToggle={() => setActiveStep(isActive ? null : step.key)}
              >
                {renderStepContent(step)}
              </StepRow>
            );
          })}
        </div>
      )}
    </div>
  );
}
