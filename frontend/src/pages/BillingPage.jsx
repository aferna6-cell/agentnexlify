import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchDashboard, billingCheckout, billingPortal, fetchTrialStatus, changePlan, cancelSubscription } from "../utils/api";
import SkeletonLoader from "../components/SkeletonLoader";

const PLANS = [
  {
    key: "free",
    name: "Free",
    price: "$0",
    period: "/mo",
    features: ["Unlimited conversations", "14-day free trial", "AI chat widget", "Customer capture", "Basic dashboard"],
  },
  {
    key: "growth",
    name: "Growth",
    price: "$249",
    period: "/mo",
    features: ["Appointment booking", "SMS notifications", "Basic SEO audit", "AI content writer", "Analytics dashboard"],
  },
  {
    key: "professional",
    name: "Professional",
    price: "$499",
    period: "/mo",
    features: ["Everything in Growth", "Full SEO suite", "Social media marketing", "Email & SMS campaigns", "Advanced analytics"],
    popular: true,
  },
  {
    key: "autopilot",
    name: "Autopilot",
    price: "$299",
    period: "/mo",
    features: [
      "Everything in Professional",
      "Missed call text-back",
      "Monthly reports",
      "Local SEO tools",
      "Auto portal delivery",
    ],
  },
  {
    key: "enterprise",
    name: "Enterprise",
    price: "$899",
    period: "/mo",
    features: ["Everything in Professional", "AI visibility tracking (GEO)", "Priority onboarding support", "Team accounts", "White-label branding"],
  },
];

