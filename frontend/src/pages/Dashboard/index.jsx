import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  fetchDashboard,
  fetchActivity,
  fetchOnboardingStatus,
  fetchKpiDeltas,
} from "../../utils/api/dashboard";
import { fetchAnalyticsHealth } from "../../utils/api/analytics";
import { fetchLeads, updateLead, deleteLead } from "../../utils/api/leads";
import {
  fetchSequenceStats,
  fetchAutomations,
} from "../../utils/api/automations";
import { fetchCrmDashboardWidgets } from "../../utils/api/crm";
import AutomationActivityCard from "./AutomationActivityCard";
import OverviewCards from "./OverviewCards";
import LeadPipeline from "./LeadPipeline";
import ActivityFeed from "./ActivityFeed";
import WidgetEmbed from "./WidgetEmbed";
import QuickActions from "./QuickActions";
import LeadDetailDrawer from "./LeadDetailDrawer";
import OnboardingChecklist from "./OnboardingChecklist";
import TodayAppointments from "./TodayAppointments";
import ActionItemsWidget from "./ActionItemsWidget";
import AIInsightsWidget from "./AIInsightsWidget";
import FrontDeskHealthCard from "./FrontDeskHealthCard";
import RecoveryStatsWidget from "./RecoveryStatsWidget";
import SkeletonLoader from "../../components/SkeletonLoader";

const ONBOARDING_KEY_PREFIX = "anx_onboarding_";

function isOnboardingDismissed(tenantId) {
  try {
    const raw = localStorage.getItem(`${ONBOARDING_KEY_PREFIX}${tenantId}`);
    return raw ? JSON.parse(raw).dismissed === true : false;
  } catch {
    return false;
  }
}

