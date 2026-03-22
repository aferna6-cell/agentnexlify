import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import { fetchDashboard, fetchActivity, fetchOnboardingStatus } from "../../utils/api/dashboard";
import { fetchLeads, updateLead, deleteLead } from "../../utils/api/leads";
import { fetchSequenceStats, fetchAutomations } from "../../utils/api/automations";
import { fetchCrmDashboardWidgets } from "../../utils/api/crm";
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

  const loadDashboard = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    setError(null);
    try {
      const [dashRes, leadsRes, autoRes, activityRes, crmRes, seqStatsRes, onboardRes] =
        await Promise.allSettled([
          fetchDashboard(user.tenantId, token),
          fetchLeads(user.tenantId, token),
          fetchAutomations(user.tenantId, token),
          fetchActivity(user.tenantId, token),
          fetchCrmDashboardWidgets(user.tenantId, token),
          fetchSequenceStats(user.tenantId, token),
          fetchOnboardingStatus(user.tenantId, token),
        ]);

      if (dashRes.status === "fulfilled") {
        setDashData(dashRes.value);
        if (onPlanLoaded) onPlanLoaded(dashRes.value.plan);
        setShowOnboarding(!isOnboardingDismissed(user.tenantId));
      }
      if (leadsRes.status === "fulfilled") setLeads(leadsRes.value.leads || []);
      if (autoRes.status === "fulfilled") setAutomations(autoRes.value.automations || []);
      if (activityRes.status === "fulfilled") setActivity(activityRes.value.activity || []);
      if (crmRes.status === "fulfilled") setCrmWidgets(crmRes.value);
      if (seqStatsRes.status === "fulfilled") setSeqStats(seqStatsRes.value);
      if (onboardRes.status === "fulfilled") setOnboardingStatus(onboardRes.value);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, onPlanLoaded]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const handleStepComplete = useCallback(() => {
    if (user?.tenantId) {
      fetchDashboard(user.tenantId, token)
        .then((data) => setDashData(data))
        .catch((err) => console.warn("Dashboard refresh failed:", err.message));
    }
  }, [user?.tenantId, token]);

  const handleStageDrop = useCallback(async (leadId, newStage) => {
    const prev = leads.slice();
    // Optimistic update
    setLeads((cur) =>
      cur.map((l) => (l.id === leadId ? { ...l, status: newStage } : l))
    );
    try {
      await updateLead(user.tenantId, token, leadId, { status: newStage });
    } catch (err) {
      setLeads(prev); // Revert on failure
      setError(err.body?.detail || err.message || "Failed to update lead stage.");
      setTimeout(() => setError(null), 5000);
    }
  }, [leads, user?.tenantId, token]);

  const handleLeadSave = useCallback(async (leadId, updates) => {
    try {
      const updated = await updateLead(user.tenantId, token, leadId, updates);
      setLeads((cur) => cur.map((l) => (l.id === leadId ? { ...l, ...updated } : l)));
      setSelectedLead((cur) => (cur?.id === leadId ? { ...cur, ...updated } : cur));
    } catch (err) {
      setError(err.body?.detail || err.message || "Failed to save lead.");
      setTimeout(() => setError(null), 5000);
    }
  }, [user?.tenantId, token]);

  const handleLeadDelete = useCallback(async (leadId) => {
    try {
      await deleteLead(user.tenantId, token, leadId);
      setLeads((cur) => cur.filter((l) => l.id !== leadId));
      setSelectedLead(null);
    } catch (err) {
      setError(err.body?.detail || err.message || "Failed to delete lead.");
      setTimeout(() => setError(null), 5000);
    }
  }, [user?.tenantId, token]);

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

  return (
    <div className="fade-in">
      {error && dashData && <div className="error-banner" style={{ marginBottom: "1rem" }}>{error}</div>}
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Welcome back{dashData?.business_name ? `, ${dashData.business_name}` : user.businessName ? `, ${user.businessName}` : ""}</p>
      </div>

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

      <OverviewCards
        conversationsUsed={dashData?.conversations_used_this_month ?? 0}
        leadCount={dashData?.leads_count ?? leads.length}
        automationCount={seqStats?.active_sequences ?? enabledAutomations.length}
        plan={dashData?.plan ?? user.plan}
        onNavigate={onNavigate}
        hotLeadsCount={dashData?.hot_leads_count ?? 0}
        emailsSentToday={seqStats?.emails_sent_today ?? 0}
        missedCallsThisWeek={dashData?.missed_calls_this_week ?? null}
      />
      <div className="analytics-link" onClick={() => onNavigate("analytics")}>
        View Analytics &rarr;
      </div>

      <div className="dashboard-main-grid">
        <div className="dashboard-main-content">
          <LeadPipeline
            leads={leads}
            onSelectLead={setSelectedLead}
            onNavigate={onNavigate}
            onStageDrop={handleStageDrop}
          />
          <div className="dashboard-bottom-row">
            <ActivityFeed activity={activity} />
            <TodayAppointments tenantId={user.tenantId} token={token} onNavigate={onNavigate} />
            <ActionItemsWidget tenantId={user.tenantId} token={token} onNavigate={onNavigate} />
            <AIInsightsWidget tenantId={user.tenantId} token={token} />
            <WidgetEmbed
              apiKey={dashData?.widget_api_key}
              tenantId={user.tenantId}
              widgetConfig={dashData?.widget_config}
              onNavigate={onNavigate}
            />
          </div>
        </div>
        <QuickActions onNavigate={onNavigate} />
      </div>

      {/* CRM Dashboard Widgets */}
      {crmWidgets && (
        <div className="crm-widgets">
          <div className="crm-widget-card">
            <h3>Weekly Stats</h3>
            <div className="crm-stat-grid">
              <div className="crm-stat">
                <div className="crm-stat-value">{crmWidgets.weekly_stats?.new_leads ?? 0}</div>
                <div className="crm-stat-label">New Leads</div>
              </div>
              <div className="crm-stat">
                <div className="crm-stat-value">{crmWidgets.weekly_stats?.messages ?? 0}</div>
                <div className="crm-stat-label">Messages</div>
              </div>
              <div className="crm-stat">
                <div className="crm-stat-value">{crmWidgets.weekly_stats?.notes_added ?? 0}</div>
                <div className="crm-stat-label">Notes</div>
              </div>
              <div className="crm-stat">
                <div className="crm-stat-value">{crmWidgets.weekly_stats?.stage_changes ?? 0}</div>
                <div className="crm-stat-label">Stage Changes</div>
              </div>
            </div>
          </div>
          <div className="crm-widget-card">
            <h3>Recent Activity</h3>
            {(crmWidgets.recent_activity || []).slice(0, 5).map((a) => (
              <div key={a.id} className="attention-item" onClick={() => a.lead_id && onNavigate("client_profile", { leadId: a.lead_id })}>
                <span>{a.description}</span>
                <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
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
            {(!crmWidgets.recent_activity || crmWidgets.recent_activity.length === 0) && (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>No recent activity</p>
            )}
          </div>
          <div className="crm-widget-card">
            <h3>Needs Attention</h3>
            {(crmWidgets.needs_attention || []).slice(0, 5).map((c) => (
              <div key={c.id} className="attention-item" onClick={() => onNavigate("client_profile", { leadId: c.id })}>
                <span>{c.name || c.email || c.phone || "Unknown"}</span>
                <span className={`stage-badge ${c.status}`}>{c.status}</span>
              </div>
            ))}
            {(!crmWidgets.needs_attention || crmWidgets.needs_attention.length === 0) && (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>All caught up!</p>
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
