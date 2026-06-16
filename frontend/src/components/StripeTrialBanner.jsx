import { useAuth } from "../context/AuthContext";

/**
 * StripeTrialBanner - shown when a tenant is on a Stripe 7-day paid trial
 * (plan_status === "trialing"). Warns that the card on file will be charged
 * automatically when the trial ends.
 *
 * When user.trialEnd (ISO 8601 from /me) is present, computes days remaining
 * and formats the exact charge date. Falls back to generic copy when absent.
 *
 * Mutually exclusive with the legacy free TrialBanner (App.jsx) which fires
 * only when trialData.plan === "free" using free_trial_started_at.
 */
export default function StripeTrialBanner({ onNavigate }) {
  const { user } = useAuth();

  if (!user || user.planStatus !== "trialing") return null;

  let countdownText = null;
  if (user.trialEnd) {
    const trialEndMs = new Date(user.trialEnd).getTime();
    const nowMs = Date.now();
    const daysLeft = Math.ceil((trialEndMs - nowMs) / 86400000);
    const chargeDate = new Date(user.trialEnd).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
    countdownText = `${daysLeft} day${daysLeft === 1 ? "" : "s"} left in your free trial - your card will be charged on ${chargeDate}.`;
  }

  return (
    <div
      data-testid="stripe-trial-banner"
      style={{
        padding: "10px 20px",
        background: "#f5a623",
        color: "#0a0a0f",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        fontSize: "0.85rem",
        fontWeight: 500,
        flexShrink: 0,
        gap: "1rem",
      }}
    >
      <span>
        {countdownText ||
          "You're on a 7-day free trial. Your card will be charged automatically when the trial ends."}
      </span>
      <button
        onClick={() => onNavigate("billing")}
        style={{
          background: "rgba(0, 0, 0, 0.15)",
          color: "#0a0a0f",
          border: "none",
          padding: "6px 16px",
          borderRadius: "6px",
          cursor: "pointer",
          fontWeight: 600,
          fontSize: "0.8rem",
          whiteSpace: "nowrap",
          flexShrink: 0,
        }}
      >
        Manage billing
      </button>
    </div>
  );
}
