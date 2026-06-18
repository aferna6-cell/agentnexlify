import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchDashboard, billingCheckout, billingPortal, fetchTrialStatus, changePlan, cancelSubscription, fetchAiUsage, buyMoreUsage } from "../utils/api/dashboard";
import SkeletonLoader from "../components/SkeletonLoader";
import ReferralCard from "../components/billing/ReferralCard";
import { notify } from "../utils/notify";

// Two purchasable plans. Keys must match the backend PLAN_PRICES keys.
// Chatbot: $19.99/mo - widget/chatbot features only.
// Agent OS: $99.99/mo - full platform.
const PLANS = [
  {
    key: "chatbot",
    name: "Chatbot",
    price: "$19.99",
    period: "/mo",
    description: "AI chat widget + lead capture for your website.",
  },
  {
    key: "agent_os",
    name: "Agent OS",
    price: "$99.99",
    period: "/mo",
    popular: true,
    description: "Full platform - Agent OS, marketing, CRM, and everything.",
  },
];

// Data-driven feature comparison matrix
// value can be: true (checkmark), false (dash), or a string (custom label)
const FEATURE_MATRIX = [
  {
    feature: "AI Chat Widget",
    chatbot: true, agent_os: true,
  },
  {
    feature: "Lead Capture & Dashboard",
    chatbot: true, agent_os: true,
  },
  {
    feature: "Appointments & Booking",
    chatbot: false, agent_os: true,
  },
  {
    feature: "Email & SMS Automation",
    chatbot: false, agent_os: true,
  },
  {
    feature: "CRM & Pipeline Management",
    chatbot: false, agent_os: true,
  },
  {
    feature: "Marketing Campaigns",
    chatbot: false, agent_os: true,
  },
  {
    feature: "Invoicing & Documents",
    chatbot: false, agent_os: true,
  },
  {
    feature: "SEO & Local Marketing",
    chatbot: false, agent_os: true,
  },
  {
    feature: "Agent OS (AI workers)",
    chatbot: false, agent_os: true,
  },
  {
    feature: "Team Members",
    chatbot: "1", agent_os: "Unlimited",
  },
];

