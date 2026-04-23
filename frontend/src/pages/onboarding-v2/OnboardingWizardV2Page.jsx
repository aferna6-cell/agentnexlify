import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { completeWizard } from "../../utils/api/onboardingV2";
import WizardStepBusinessV2 from "./WizardStepBusinessV2";
import WizardStepServicesV2 from "./WizardStepServicesV2";
import WizardStepAutoKbV2 from "./WizardStepAutoKbV2";
import WizardStepHoursFaqV2 from "./WizardStepHoursFaqV2";
import WizardStepInstallV2 from "./WizardStepInstallV2";

const STORAGE_KEY = "anx_wizard_v2";
const TOTAL_STEPS = 5;

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
    // sessionStorage write failure is non-fatal (private browsing quota)
  }
}

function ProgressDots({ current, total }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        gap: 8,
        padding: "16px 0 0",
      }}
    >
      {Array.from({ length: total }, (_, i) => {
        const n = i + 1;
        const done = n < current;
        const active = n === current;
        return (
          <div
            key={n}
            style={{
              width: active ? 24 : 8,
              height: 8,
              borderRadius: 4,
              background: active
                ? "#6366f1"
                : done
                  ? "rgba(99,102,241,0.4)"
                  : "rgba(255,255,255,0.12)",
              transition: "all 0.25s ease",
            }}
          />
        );
      })}
    </div>
  );
}

export default function OnboardingWizardV2Page() {
  const { user, token } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user === null) navigate("/signup", { replace: true });
  }, [user, navigate]);

  // Feature flag guard — fall back to v1 if flag is absent
  useEffect(() => {
    if (
      user &&
      user.featureFlags &&
      user.featureFlags.onboarding_v2 === false
    ) {
      navigate("/onboarding", { replace: true });
    }
  }, [user, navigate]);

  const saved = loadState();
  const [step, setStep] = useState(() => saved?.step || 1);
  const [wizardData, setWizardData] = useState(
    () =>
      saved?.data || {
        businessName: user?.businessName || "",
        websiteUrl: "",
        serviceArea: "",
        timezone:
          Intl.DateTimeFormat().resolvedOptions().timeZone ||
          "America/New_York",
        vertical: user?.businessType || "",
        services: [],
        avgTicket: null,
        autoKbResult: null,
        hours: null,
        faqs: [],
      },
  );
  const [completing, setCompleting] = useState(false);
  const [toastMsg, setToastMsg] = useState(null);

  useEffect(() => {
    saveState(step, wizardData);
  }, [step, wizardData]);

  const onNext = useCallback((updates = {}) => {
    setWizardData((prev) => ({ ...prev, ...updates }));
    setStep((s) => Math.min(s + 1, TOTAL_STEPS));
  }, []);

  const onBack = useCallback(() => {
    setStep((s) => Math.max(s - 1, 1));
  }, []);

  async function handleComplete(finalUpdates = {}) {
    if (completing) return;
    setCompleting(true);
    setWizardData((prev) => ({ ...prev, ...finalUpdates }));
    try {
      await completeWizard(token);
      sessionStorage.removeItem(STORAGE_KEY);
      setToastMsg("Setup complete!");
      setTimeout(() => navigate("/dashboard"), 1200);
    } catch {
      setCompleting(false);
      setToastMsg("Something went wrong. Try again.");
      setTimeout(() => setToastMsg(null), 3500);
    }
  }

  if (!user) return null;

  const stepComponents = [
    null,
    <WizardStepBusinessV2
      key="1"
      wizardData={wizardData}
      user={user}
      token={token}
      onNext={onNext}
    />,
    <WizardStepServicesV2
      key="2"
      wizardData={wizardData}
      token={token}
      onNext={onNext}
      onBack={onBack}
    />,
    <WizardStepAutoKbV2
      key="3"
      wizardData={wizardData}
      token={token}
      onNext={onNext}
      onBack={onBack}
    />,
    <WizardStepHoursFaqV2
      key="4"
      wizardData={wizardData}
      token={token}
      onNext={onNext}
      onBack={onBack}
    />,
    <WizardStepInstallV2
      key="5"
      wizardData={wizardData}
      token={token}
      user={user}
      onComplete={handleComplete}
      onBack={onBack}
      completing={completing}
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
      {/* Fixed top progress bar */}
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          background: "rgba(255,255,255,0.08)",
          zIndex: 100,
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${(step / TOTAL_STEPS) * 100}%`,
            background: "#6366f1",
            transition: "width 0.35s ease",
          }}
        />
      </div>

      {/* Header */}
      <div
        style={{
          padding: "20px 24px 0",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <span
          style={{ fontSize: "1.05rem", fontWeight: 700, color: "#6366f1" }}
        >
          AgentNexLiFy
        </span>
        <span style={{ color: "rgba(255,255,255,0.3)", fontSize: "0.8rem" }}>
          Step {step} of {TOTAL_STEPS}
        </span>
      </div>

      <ProgressDots current={step} total={TOTAL_STEPS} />

      {/* Step content — max-width 480px, centered, mobile-first */}
      <div
        style={{
          maxWidth: 480,
          margin: "0 auto",
          padding: "28px 20px 80px",
          boxSizing: "border-box",
          width: "100%",
        }}
      >
        {stepComponents[step]}
      </div>

      {/* Toast */}
      {toastMsg && (
        <div
          style={{
            position: "fixed",
            bottom: 24,
            left: "50%",
            transform: "translateX(-50%)",
            background: toastMsg.includes("wrong")
              ? "rgba(220,38,38,0.9)"
              : "rgba(34,197,94,0.9)",
            color: "#fff",
            padding: "12px 24px",
            borderRadius: 10,
            fontWeight: 600,
            fontSize: "0.95rem",
            zIndex: 200,
            whiteSpace: "nowrap",
          }}
        >
          {toastMsg}
        </div>
      )}
    </div>
  );
}
