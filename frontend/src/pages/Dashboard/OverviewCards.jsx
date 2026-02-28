export default function OverviewCards({ usage, leadCount, summary, automationCount, plan }) {
  const convUsed = usage?.conversations_used ?? 0;
  const convLimit = usage?.conversations_limit ?? 100;
  const convPct = convLimit > 0 ? Math.round((convUsed / convLimit) * 100) : 0;
  const nearLimit = convPct >= 80;

  const leadsLastMonth = summary?.last_month_total ?? 0;
  const leadsThisMonth = leadCount;
  const leadTrend = leadsLastMonth > 0
    ? Math.round(((leadsThisMonth - leadsLastMonth) / leadsLastMonth) * 100)
    : 0;

  const planLabels = {
    starter: "Starter",
    growth: "Growth",
    pro: "Pro",
    enterprise: "Enterprise",
  };

  return (
    <div className="stats-row">
      {/* Conversations This Month */}
      <div className="stat-card">
        <div className="stat-label">Conversations This Month</div>
        <div className="stat-value">{convUsed}</div>
        <div className="stat-usage-bar">
          <div
            className={`stat-usage-fill${nearLimit ? " near-limit" : ""}`}
            style={{ width: `${Math.min(convPct, 100)}%` }}
          />
        </div>
        <div className="stat-usage-text">
          {convUsed} / {convLimit} used
          {nearLimit && (
            <button className="upgrade-cta-inline">Upgrade</button>
          )}
        </div>
      </div>

      {/* Leads Captured */}
      <div className="stat-card">
        <div className="stat-label">Leads Captured</div>
        <div className="stat-value">{leadsThisMonth}</div>
        <div className={`stat-trend ${leadTrend >= 0 ? "up" : "down"}`}>
          {leadTrend >= 0 ? "\u2191" : "\u2193"} {Math.abs(leadTrend)}% vs last month
        </div>
      </div>

      {/* Automations Active */}
      <div className="stat-card">
        <div className="stat-label">Automations Active</div>
        <div className="stat-value">{automationCount}</div>
        <div className="stat-trend neutral">
          {automationCount === 0 ? "Set up your first automation" : "Running"}
        </div>
      </div>

      {/* Plan Status */}
      <div className="stat-card">
        <div className="stat-label">Plan Status</div>
        <div className="stat-plan-row">
          <span className="plan-badge">{planLabels[plan] || plan}</span>
          {plan !== "enterprise" && (
            <button className="upgrade-btn">Upgrade</button>
          )}
        </div>
        <div className="stat-trend neutral">
          {plan === "starter" && "50 conversations/mo"}
          {plan === "growth" && "500 conversations/mo"}
          {plan === "pro" && "2,000 conversations/mo"}
          {plan === "enterprise" && "Unlimited"}
        </div>
      </div>
    </div>
  );
}