const CANCEL_REASONS = [
  { value: "too_expensive", label: "Too expensive" },
  { value: "missing_feature", label: "Missing something I need" },
  { value: "not_enough_leads", label: "Not enough leads" },
  { value: "switching_tools", label: "Switching tools" },
  { value: "setup_too_hard", label: "Setup was too hard" },
  { value: "temporary_pause", label: "Pausing for now" },
  { value: "other", label: "Other" },
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
  const [showSaveOffer, setShowSaveOffer] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelDetail, setCancelDetail] = useState("");
  const [cancelStatus, setCancelStatus] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [aiUsage, setAiUsage] = useState(null);
  const [aiUsageLoading, setAiUsageLoading] = useState(true);
  const [buyingUsage, setBuyingUsage] = useState(false);

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

  const loadAiUsage = useCallback(async () => {
    if (!token) return;
    setAiUsageLoading(true);
    try {
      const data = await fetchAiUsage(token);
      setAiUsage(data);
    } catch (err) {
      console.warn("Failed to load AI usage:", err.message || err);
    } finally {
      setAiUsageLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadAiUsage(); }, [loadAiUsage]);

  // Show success toast when returning from Stripe Checkout
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("checkout_success") === "1") {
      notify.success("Payment successful! Your plan is being activated.");
      // Clean the URL so refresh doesn't re-trigger
      params.delete("checkout_success");
      params.delete("session_id");
      const newUrl = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}${window.location.hash}`;
      window.history.replaceState({}, "", newUrl);
    }
  }, []);

  const handleUpgrade = async (planKey) => {
    setUpgrading(planKey);
    try {
      const res = await billingCheckout(token, { plan: planKey });
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      }
    } catch (err) {
      console.error("Failed to start checkout", err);
      notify.error(err.message || "Failed to start checkout");
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
      notify.error(err.message || "Failed to open billing portal");
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
      notify.error(err.body?.detail || err.message || "Failed to change plan");
    } finally {
      setChangingPlan(null);
    }
  };

  const handleCancel = async () => {
    if (!confirmCancel) {
      // Step 1: open the save offer before revealing the cancel form.
      setShowSaveOffer(true);
      return;
    }
    if (!cancelReason) {
      notify.error("Choose a cancellation reason first");
      return;
    }
    setConfirmCancel(false);
    setCancelStatus("cancelling");
    try {
      const res = await cancelSubscription(token, {
        reason: cancelReason,
        reason_detail: cancelDetail,
      });
      setCancelStatus("scheduled");
      setCancelReason("");
      setCancelDetail("");
    } catch (err) {
      setCancelStatus(null);
      notify.error(err.body?.detail || err.message || "Failed to cancel");
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
            onClick={() => handleUpgrade("chatbot")}
            disabled={upgrading === "chatbot"}
            style={{
              background: "#fff",
              color: trialData.is_expired ? "#dc2626" : "#1e40af",
              fontWeight: 600,
            }}
          >
            {upgrading === "chatbot" ? "Redirecting..." : "Upgrade Now"}
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
          {currentPlan !== "free" && (
            <div
              style={{
                marginTop: 12,
                fontSize: "0.8rem",
                lineHeight: 1.5,
                color: "var(--text-muted)",
              }}
            >
              Need help with a billing mistake or accidental renewal? Email{" "}
              <a href="mailto:support@agentnexlify.com">support@agentnexlify.com</a>{" "}
              within 5 business days. Duplicate charges and service-activation
              billing errors are eligible for manual review.
            </div>
          )}
          {showSaveOffer && !confirmCancel && currentPlan !== "free" && (
            <div style={{
              marginTop: 12,
              padding: 14,
              border: "1px solid var(--border)",
              borderRadius: 8,
              background: "rgba(99,102,241,0.06)",
            }}>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>Before you go</div>
              {currentPlan === "agent_os" ? (
                <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginBottom: 10 }}>
                  Keep your AI receptionist for less. Downgrade to AI Front Desk
                  ($19.99/mo) and your widget keeps answering customers, capturing
                  leads, and booking appointments 24/7.
                </p>
              ) : (
                <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginBottom: 10 }}>
                  Not getting value yet? We can help you set it up. Email{" "}
                  <a href="mailto:support@agentnexlify.com">support@agentnexlify.com</a>{" "}
                  and we will get your AI working for you.
                </p>
              )}
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {currentPlan === "agent_os" && (
                  <button
                    className="btn-primary"
                    style={{ fontSize: "0.8rem" }}
                    disabled={changingPlan === "chatbot"}
                    onClick={() => { setShowSaveOffer(false); handleChangePlan("chatbot"); }}
                  >
                    {changingPlan === "chatbot" ? "Switching..." : "Downgrade to AI Front Desk"}
                  </button>
                )}
                <button
                  className="btn-secondary"
                  style={{ fontSize: "0.8rem" }}
                  onClick={() => setShowSaveOffer(false)}
                >
                  Keep my plan
                </button>
                <button
                  className="btn-danger"
                  style={{ fontSize: "0.8rem" }}
                  onClick={() => { setShowSaveOffer(false); setConfirmCancel(true); }}
                >
                  Cancel anyway
                </button>
              </div>
            </div>
          )}
          {confirmCancel && currentPlan !== "free" && (
            <div style={{
              marginTop: 12,
              padding: 12,
              border: "1px solid var(--border)",
              borderRadius: 8,
              background: "rgba(255,255,255,0.03)",
            }}>
              <label style={{ display: "block", fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: 6 }}>
                Why are you cancelling?
              </label>
              <select
                value={cancelReason}
                onChange={(event) => setCancelReason(event.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "var(--bg-primary)",
                  color: "var(--text-primary)",
                  marginBottom: 8,
                }}
              >
                <option value="">Choose a reason</option>
                {CANCEL_REASONS.map((reason) => (
                  <option key={reason.value} value={reason.value}>{reason.label}</option>
                ))}
              </select>
              <textarea
                value={cancelDetail}
                onChange={(event) => setCancelDetail(event.target.value)}
                placeholder="Anything we should know?"
                rows={3}
                maxLength={1000}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "var(--bg-primary)",
                  color: "var(--text-primary)",
                  resize: "vertical",
                }}
              />
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

      {/* Plan Comparison Matrix */}
      <h3 style={{ marginTop: "2rem", marginBottom: "1rem" }}>Plan Comparison</h3>
      <div style={{ overflowX: "auto", marginBottom: "2rem" }}>
        <table style={{
          width: "100%",
          borderCollapse: "separate",
          borderSpacing: 0,
          background: "var(--bg-secondary, var(--card-bg))",
          border: "1px solid var(--border)",
          borderRadius: 12,
          overflow: "hidden",
          minWidth: 700,
        }}>
          <thead>
            <tr>
              <th style={{
                textAlign: "left",
                padding: "16px 20px",
                fontSize: "0.8rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                borderBottom: "1px solid var(--border)",
                width: "22%",
              }}>
                Feature
              </th>
              {PLANS.map((plan) => {
                const isCurrent = plan.key === currentPlan;
                return (
                  <th key={plan.key} style={{
                    textAlign: "center",
                    padding: "12px 8px 16px",
                    borderBottom: "1px solid var(--border)",
                    background: isCurrent
                      ? "rgba(0,191,255,0.07)"
                      : plan.popular ? "rgba(139,92,246,0.05)" : "transparent",
                    position: "relative",
                  }}>
                    {plan.popular && (
                      <div style={{
                        position: "absolute",
                        top: 0,
                        left: "50%",
                        transform: "translateX(-50%)",
                        background: "linear-gradient(135deg, var(--accent, #00bfff), #8b5cf6)",
                        color: "#fff",
                        fontSize: "0.65rem",
                        fontWeight: 700,
                        padding: "2px 10px",
                        borderRadius: "0 0 6px 6px",
                        letterSpacing: "0.04em",
                        whiteSpace: "nowrap",
                      }}>
                        MOST POPULAR
                      </div>
                    )}
                    <div style={{
                      fontSize: "0.9rem",
                      fontWeight: 700,
                      color: isCurrent ? "var(--accent)" : "var(--text-primary)",
                      marginTop: plan.popular ? 14 : 4,
                    }}>
                      {plan.name}
                    </div>
                    <div style={{
                      fontSize: "0.8rem",
                      color: "var(--text-muted)",
                      marginTop: 2,
                    }}>
                      {plan.price}<span style={{ fontSize: "0.7rem" }}>{plan.period}</span>
                    </div>
                    {plan.trial && (
                      <div style={{
                        fontSize: "0.65rem",
                        fontWeight: 700,
                        color: "var(--green)",
                        marginTop: 4,
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                      }}>
                        {plan.trial}
                      </div>
                    )}
                    {isCurrent && (
                      <div style={{
                        fontSize: "0.65rem",
                        fontWeight: 700,
                        color: "var(--accent)",
                        marginTop: 4,
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                      }}>
                        Current
                      </div>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {FEATURE_MATRIX.map((row, rowIdx) => (
              <tr key={row.feature} style={{ background: rowIdx % 2 === 0 ? "transparent" : "rgba(255,255,255,0.02)" }}>
                <td style={{
                  padding: "13px 20px",
                  fontSize: "0.875rem",
                  color: "var(--text-secondary)",
                  borderBottom: rowIdx < FEATURE_MATRIX.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none",
                  fontWeight: 500,
                }}>
                  {row.feature}
                </td>
                {PLANS.map((plan) => {
                  const isCurrent = plan.key === currentPlan;
                  const val = row[plan.key];
                  let cell;
                  if (val === true) {
                    cell = (
                      <span style={{ color: "#22c55e", fontSize: "1rem", fontWeight: 700 }}>&#x2713;</span>
                    );
                  } else if (val === false) {
                    cell = (
                      <span style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>-</span>
                    );
                  } else {
                    cell = (
                      <span style={{ color: "var(--text-primary)", fontSize: "0.8rem", fontWeight: 600 }}>
                        {val}
                      </span>
                    );
                  }
                  return (
                    <td key={plan.key} style={{
                      textAlign: "center",
                      padding: "13px 8px",
                      borderBottom: rowIdx < FEATURE_MATRIX.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none",
                      background: isCurrent ? "rgba(0,191,255,0.05)" : "transparent",
                    }}>
                      {cell}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td style={{ padding: "16px 20px", borderTop: "1px solid var(--border)" }} />
              {PLANS.map((plan) => {
                const isCurrent = plan.key === currentPlan;
                let btn;
                if (isCurrent) {
                  btn = <button className="btn-secondary" disabled style={{ width: "100%", fontSize: "0.8rem", padding: "8px 0" }}>Current Plan</button>;
                } else if (plan.key === "free") {
                  btn = currentPlan !== "free"
                    ? <button className="btn-secondary" onClick={() => { setConfirmCancel(false); handleCancel(); }} disabled={cancelStatus === "cancelling"} style={{ width: "100%", fontSize: "0.8rem", padding: "8px 0" }}>
                        {cancelStatus === "cancelling" ? "Cancelling..." : "Downgrade"}
                      </button>
                    : <button className="btn-secondary" disabled style={{ width: "100%", fontSize: "0.8rem", padding: "8px 0" }}>Free Tier</button>;
                } else if (currentPlan === "free") {
                  btn = <button className="btn-primary" onClick={() => handleUpgrade(plan.key)} disabled={upgrading === plan.key} style={{ width: "100%", fontSize: "0.8rem", padding: "8px 0" }}>
                    {upgrading === plan.key ? "Redirecting..." : "Upgrade"}
                  </button>;
                } else {
                  btn = <button className="btn-primary" onClick={() => handleChangePlan(plan.key)} disabled={changingPlan === plan.key} style={{ width: "100%", fontSize: "0.8rem", padding: "8px 0" }}>
                    {changingPlan === plan.key ? "Switching..." : "Switch Plan"}
                  </button>;
                }
                return (
                  <td key={plan.key} style={{
                    padding: "16px 10px",
                    textAlign: "center",
                    borderTop: "1px solid var(--border)",
                    background: isCurrent ? "rgba(0,191,255,0.05)" : "transparent",
                  }}>
                    {btn}
                  </td>
                );
              })}
            </tr>
          </tfoot>
        </table>
      </div>

      <ReferralCard />
    </div>
  );
}
