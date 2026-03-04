import { trackEvent } from "../../utils/analytics";

export default function OverviewCards({ conversationsUsed, conversationsLimit, leadCount, automationCount, plan, onNavigate, hotLeadsCount = 0, emailsSentToday = 0 }) {
  const convPct = conversationsLimit > 0 ? Math.round((conversationsUsed / conversationsLimit) * 100) : 0;
  const nearLimit = convPct >= 80;

  const planLabels = {
    free: "Free",
    foundation: "Foundation",
    growth: "Growth",
    operations: "Operations",
    enterprise: "Enterprise",
  };

  const planConvoLabels = {
    free: "50 conversations/mo",
    foundation: "500 conversations/mo",
    growth: "2,000 conversations/mo",
    operations: "10,000 conversations/mo",
    enterprise: "Unlimited",
  };

  return (
    <div className="stats-row">
      {/* Conversations This Month */}
      <div className="stat-card">
        <div className="stat-label">Conversations This Month</div>
        <div className="stat-value">{conversationsUsed}</div>
        <div className="stat-usage-bar">
          <div
            className={`stat-usage-fill${nearLimit ? " near-limit" : ""}`}
            style={{ width: `${Math.min(convPct, 100)}%` }}
          />
        </div>
        <div className="stat-usage-text">
          {conversationsUsed} / {conversationsLimit} used
          {nearLimit && (
            <button className="upgrade-cta-inline" onClick={() => trackEvent("begin_checkout", { event_label: "dashboard_usage_limit" })}>Upgrade</button>
          )}
        </div>
        {conversationsUsed === 0 && (
          <div className="stat-empty-hint">
            Set up your widget to start capturing conversations
          </div>
        )}
      </div>

      {/* Leads Captured */}
      <div className="stat-card">
        <div className="stat-label">Leads Captured</div>
        <div className="stat-value">{leadCount}</div>
        {hotLeadsCount > 0 ? (
          <div
            className="stat-trend hot-alert"
            onClick={() => onNavigate?.("leads")}
          >
            {hotLeadsCount} hot lead{hotLeadsCount !== 1 ? "s" : ""} need attention
          </div>
        ) : (
          <div className="stat-trend neutral">
            Total leads captured
          </div>
        )}
        {leadCount === 0 && (
          <div className="stat-empty-hint">
            Leads appear automatically from widget chats
          </div>
        )}
      </div>

      {/* Automations Active */}
      <div className="stat-card">
        <div className="stat-label">Automations Active</div>
        <div className="stat-value">{automationCount}</div>
        <div className="stat-trend neutral">
          {automationCount === 0 ? "Set up your first automation" : emailsSentToday > 0 ? `${emailsSentToday} email${emailsSentToday !== 1 ? "s" : ""} sent today` : "Running"}
        </div>
        {automationCount === 0 && (
          <button
            className="stat-empty-link"
            onClick={() => onNavigate?.("automations")}
          >
            Set up automated follow-ups &rarr;
          </button>
        )}
      </div>

      {/* Plan Status */}
      <div className="stat-card">
        <div className="stat-label">Plan Status</div>
        <div className="stat-plan-row">
          <span className="plan-badge">{planLabels[plan] || plan}</span>
          {plan !== "enterprise" && (
            <button className="upgrade-btn" onClick={() => trackEvent("begin_checkout", { event_label: "dashboard_plan_status" })}>Upgrade</button>
          )}
        </div>
        <div className="stat-trend neutral">
          {planConvoLabels[plan] || ""}
        </div>
      </div>
    </div>
  );
}
