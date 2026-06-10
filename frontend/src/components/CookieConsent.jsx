/**
 * Cookie consent banner (launch rubric 1.4).
 *
 * Shown once per browser until a choice is stored. The product itself uses
 * only functional storage (auth token, consent choice) — the banner exists
 * for the marketing site analytics surface and regulatory clarity, and the
 * Decline path simply records the refusal. Links to the privacy policy.
 */

import { useState } from "react";

const CONSENT_KEY = "anx_cookie_consent"; // "accepted" | "declined"

export function getCookieConsent() {
  try {
    return window.localStorage.getItem(CONSENT_KEY);
  } catch {
    return null;
  }
}

export default function CookieConsent() {
  const [choice, setChoice] = useState(() => getCookieConsent());

  if (choice) return null;

  const decide = (value) => {
    try {
      window.localStorage.setItem(CONSENT_KEY, value);
    } catch {
      // Storage unavailable (private mode) — hide for this visit only.
    }
    setChoice(value);
  };

  return (
    <div
      role="dialog"
      aria-label="Cookie consent"
      style={{
        position: "fixed",
        bottom: 16,
        left: 16,
        right: 16,
        maxWidth: 560,
        margin: "0 auto",
        zIndex: 90,
        background: "var(--bg-secondary, #16181d)",
        border: "1px solid var(--border, #2a2d35)",
        borderRadius: 12,
        padding: "14px 16px",
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: 12,
        boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
      }}
    >
      <p
        style={{
          margin: 0,
          flex: "1 1 260px",
          fontSize: "0.82rem",
          lineHeight: 1.45,
          color: "var(--text-secondary, #b6bac3)",
        }}
      >
        We use essential cookies to run the app and optional analytics to
        improve it. See the{" "}
        <a href="/privacy" style={{ color: "var(--accent, #6366f1)" }}>
          privacy policy
        </a>
        .
      </p>
      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={() => decide("declined")}
          style={{
            border: "1px solid var(--border, #2a2d35)",
            background: "transparent",
            color: "var(--text-muted, #8b8f98)",
            borderRadius: 8,
            padding: "7px 14px",
            cursor: "pointer",
            fontSize: "0.82rem",
          }}
        >
          Decline
        </button>
        <button
          className="btn-primary"
          onClick={() => decide("accepted")}
          style={{
            borderRadius: 8,
            padding: "7px 14px",
            cursor: "pointer",
            fontSize: "0.82rem",
            border: "none",
          }}
        >
          Accept
        </button>
      </div>
    </div>
  );
}
