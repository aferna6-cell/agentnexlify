import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchDashboard, billingCheckout, billingPortal, fetchTrialStatus } from "../utils/api";
import SkeletonLoader from "../components/SkeletonLoader";

const PLANS = [
  {
    key: "free",
    name: "Free",
    price: "$0",
    period: "/mo",
    features: ["50 conversations/mo", "AI chat widget", "Customer capture", "Basic dashboard"],
  },
  {
    key: "growth",
    name: "Growth",
    price: "$199",
    period: "/mo",
    features: ["Unlimited conversations", "Appointment booking", "SMS notifications", "Analytics dashboard"],
  },
  {
    key: "professional",
    name: "Professional",
    price: "$399",
    period: "/mo",
    features: ["Everything in Growth", "Email follow-ups", "CRM & client management", "Lead Scoring"],
    popular: true,
  },
  {
    key: "enterprise",
    name: "Enterprise",
    price: "$799",
    period: "/mo",
    features: ["Everything in Professional", "Team accounts", "Webhook integrations", "White-label branding", "Dedicated support"],
  },
];

export default function BillingPage() {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [dashData, setDashData] = useState(null);
  const [upgrading, setUpgrading] = useState(null);
  const [portalLoading, setPortalLoading] = useState(false);
  const [trialData, setTrialData] = useState(null);

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const [data, trial] = await Promise.all([
        fetchDashboard(user.tenantId, token),
        fetchTrialStatus(user.tenantId, token).catch(() => null),
      ]);
      setDashData(data);
      setTrialData(trial);
    } catch (err) {
      console.error("Failed to load billing data", err);
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

  if (loading) return <SkeletonLoader />;

  const currentPlan = dashData?.plan || user?.plan || "free";
  const planStatus = dashData?.plan_status || "active";
  const used = dashData?.conversations_used_this_month ?? 0;
  const limit = dashData?.monthly_conversation_limit ?? 50;
  const usagePercent = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;

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
            <button
              className="btn-secondary"
              onClick={handleManageBilling}
              disabled={portalLoading}
              style={{ marginTop: "1rem" }}
            >
              {portalLoading ? "Loading..." : "Manage Billing"}
            </button>
          )}
        </div>
        <div className="settings-card">
          <h3>Usage This Month</h3>
          <div className="billing-usage-bar">
            <div className="billing-usage-fill" style={{ width: `${usagePercent}%` }} />
          </div>
          <div className="billing-usage-text">
            {used} / {limit} conversations ({usagePercent}%)
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
                <button className="btn-secondary" disabled>Free Tier</button>
              ) : (
                <button
                  className="btn-primary"
                  onClick={() => handleUpgrade(plan.key)}
                  disabled={upgrading === plan.key}
                >
                  {upgrading === plan.key ? "Redirecting..." : "Upgrade"}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
