import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { trackWizardEvent } from "../utils/api/onboarding";
import WizardExpressSetup from "./wizard/WizardExpressSetup";
import WizardStepBusiness from "./wizard/WizardStepBusiness";
import WizardStepAutoKB from "./wizard/WizardStepAutoKB";
import WizardStepServices from "./wizard/WizardStepServices";
import WizardStepKnowledgeBase from "./wizard/WizardStepKnowledgeBase";
import WizardStepCustomize from "./wizard/WizardStepCustomize";
// WizardStepPlan imported but NOT in the wizard sequence - used by RequirePaid gate instead.
import WizardStepEmbed from "./wizard/WizardStepEmbed";
import WizardStepDriveConnect from "./wizard/WizardStepDriveConnect";

// AuthContext user fields:
//   tenantId, email, plan, businessName, businessType, role, isTeamMember, name, userId
// Note: widgetApiKey and city are NOT on the JWT â€” steps that need them fetch from the API.

const STORAGE_KEY = "anx_wizard";
// Plan step removed (2026-06-15): payment gate is now at signup, not inside the wizard.
// Steps: 0=express, 1=business, 2=auto-KB (also drafts/saves instant FAQs),
//        3=services, 4=KB, 5=customize, 6=embed, 7=connect-drive (optional, #53)
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

  // Redirect to signup only when there is no token at all. With a token
  // present, user is null for a tick while AuthContext parses it - bouncing
  // on that tick sent logged-in users cold-loading /setup to /signup.
  useEffect(() => {
    if (user === null && !token) navigate("/signup", { replace: true });
  }, [user, token, navigate]);

  // Check URL params for Stripe return (e.g. ?step=6)
  const urlParams = new URLSearchParams(window.location.search);
  const urlStep = parseInt(urlParams.get("step") || "0", 10);

  const saved = loadState();
  // Step 0 = express setup chooser. Fresh visitors land there; an explicit
  // ?step= (Stripe return) or saved wizard progress goes straight to the step.
  const [step, setStep] = useState(() =>
    urlStep >= 1 && urlStep <= TOTAL_STEPS ? urlStep : saved?.step ?? 0,
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

  // Track step entries for drop-off analytics (0 = express chooser, 1-6 wizard)
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

  // Skip-ahead from Auto-KB: persist whatever the crawl produced, then jump
  // straight to the widget so the owner can talk to their AI now and finish
  // Services/Customize/Embed later. /dashboard/widget is reachable on every
  // paid tier (the gated AI Workforce page would 402 a chatbot-tier signup).
  const goTalkToAiNow = useCallback(
    (updates = {}) => {
      setWizardData((prev) => ({ ...prev, ...updates }));
      navigate("/dashboard/widget");
    },
    [navigate],
  );

  // Don't render until user is resolved (avoids flash before redirect)
  if (!user) return null;

  // widgetApiKey is not available on the JWT user object.
  // Steps 4 and 6 that need the API key will fetch it themselves via the API.
  const apiKey = null;

  // Order (2026-06-15): express chooser (0), then teach the AI staff (1-3),
  // then the OPTIONAL website-widget steps (4-6). Plan step removed - payment
  // is gated at signup via RequirePaid before the wizard is ever shown.
  // Auto-KB (step 2) both pre-fills the profile from the site AND drafts/saves
  // instant FAQs for the chat widget; there is no standalone instant-FAQ step.
  const stepComponents = [
    <WizardExpressSetup
      key="0"
      user={user}
      token={token}
      onCustomize={() => setStep(1)}
    />,
    <WizardStepBusiness key="1" wizardData={wizardData} onNext={goNext} />,
    <WizardStepAutoKB
      key="2"
      wizardData={wizardData}
      onNext={goNext}
      onBack={goBack}
      onTalkToAiNow={goTalkToAiNow}
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
    <WizardStepEmbed
      key="6"
      wizardData={wizardData}
      token={token}
      tenantId={user?.tenantId}
      onNext={goNext}
    />,
    <WizardStepDriveConnect
      key="7"
      token={token}
      tenantId={user?.tenantId}
      onDone={() => navigate("/dashboard/agent-os")}
      onSkip={() => navigate("/dashboard/agent-os")}
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
        {step >= 1 && (
          <span style={{ color: "rgba(255,255,255,0.3)", fontSize: "0.85rem" }}>
            Step {step} of {TOTAL_STEPS} · ~3 minutes
          </span>
        )}
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
