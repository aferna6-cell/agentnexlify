/**
 * DemoTour - first-visit guided coach-mark tour for the workforce page.
 *
 * Two audiences (suite onboarding, round 7 item 5):
 *   - Demo visitors (user.role === "demo"): once per session via the
 *     sessionStorage key "anx_demo_tour_done"; after the 2-hour demo token
 *     expires the visitor gets a fresh session and the tour runs again.
 *   - Real owners: once ever per browser via the localStorage key
 *     "anx_os_tour_done", with owner copy (no "sends are simulated" line) -
 *     a new agent_os signup lands here from the wizard and gets walked to
 *     the approval loop on their first visit.
 *
 * Dismissal (Skip or Done) sets the matching key.
 *
 * Targets are located by data-tour attributes added to the OS page:
 *   - data-tour="thread-rail" - the inbox thread list
 *   - data-tour="deliverable-panel" - the deliverable / draft area
 *   - data-tour="approve-button" - the Approve button region
 *
 * If a target element isn't mounted the card still shows centered - never
 * crashes, never blocks the UI.
 */
import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";

const STORAGE_KEY = "anx_demo_tour_done";
const OWNER_STORAGE_KEY = "anx_os_tour_done";

const STEPS = [
  {
    target: "thread-rail",
    heading: "Your Agent OS inbox",
    body: "Everything your AI staff handles lands here - missed calls, leads, follow-ups. Each thread is a task your agents are working on.",
  },
  {
    target: "deliverable-panel",
    heading: "AI drafted a response overnight",
    body: "A missed call came in after hours. Your AI already drafted the callback text and queued it for your review.",
  },
  {
    target: "approve-button",
    heading: "Nothing sends without your OK",
    body: "Tap Approve to see it go out. In the demo, sends are simulated - no real messages leave.",
  },
];

const OWNER_STEPS = [
  {
    target: "thread-rail",
    heading: "Meet your AI workforce",
    body: "Ask for anything here - follow up with leads, draft an email, research a competitor. Each thread is a task your AI staff works on.",
  },
  {
    target: "deliverable-panel",
    heading: "Drafts land here for review",
    body: "When your staff writes something outbound - a text, an email, a quote - the draft parks here. Pick a starter task below to see it happen.",
  },
  {
    target: "approve-button",
    heading: "Nothing sends without your OK",
    body: "Every outbound draft waits for your approval. Approve it and your staff sends it; reject it and they learn from the feedback.",
  },
];

const HIGHLIGHT_CLASS = "demo-tour-highlight";

function getTargetRect(targetKey) {
  const el = document.querySelector(`[data-tour="${targetKey}"]`);
  if (!el) return null;
  return el.getBoundingClientRect();
}

function addHighlight(targetKey) {
  const el = document.querySelector(`[data-tour="${targetKey}"]`);
  if (el) el.classList.add(HIGHLIGHT_CLASS);
}

function removeAllHighlights() {
  document.querySelectorAll(`.${HIGHLIGHT_CLASS}`).forEach((el) => {
    el.classList.remove(HIGHLIGHT_CLASS);
  });
}

/**
 * Compute card position anchored near the target element.
 * Returns a style object for the fixed-position card.
 * Falls back to centered if target isn't mounted.
 */
function cardPosition(rect) {
  if (!rect) {
    return {
      position: "fixed",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
    };
  }

  const CARD_WIDTH = 320;
  const CARD_APPROX_HEIGHT = 180;
  const GAP = 14;
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  // Try to place the card to the right of the target
  let left = rect.right + GAP;
  let top = Math.max(GAP, rect.top);

  // If it overflows the right edge, place to the left
  if (left + CARD_WIDTH > vw - GAP) {
    left = Math.max(GAP, rect.left - CARD_WIDTH - GAP);
  }

  // If it overflows the bottom, push up
  if (top + CARD_APPROX_HEIGHT > vh - GAP) {
    top = Math.max(GAP, vh - CARD_APPROX_HEIGHT - GAP);
  }

  return { position: "fixed", top, left, transform: "none" };
}

