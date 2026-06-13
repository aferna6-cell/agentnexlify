import { useAuth } from "../context/AuthContext";

/**
 * DemoBanner - rendered in the authenticated shell (App.jsx) when the
 * current user is in a demo session (user.role === "demo").
 *
 * The role value comes from the JWT parsed by AuthContext - no extra API
 * call needed. Demo JWTs carry role="demo" per the backend contract.
 */
export default function DemoBanner() {
  const { user } = useAuth();

  if (!user || user.role !== "demo") return null;

  // Carry the toured vertical into signup so the new account starts in the
  // same industry the visitor just explored (salon demo -> salon onboarding).
  const signupHref = user.businessType
    ? `/signup?from=demo&vertical=${encodeURIComponent(user.businessType)}`
    : "/signup?from=demo";

  return (
    <div
      data-testid="demo-banner"
      style={{
        padding: "10px 20px",
        background: "var(--accent-dim)",
        borderBottom: "1px solid var(--accent-glow)",
        color: "var(--text-primary)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        fontSize: "0.85rem",
        fontWeight: 500,
        flexShrink: 0,
        gap: "1rem",
      }}
    >
      <span style={{ color: "var(--text-secondary)" }}>
        You&rsquo;re in the live demo &mdash; explore everything, data resets
        nightly.
      </span>
      <a
        href={signupHref}
        style={{
          background: "var(--accent)",
          color: "var(--accent-contrast)",
          border: "none",
          padding: "6px 16px",
          borderRadius: "var(--radius-sm)",
          cursor: "pointer",
          fontWeight: 600,
          fontSize: "0.8rem",
          whiteSpace: "nowrap",
          textDecoration: "none",
          display: "inline-block",
          flexShrink: 0,
        }}
      >
        Start your free account &rarr;
      </a>
    </div>
  );
}
