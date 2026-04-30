import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { trackWizardEvent } from "../utils/api/onboarding";
import WizardStepBusiness from "./wizard/WizardStepBusiness";
import WizardStepAutoKB from "./wizard/WizardStepAutoKB";
import WizardStepServices from "./wizard/WizardStepServices";
import WizardStepKnowledgeBase from "./wizard/WizardStepKnowledgeBase";
import WizardStepCustomize from "./wizard/WizardStepCustomize";
import WizardStepPlan from "./wizard/WizardStepPlan";
import WizardStepEmbed from "./wizard/WizardStepEmbed";

// AuthContext user fields:
//   tenantId, email, plan, businessName, businessType, role, isTeamMember, name, userId
// Note: widgetApiKey and city are NOT on the JWT â€” steps that need them fetch from the API.

const STORAGE_KEY = "anx_wizard";
const TOTAL_STEPS = 7;

function loadState() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveState(step, data) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ step, data }));
  } catch {
    // sessionStorage write failure is non-fatal (e.g. private browsing quota)
  }
}

export default function OnboardingWizardPage() {
  const { user, token } = useAuth();
  const navigate = useNavigate();

  // Redirect to signup if not authenticated
  useEffect(() => {
    if (user === null) navigate("/signup", { replace: true });
  }, [user, navigate]);

  // Check URL params for Stripe return (e.g. ?step=6)
  const urlParams = new URLSearchParams(window.location.search);
  const urlStep = parseInt(urlParams.get("step") || "0", 10);

  const saved = loadState();
  const [step, setStep] = useState(() =>
    urlStep >= 1 && urlStep <= TOTAL_STEPS ? urlStep : saved?.step || 1,
  );
  const [wizardData, setWizardData] = useState(
    () =>
      saved?.data || {
        // Business info â€” seeded from JWT claims where available
        business_name: user?.businessName || "",
        business_type: user?.businessType || "",
        // city is not in the JWT; steps that need it will populate via API or user input
        city: "",
        phone: "",
        website_url: "",
        hours: null,
        // Services step
        services: [],
        faqs: [],
        // Knowledge base step
        knowledge_base: null,
        // Widget customization step
        widget_bot_name: "",
        widget_primary_color: "#00BFFF",
        widget_greeting_message: "",
        widget_position: "bottom-right",
      },
  );

  // Persist to sessionStorage on every change so the user can refresh without losing progress
  useEffect(() => {
    saveState(step, wizardData);
  }, [step, wizardData]);

  // Track wizard step entries for drop-off analytics
  const prevStep = useRef(step);
  useEffect(() => {
    if (!user?.tenantId || !token) return;
    if (prevStep.current !== step) {
      trackWizardEvent(user.tenantId, token, prevStep.current, "complete");
      prevStep.current = step;
    }
    trackWizardEvent(user.tenantId, token, step, "enter");
  }, [step, user?.tenantId, token]);

  const goNext = useCallback((updates = {}) => {
    setWizardData((prev) => ({ ...prev, ...updates }));
    setStep((s) => Math.min(s + 1, TOTAL_STEPS));
  }, []);

  const goBack = useCallback(() => {
    setStep((s) => Math.max(s - 1, 1));
  }, []);

  // Don't render until user is resolved (avoids flash before redirect)
  if (!user) return null;

  // widgetApiKey is not available on the JWT user object.
  // Steps 4 and 6 that need the API key will fetch it themselves via the API.
  const apiKey = null;

  const stepComponents = [
    null, // index 0 unused â€” wizard is 1-indexed
    <WizardStepBusiness key="1" wizardData={wizardData} onNext={goNext} />,
    <WizardStepAutoKB
      key="2"
      wizardData={wizardData}
      onNext={goNext}
      onBack={goBack}
      token={token}
      tenantId={user?.tenantId}
    />,
    <WizardStepServices
      key="3"
      wizardData={wizardData}
      onNext={goNext}
      onBack={goBack}
    />,
    <WizardStepKnowledgeBase
      key="4"
      wizardData={wizardData}
      onNext={goNext}
      onBack={goBack}
      token={token}
      tenantId={user.tenantId}
    />,
    <WizardStepCustomize
      key="5"
      wizardData={wizardData}
      onNext={goNext}
      onBack={goBack}
      token={token}
      tenantId={user?.tenantId}
    />,
    <WizardStepPlan
      key="6"
      wizardData={wizardData}
      onNext={goNext}
      onBack={goBack}
      token={token}
      tenantId={user.tenantId}
    />,
    <WizardStepEmbed
      key="7"
      wizardData={wizardData}
      token={token}
      tenantId={user?.tenantId}
    />,
  ];

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--bg-primary, #0a0a0f)",
        color: "var(--text-primary, #e2e8f0)",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      {/* Fixed progress bar at top */}
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          background: "rgba(255,255,255,0.1)",
          zIndex: 100,
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${(step / TOTAL_STEPS) * 100}%`,
            background: "#6366f1",
            transition: "width 0.3s ease",
          }}
        />
      </div>

      {/* Header */}
      <div
        style={{
          padding: "20px 24px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <span style={{ fontSize: "1.1rem", fontWeight: 700, color: "#6366f1" }}>
          AgentNexLiFy
        </span>
        <span style={{ color: "rgba(255,255,255,0.3)", fontSize: "0.85rem" }}>
          Step {step} of {TOTAL_STEPS}
        </span>
      </div>

      {/* Step content */}
      <div
        style={{ maxWidth: 640, margin: "0 auto", padding: "40px 24px 80px" }}
      >
        {stepComponents[step]}
      </div>
    </div>
  );
}