export default function BillingPage() {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [dashData, setDashData] = useState(null);
  const [upgrading, setUpgrading] = useState(null);
  const [portalLoading, setPortalLoading] = useState(false);
  const [trialData, setTrialData] = useState(null);
  const [changingPlan, setChangingPlan] = useState(null);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [cancelStatus, setCancelStatus] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    setLoadError(null);
    try {
      const [data, trial] = await Promise.all([
        fetchDashboard(user.tenantId, token),
        fetchTrialStatus(user.tenantId, token).catch((err) => { console.warn("Trial status fetch failed:", err.message); return null; }),
      ]);
      setDashData(data);
      setTrialData(trial);
    } catch (err) {
      console.warn("Failed to load billing data:", err.message || err);
      setLoadError(err.message || "Failed to load billing data. Please refresh the page.");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => { load(); }, [load]);

  const handleUpgrade = async (planKey) => {
    setUpgrading(planKey);
    try {
      const res = await billingCheckout(token, { plan: planKey });
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      }
    } catch (err) {
      console.error("Failed to start checkout", err);
      alert(err.message || "Failed to start checkout");
    } finally {
      setUpgrading(null);
    }
  };

  const handleManageBilling = async () => {
    setPortalLoading(true);
    try {
      const res = await billingPortal(user.tenantId, token);
      if (res.portal_url) {
        window.location.href = res.portal_url;
      }
    } catch (err) {
      console.error("Failed to open billing portal", err);
      alert(err.message || "Failed to open billing portal");
    } finally {
      setPortalLoading(false);
    }
  };

  const handleChangePlan = async (planKey) => {
    if (planKey === currentPlan) return;
    setChangingPlan(planKey);
    try {
      await changePlan(token, planKey);
      await load();
    } catch (err) {
      alert(err.body?.detail || err.message || "Failed to change plan");
    } finally {
      setChangingPlan(null);
    }
  };

  const handleCancel = async () => {
    if (!confirmCancel) {
      setConfirmCancel(true);
      return;
    }
    setConfirmCancel(false);
    setCancelStatus("cancelling");
    try {
      const res = await cancelSubscription(token);
      setCancelStatus("scheduled");
    } catch (err) {
      setCancelStatus(null);
      alert(err.body?.detail || err.message || "Failed to cancel");
    }
  };

  if (loading) return <SkeletonLoader />;

  if (loadError) {
    return (
      <div className="fade-in">
        <div className="page-header">
          <h1>Billing</h1>
          <p>Manage your subscription and usage</p>
        </div>
        <div className="error-banner" style={{ marginBottom: "1rem" }}>{loadError}</div>
        <button className="btn-primary" onClick={load}>Retry</button>
      </div>
    );
  }

  const currentPlan = dashData?.plan || user?.plan || "free";
  const planStatus = dashData?.plan_status || "active";
  const used = dashData?.conversations_used_this_month ?? 0;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Billing</h1>
        <p>Manage your subscription and usage</p>
      </div>

      {/* Trial Status */}
      {trialData && trialData.plan === "free" && trialData.days_remaining !== null && (
        <div
          style={{
            padding: "16px 20px",
            marginBottom: "1.5rem",
            borderRadius: "12px",
            background: trialData.is_expired
              ? "linear-gradient(135deg, #dc2626, #b91c1c)"
              : trialData.days_remaining <= 7
                ? "linear-gradient(135deg, #f59e0b, #d97706)"
                : "linear-gradient(135deg, #3b82f6, #2563eb)",
            color: "#fff",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div style={{ fontWeight: 600, fontSize: "1rem" }}>
              {trialData.is_expired
                ? "Free Trial Expired"
                : `Free Trial: ${trialData.days_remaining} day${trialData.days_remaining !== 1 ? "s" : ""} remaining`}
            </div>
            <div style={{ fontSize: "0.8rem", opacity: 0.85, marginTop: "4px" }}>
              {trialData.is_expired
                ? "Your AI assistant is paused. Upgrade to restore service."
                : trialData.trial_expires
                  ? `Expires ${new Date(trialData.trial_expires).toLocaleDateString()}`
                  : ""}
            </div>
          </div>
          <button
            className="btn-primary"
            onClick={() => handleUpgrade("growth")}
            disabled={upgrading === "growth"}
            style={{
              background: "#fff",
              color: trialData.is_expired ? "#dc2626" : "#1e40af",
              fontWeight: 600,
            }}
          >
            {upgrading === "growth" ? "Redirecting..." : "Upgrade Now"}
          </button>
        </div>
      )}

      {/* Current Plan & Usage */}
      <div className="billing-current">
        <div className="settings-card">
          <h3>Current Plan</h3>
          <div className="billing-plan-name">{currentPlan.charAt(0).toUpperCase() + currentPlan.slice(1)}</div>
          <div className="billing-plan-status" data-status={planStatus}>
            {planStatus === "active" ? "Active" : planStatus === "paused" ? "Payment Issue" : planStatus}
          </div>
          {currentPlan !== "free" && (
            <div style={{ display: "flex", gap: 8, marginTop: "1rem", flexWrap: "wrap" }}>
              <button
                className="btn-secondary"
                onClick={handleManageBilling}
                disabled={portalLoading}
              >
                {portalLoading ? "Loading..." : "Manage Billing"}
              </button>
              <button
                className="btn-danger"
                onClick={handleCancel}
                disabled={cancelStatus === "cancelling"}
                style={{ fontSize: "0.85rem" }}
              >
                {confirmCancel ? "Confirm Cancel" : cancelStatus === "scheduled" ? "Cancellation Scheduled" : "Cancel Subscription"}
              </button>
            </div>
          )}
          {cancelStatus === "scheduled" && (
            <div style={{ marginTop: 8, fontSize: "0.8rem", color: "var(--text-muted)" }}>
              Your subscription will remain active until the end of the current billing period.
            </div>
          )}
        </div>
        <div className="settings-card">
          <h3>Usage This Month</h3>
          <div className="billing-usage-text">
            {used} conversations
          </div>
        </div>
      </div>

      {/* Plan Cards */}
      <h3 style={{ marginTop: "2rem", marginBottom: "1rem" }}>Plans</h3>
      <div className="billing-plans">
        {PLANS.map((plan) => {
          const isCurrent = plan.key === currentPlan;
          return (
            <div key={plan.key} className={`billing-plan-card${plan.popular ? " popular" : ""}${isCurrent ? " current" : ""}`}>
              {plan.popular && <div className="billing-popular-badge">Most Popular</div>}
              <div className="billing-plan-card-name">{plan.name}</div>
              <div className="billing-plan-card-price">
                {plan.price}<span>{plan.period}</span>
              </div>
              {plan.setup && <div className="billing-plan-setup">{plan.setup}</div>}
              <ul className="billing-plan-features">
                {plan.features.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
              {isCurrent ? (
                <button className="btn-secondary" disabled>Current Plan</button>
              ) : plan.key === "free" ? (
                currentPlan !== "free" ? (
                  <button className="btn-secondary" onClick={() => { setConfirmCancel(false); handleCancel(); }} disabled={cancelStatus === "cancelling"}>
                    {cancelStatus === "cancelling" ? "Cancelling..." : "Downgrade"}
                  </button>
                ) : (
                  <button className="btn-secondary" disabled>Free Tier</button>
                )
              ) : currentPlan === "free" ? (
                <button
                  className="btn-primary"
                  onClick={() => handleUpgrade(plan.key)}
                  disabled={upgrading === plan.key}
                >
                  {upgrading === plan.key ? "Redirecting..." : "Upgrade"}
                </button>
              ) : (
                <button
                  className="btn-primary"
                  onClick={() => handleChangePlan(plan.key)}
                  disabled={changingPlan === plan.key}
                >
                  {changingPlan === plan.key ? "Switching..." : "Switch Plan"}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