export default function Dashboard({ onNavigate, onPlanLoaded }) {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [leads, setLeads] = useState([]);
  const [dashData, setDashData] = useState(null);
  const [automations, setAutomations] = useState([]);
  const [activity, setActivity] = useState([]);
  const [selectedLead, setSelectedLead] = useState(null);
  const [error, setError] = useState(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [crmWidgets, setCrmWidgets] = useState(null);
  const [seqStats, setSeqStats] = useState(null);
  const [onboardingStatus, setOnboardingStatus] = useState(null);
  const [kpiDeltas, setKpiDeltas] = useState(null);
  const [lastActivity, setLastActivity] = useState(undefined); // undefined = loading, null = no data

  const loadDashboard = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    setError(null);
    try {
      const [
        dashRes,
        leadsRes,
        autoRes,
        activityRes,
        crmRes,
        seqStatsRes,
        onboardRes,
        kpiRes,
      ] = await Promise.allSettled([
        fetchDashboard(user.tenantId, token),
        fetchLeads(user.tenantId, token),
        fetchAutomations(user.tenantId, token),
        fetchActivity(user.tenantId, token),
        fetchCrmDashboardWidgets(user.tenantId, token),
        fetchSequenceStats(user.tenantId, token),
        fetchOnboardingStatus(user.tenantId, token),
        fetchKpiDeltas(user.tenantId, token),
      ]);

      if (dashRes.status === "fulfilled") {
        setDashData(dashRes.value);
        if (onPlanLoaded) onPlanLoaded(dashRes.value.plan);
        setShowOnboarding(!isOnboardingDismissed(user.tenantId));
      }
      if (leadsRes.status === "fulfilled") setLeads(leadsRes.value.leads || []);
      if (autoRes.status === "fulfilled")
        setAutomations(autoRes.value.automations || []);
      if (activityRes.status === "fulfilled")
        setActivity(activityRes.value.activity || []);
      if (crmRes.status === "fulfilled") setCrmWidgets(crmRes.value);
      if (seqStatsRes.status === "fulfilled") setSeqStats(seqStatsRes.value);
      if (onboardRes.status === "fulfilled")
        setOnboardingStatus(onboardRes.value);
      if (kpiRes.status === "fulfilled") setKpiDeltas(kpiRes.value);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, onPlanLoaded]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  // Fetch last message timestamp for widget status badge
  useEffect(() => {
    if (!user?.tenantId || !token) return;
    fetchAnalyticsHealth(user.tenantId, token)
      .then((data) => setLastActivity(data.last_message_at || null))
      .catch((err) => {
        console.warn("Analytics health fetch failed:", err?.message);
        setLastActivity(null);
      });
  }, [user?.tenantId, token]);

  const handleStepComplete = useCallback(() => {
    if (user?.tenantId) {
      fetchDashboard(user.tenantId, token)
        .then((data) => setDashData(data))
        .catch((err) => console.warn("Dashboard refresh failed:", err.message));
    }
  }, [user?.tenantId, token]);

  const handleStageDrop = useCallback(
    async (leadId, newStage) => {
      const prev = leads.slice();
      // Optimistic update
      setLeads((cur) =>
        cur.map((l) => (l.id === leadId ? { ...l, status: newStage } : l)),
      );
      try {
        await updateLead(user.tenantId, token, leadId, { status: newStage });
      } catch (err) {
        setLeads(prev); // Revert on failure
        setError(
          err.body?.detail || err.message || "Failed to update lead stage.",
        );
        setTimeout(() => setError(null), 5000);
      }
    },
    [leads, user?.tenantId, token],
  );

  const handleLeadSave = useCallback(
    async (leadId, updates) => {
      try {
        const updated = await updateLead(user.tenantId, token, leadId, updates);
        setLeads((cur) =>
          cur.map((l) => (l.id === leadId ? { ...l, ...updated } : l)),
        );
        setSelectedLead((cur) =>
          cur?.id === leadId ? { ...cur, ...updated } : cur,
        );
      } catch (err) {
        setError(err.body?.detail || err.message || "Failed to save lead.");
        setTimeout(() => setError(null), 5000);
      }
    },
    [user?.tenantId, token],
  );

  const handleLeadDelete = useCallback(
    async (leadId) => {
      try {
        await deleteLead(user.tenantId, token, leadId);
        setLeads((cur) => cur.filter((l) => l.id !== leadId));
        setSelectedLead(null);
      } catch (err) {
        setError(err.body?.detail || err.message || "Failed to delete lead.");
        setTimeout(() => setError(null), 5000);
      }
    },
    [user?.tenantId, token],
  );

  if (loading) return <SkeletonLoader />;

  if (error && !dashData) {
    return (
      <div className="fade-in">
        <div className="page-header">
          <h1>Dashboard</h1>
        </div>
        <div className="error-banner">Failed to load dashboard: {error}</div>
      </div>
    );
  }

  const enabledAutomations = automations.filter((a) => a.is_enabled);
  const businessProfile = dashData?.business_profile || null;

  return (
    <div className="fade-in">
      {error && dashData && (
        <div className="error-banner" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>
          Welcome back
          {dashData?.business_name
            ? `, ${dashData.business_name}`
            : user.businessName
              ? `, ${user.businessName}`
              : ""}
        </p>
      </div>

      {businessProfile && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "18px",
            alignItems: "start",
            marginBottom: "18px",
            padding: "18px 20px",
            borderRadius: "8px",
            border: "1px solid rgba(255,255,255,0.08)",
            background:
              "linear-gradient(135deg, rgba(15,23,42,0.92), rgba(30,41,59,0.88))",
          }}
        >
          <div>
            <div
              style={{
                fontSize: "0.78rem",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "rgba(255,255,255,0.55)",
                marginBottom: "8px",
              }}
            >
              Configured for {businessProfile.label}
            </div>
            <div
              style={{
                fontSize: "1.15rem",
                fontWeight: 700,
                color: "#fff",
                marginBottom: "6px",
              }}
            >
              {businessProfile.headline}
            </div>
            <div style={{ color: "rgba(255,255,255,0.72)", lineHeight: 1.5 }}>
              {businessProfile.subheadline}
            </div>
          </div>
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "8px",
              justifyContent: "flex-end",
            }}
          >
            {businessProfile.focus_areas.map((item) => (
              <span
                key={item}
                style={{
                  padding: "8px 12px",
                  borderRadius: "999px",
                  background: "rgba(148,163,184,0.12)",
                  border: "1px solid rgba(148,163,184,0.18)",
                  color: "#e2e8f0",
                  fontSize: "0.82rem",
                  fontWeight: 600,
                }}
              >
                {item}
              </span>
            ))}
          </div>
          <div
            style={{
              textAlign: "right",
              minWidth: "180px",
              alignSelf: "end",
              color: "rgba(255,255,255,0.72)",
            }}
          >
            <div
              style={{
                fontSize: "0.78rem",
                textTransform: "uppercase",
                color: "rgba(255,255,255,0.52)",
                marginBottom: "4px",
              }}
            >
              Proof metric
            </div>
            <div style={{ color: "#fff", fontSize: "1.6rem", fontWeight: 700 }}>
              {dashData?.leads_count ?? 0}
            </div>
            <div style={{ fontSize: "0.86rem", lineHeight: 1.35 }}>
              {(dashData?.leads_count ?? 0) > 0
                ? businessProfile.proof_metric_label
                : businessProfile.proof_metric_empty_hint}
            </div>
          </div>
        </div>
      )}

      {/* Widget Status Badge */}
      {lastActivity !== undefined &&
        (() => {
          let dotColor = "#666";
          let label = "No Activity Yet";
          let detail =
            "Your widget is ready - share your website link to start capturing leads";

          if (lastActivity) {
            const diffMs = Date.now() - new Date(lastActivity).getTime();
            const diffMins = Math.floor(diffMs / 60000);
            const diffHrs = Math.floor(diffMins / 60);

            if (diffMs < 3600000) {
              dotColor = "#4caf50";
              label = "Widget Live";
              detail =
                diffMins < 1
                  ? "Last activity: just now"
                  : `Last activity: ${diffMins}m ago`;
            } else if (diffMs < 86400000) {
              dotColor = "#ff9800";
              label = "Widget Idle";
              detail = `Last activity: ${diffHrs}h ago`;
            } else {
              dotColor = "#666";
              label = "No Activity Yet";
              detail = `Last activity: ${Math.floor(diffHrs / 24)}d ago`;
            }
          }

          return (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                background: "rgba(255,255,255,0.05)",
                borderRadius: "8px",
                padding: "8px 16px",
                marginBottom: "16px",
                fontSize: "0.85rem",
              }}
            >
              <span
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  background: dotColor,
                  display: "inline-block",
                  flexShrink: 0,
                  boxShadow:
                    dotColor === "#4caf50"
                      ? "0 0 6px rgba(76,175,80,0.5)"
                      : "none",
                }}
              />
              <span style={{ color: "#fff", fontWeight: 600 }}>{label}</span>
              <span style={{ color: "var(--text-muted)" }}>{detail}</span>
            </div>
          );
        })()}

      {/* Resume setup banner for users who haven't completed onboarding */}
      {onboardingStatus && onboardingStatus.onboarding_completed === false && (
        <a
          href="/setup"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "14px 20px",
            marginBottom: 16,
            background:
              "linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.1))",
            border: "1px solid rgba(99,102,241,0.3)",
            borderRadius: "var(--radius, 12px)",
            color: "#a5b4fc",
            textDecoration: "none",
            fontSize: "0.9rem",
          }}
        >
          <span>
            <strong>Complete your setup</strong> - finish the onboarding wizard
            to activate your AI assistant (
            {onboardingStatus.completion_percentage || 0}% done)
          </span>
          <span style={{ fontSize: "1.2rem" }}>&rarr;</span>
        </a>
      )}

      {showOnboarding && dashData && (
        <OnboardingChecklist
          dashData={dashData}
          tenantId={user.tenantId}
          token={token}
          onNavigate={onNavigate}
          onDismiss={() => setShowOnboarding(false)}
          onStepComplete={handleStepComplete}
          onboardingStatus={onboardingStatus}
        />
      )}

      <AutomationActivityCard
        tenantId={user.tenantId}
        token={token}
        onNavigate={onNavigate}
      />

      <OverviewCards
        conversationsUsed={dashData?.conversations_used_this_month ?? 0}
        leadCount={dashData?.leads_count ?? leads.length}
        automationCount={
          seqStats?.active_sequences ?? enabledAutomations.length
        }
        plan={dashData?.plan ?? user.plan}
        onNavigate={onNavigate}
        hotLeadsCount={dashData?.hot_leads_count ?? 0}
        emailsSentToday={seqStats?.emails_sent_today ?? 0}
        missedCallsThisWeek={dashData?.missed_calls_this_week ?? null}
        kpiDeltas={kpiDeltas}
        businessProfile={businessProfile}
      />
      <div className="analytics-link" onClick={() => onNavigate("analytics")}>
        View Analytics &rarr;
      </div>

      <RecoveryStatsWidget tenantId={user.tenantId} token={token} />

      <div className="dashboard-main-grid">
        <div className="dashboard-main-content">
          <LeadPipeline
            leads={leads}
            onSelectLead={setSelectedLead}
            onNavigate={onNavigate}
            onStageDrop={handleStageDrop}
          />
          {leads.length === 0 && (
            <p
              style={{
                color: "var(--text-muted)",
                fontSize: "0.85rem",
                margin: "-4px 0 12px 0",
                textAlign: "center",
              }}
            >
              Your first leads will appear here once visitors start chatting
              with your widget.
            </p>
          )}
          <div className="dashboard-bottom-row">
            <ActivityFeed activity={activity} />
            <TodayAppointments
              tenantId={user.tenantId}
              token={token}
              onNavigate={onNavigate}
            />
            <ActionItemsWidget
              tenantId={user.tenantId}
              token={token}
              onNavigate={onNavigate}
            />
            <AIInsightsWidget tenantId={user.tenantId} token={token} />
            <FrontDeskHealthCard tenantId={user.tenantId} token={token} />
            <WidgetEmbed
              apiKey={dashData?.widget_api_key}
              tenantId={user.tenantId}
              widgetConfig={dashData?.widget_config}
              onNavigate={onNavigate}
            />
          </div>
        </div>
        <QuickActions
          onNavigate={onNavigate}
          businessProfile={businessProfile}
        />
      </div>

      {/* CRM Dashboard Widgets */}
      {crmWidgets && (
        <div className="crm-widgets">
          <div className="crm-widget-card">
            <h3>Weekly Stats</h3>
            <div className="crm-stat-grid">
              <div className="crm-stat">
                <div className="crm-stat-value">
                  {crmWidgets.weekly_stats?.new_leads ?? 0}
                </div>
                <div className="crm-stat-label">New Leads</div>
              </div>
              <div className="crm-stat">
                <div className="crm-stat-value">
                  {crmWidgets.weekly_stats?.messages ?? 0}
                </div>
                <div className="crm-stat-label">Messages</div>
              </div>
              <div className="crm-stat">
                <div className="crm-stat-value">
                  {crmWidgets.weekly_stats?.notes_added ?? 0}
                </div>
                <div className="crm-stat-label">Notes</div>
              </div>
              <div className="crm-stat">
                <div className="crm-stat-value">
                  {crmWidgets.weekly_stats?.stage_changes ?? 0}
                </div>
                <div className="crm-stat-label">Stage Changes</div>
              </div>
            </div>
          </div>
          <div className="crm-widget-card">
            <h3>Recent Activity</h3>
            {(crmWidgets.recent_activity || []).slice(0, 5).map((a) => (
              <div
                key={a.id}
                className="attention-item"
                onClick={() =>
                  a.lead_id &&
                  onNavigate("client_profile", { leadId: a.lead_id })
                }
              >
                <span>{a.description}</span>
                <span
                  style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}
                >
                  {(() => {
                    const diff = Date.now() - new Date(a.created_at).getTime();
                    const mins = Math.floor(diff / 60000);
                    if (mins < 60) return `${mins}m`;
                    const hrs = Math.floor(mins / 60);
                    if (hrs < 24) return `${hrs}h`;
                    return `${Math.floor(hrs / 24)}d`;
                  })()}
                </span>
              </div>
            ))}
            {(!crmWidgets.recent_activity ||
              crmWidgets.recent_activity.length === 0) && (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                No recent activity
              </p>
            )}
          </div>
          <div className="crm-widget-card">
            <h3>Needs Attention</h3>
            {(crmWidgets.needs_attention || []).slice(0, 5).map((c) => (
              <div
                key={c.id}
                className="attention-item"
                onClick={() => onNavigate("client_profile", { leadId: c.id })}
              >
                <span>{c.name || c.email || c.phone || "Unknown"}</span>
                <span className={`stage-badge ${c.status}`}>{c.status}</span>
              </div>
            ))}
            {(!crmWidgets.needs_attention ||
              crmWidgets.needs_attention.length === 0) && (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                All caught up!
              </p>
            )}
          </div>
        </div>
      )}

      {selectedLead && (
        <LeadDetailDrawer
          lead={selectedLead}
          onClose={() => setSelectedLead(null)}
          onSave={handleLeadSave}
          onDelete={handleLeadDelete}
        />
      )}
    </div>
  );
}