export default function DemoTour() {
  const { user } = useAuth();
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(false);
  const [targetRect, setTargetRect] = useState(null);

  const isDemo = user?.role === "demo";
  const steps = isDemo ? STEPS : OWNER_STEPS;

  // Determine whether to show on mount. Demo: once per session. Owner:
  // once ever per browser (first workforce visit after signup).
  useEffect(() => {
    if (!user) return;
    try {
      if (user.role === "demo") {
        if (sessionStorage.getItem(STORAGE_KEY)) return;
      } else if (localStorage.getItem(OWNER_STORAGE_KEY)) {
        return;
      }
    } catch {
      // storage unavailable - show the tour anyway
    }
    setVisible(true);
  }, [user]);

  // Update target rect and highlight when step changes or visibility changes
  useEffect(() => {
    if (!visible) {
      removeAllHighlights();
      return;
    }
    removeAllHighlights();

    const current = steps[step];
    if (!current) return;

    // Allow the DOM to settle (target may appear slightly after state update)
    const id = setTimeout(() => {
      const rect = getTargetRect(current.target);
      setTargetRect(rect);
      addHighlight(current.target);
    }, 80);

    return () => {
      clearTimeout(id);
    };
  }, [visible, step]);

  // Cleanup on unmount
  useEffect(() => {
    return () => removeAllHighlights();
  }, []);

  const dismiss = useCallback(() => {
    removeAllHighlights();
    setVisible(false);
    try {
      if (isDemo) {
        sessionStorage.setItem(STORAGE_KEY, "1");
      } else {
        localStorage.setItem(OWNER_STORAGE_KEY, "1");
      }
    } catch {
      // storage unavailable - tour will show again on next mount
    }
  }, [isDemo]);

  const handleNext = useCallback(() => {
    if (step < steps.length - 1) {
      setStep((s) => s + 1);
    } else {
      dismiss();
    }
  }, [step, steps.length, dismiss]);

  if (!visible) return null;

  const current = steps[step];
  const isLast = step === steps.length - 1;
  const posStyle = cardPosition(targetRect);

  return (
    <>
      {/* Inject highlight CSS once per render tree */}
      <style>{`
        .${HIGHLIGHT_CLASS} {
          outline: 2px solid var(--accent);
          outline-offset: 3px;
          box-shadow: 0 0 0 4px var(--accent-dim);
          border-radius: 6px;
          position: relative;
          z-index: 1000;
          transition: outline 0.15s ease, box-shadow 0.15s ease;
        }
      `}</style>

      {/* Card */}
      <div
        data-testid="demo-tour-card"
        style={{
          ...posStyle,
          width: 320,
          zIndex: 1200,
          background: "var(--bg-secondary)",
          border: "1px solid var(--accent)",
          borderRadius: 10,
          padding: "18px 20px 16px",
          boxShadow: "0 8px 32px rgba(0,0,0,0.45)",
        }}
        role="dialog"
        aria-label={`Tour step ${step + 1} of ${steps.length}: ${current.heading}`}
      >
        {/* Step indicator */}
        <div
          style={{
            display: "flex",
            gap: 5,
            marginBottom: 12,
          }}
        >
          {steps.map((_, i) => (
            <span
              key={i}
              style={{
                width: 24,
                height: 3,
                borderRadius: 2,
                background: i <= step ? "var(--accent)" : "var(--border)",
                transition: "background 0.2s ease",
              }}
            />
          ))}
        </div>

        {/* Content */}
        <div
          style={{
            fontSize: "0.88rem",
            fontWeight: 600,
            color: "var(--text-primary)",
            marginBottom: 6,
          }}
        >
          {current.heading}
        </div>
        <div
          style={{
            fontSize: "0.82rem",
            color: "var(--text-secondary)",
            lineHeight: 1.55,
            marginBottom: 16,
          }}
        >
          {current.body}
        </div>

        {/* Actions */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 10,
          }}
        >
          <button
            onClick={dismiss}
            data-testid="demo-tour-skip"
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              fontSize: "0.78rem",
              cursor: "pointer",
              padding: 0,
              textDecoration: "underline",
            }}
          >
            Skip tour
          </button>
          <button
            onClick={handleNext}
            data-testid="demo-tour-next"
            className="btn-primary"
            style={{ fontSize: "0.82rem", padding: "7px 18px" }}
          >
            {isLast ? "Done" : "Next"}
          </button>
        </div>
      </div>
    </>
  );
}
