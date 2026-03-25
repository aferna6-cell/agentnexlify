import { trackEvent } from "../../utils/analytics";

function DeltaBadge({ deltaPct }) {
  if (deltaPct === null || deltaPct === undefined) return null;
  const isUp = deltaPct > 0;
  const isDown = deltaPct < 0;
  const isFlat = deltaPct === 0;

  const color = isUp ? "#22c55e" : isDown ? "#ef4444" : "var(--text-muted)";
  const arrow = isUp ? "\u2191" : isDown ? "\u2193" : "\u2192";
  const label = isFlat ? "No change" : `${isUp ? "+" : ""}${deltaPct}%`;

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "3px",
        fontSize: "0.75rem",
        fontWeight: 600,
        color,
        padding: "2px 6px",
        borderRadius: "4px",
        background: isUp ? "rgba(34,197,94,0.1)" : isDown ? "rgba(239,68,68,0.1)" : "rgba(128,128,128,0.1)",
      }}
      title={`vs last week`}
    >
      {arrow} {label}
    </span>
  );
}

export default function OverviewCards({ conversationsUsed, leadCount, automationCount, plan, onNavigate, hotLeadsCount = 0, emailsSentToday = 0, missedCallsThisWeek = null, kpiDeltas = null }) {
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
        <div className="stat-label">
          Conversations This Month
          {kpiDeltas?.conversations && <DeltaBadge deltaPct={kpiDeltas.conversations.delta_pct} />}
        </div>
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
        <div className="stat-label">
          Leads Captured
          {kpiDeltas?.leads && <DeltaBadge deltaPct={kpiDeltas.leads.delta_pct} />}
        </div>
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
            {kpiDeltas?.leads?.this_week > 0 ? `${kpiDeltas.leads.this_week} this week` : "Total leads captured"}
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

      {/* Appointments This Week */}
      {kpiDeltas?.appointments && (
        <div className="stat-card">
          <div className="stat-label">
            Appointments This Week
            <DeltaBadge deltaPct={kpiDeltas.appointments.delta_pct} />
          </div>
          <div className="stat-value">{kpiDeltas.appointments.this_week}</div>
          <div className="stat-trend neutral">
            {kpiDeltas.appointments.last_week > 0
              ? `${kpiDeltas.appointments.last_week} last week`
              : "Track your bookings"}
          </div>
        </div>
      )}
    </div>
  );
}
