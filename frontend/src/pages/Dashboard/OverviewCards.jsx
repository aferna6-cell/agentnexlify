import { trackEvent } from "../../utils/analytics";

export default function OverviewCards({ conversationsUsed, leadCount, automationCount, plan, onNavigate, hotLeadsCount = 0, emailsSentToday = 0, missedCallsThisWeek = null }) {
  const planLabels = {
    free: "Free",
    growth: "Growth",
    professional: "Professional",
    enterprise: "Enterprise",
    foundation: "Growth",
    operations: "Professional",
  };

  return (
    <div className="stats-row">
      {/* Conversations This Month */}
      <div className="stat-card">
        <div className="stat-label">Conversations This Month</div>
        <div className="stat-value">{conversationsUsed}</div>
        <div className="stat-usage-text">Unlimited</div>
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
            <button className="upgrade-btn" onClick={() => { trackEvent("begin_checkout", { event_label: "dashboard_plan_status" }); onNavigate?.("billing"); }}>Upgrade</button>
          )}
        </div>
        <div className="stat-trend neutral">
          Unlimited conversations
        </div>
      </div>

      {/* Missed Calls This Week */}
      <div className="stat-card">
        <div className="stat-label">Missed Calls This Week</div>
        {missedCallsThisWeek !== null ? (
          <>
            <div className="stat-value">{missedCallsThisWeek}</div>
            <div className="stat-trend neutral">
              {missedCallsThisWeek === 0 ? "No missed calls" : `${missedCallsThisWeek} auto text-back${missedCallsThisWeek !== 1 ? "s" : ""} sent`}
            </div>
          </>
        ) : (
          <>
            <div className="stat-value" style={{ fontSize: "1.2rem", color: "var(--text-muted)" }}>Coming soon</div>
            <div className="stat-trend neutral">
              Enable missed call text-back in Settings
            </div>
            <button
              className="stat-empty-link"
              onClick={() => onNavigate?.("settings")}
            >
              Set up text-back &rarr;
            </button>
          </>
        )}
      </div>
    </div>
  );
}
