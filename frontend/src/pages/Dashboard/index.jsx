import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import { fetchDashboard, fetchLeads, fetchAutomations, fetchActivity, updateLead, deleteLead, fetchCrmDashboardWidgets } from "../../utils/api";
import OverviewCards from "./OverviewCards";
import LeadPipeline from "./LeadPipeline";
import ActivityFeed from "./ActivityFeed";
import WidgetEmbed from "./WidgetEmbed";
import QuickActions from "./QuickActions";
import LeadDetailDrawer from "./LeadDetailDrawer";
import OnboardingChecklist from "./OnboardingChecklist";
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

  const loadDashboard = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    setError(null);
    try {
      const [dashRes, leadsRes, autoRes, activityRes] =
        await Promise.allSettled([
          fetchDashboard(user.tenantId, token),
          fetchLeads(user.tenantId, token),
          fetchAutomations(user.tenantId, token),
          fetchActivity(user.tenantId, token),
        ]);

      if (dashRes.status === "fulfilled") {
        setDashData(dashRes.value);
        if (onPlanLoaded) onPlanLoaded(dashRes.value.plan);
        setShowOnboarding(!isOnboardingDismissed(user.tenantId));
      }
      if (leadsRes.status === "fulfilled") setLeads(leadsRes.value.leads || []);
      if (autoRes.status === "fulfilled") setAutomations(autoRes.value.automations || []);
      if (activityRes.status === "fulfilled") setActivity(activityRes.value.activity || []);
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
        .catch(() => {});
    }
  }, [user?.tenantId, token]);

  const handleStageDrop = useCallback(async (leadId, newStage) => {
    const prev = leads.slice();
    // Optimistic update
    setLeads((cur) =>
      cur.map((l) => (l.id === leadId ? { ...l, lead_stage: newStage } : l))
    );
    try {
      await updateLead(user.tenantId, token, leadId, { lead_stage: newStage });
    } catch {
      setLeads(prev); // Revert on failure
    }
  }, [leads, user?.tenantId, token]);

  const handleLeadSave = useCallback(async (leadId, updates) => {
    const updated = await updateLead(user.tenantId, token, leadId, updates);
    setLeads((cur) => cur.map((l) => (l.id === leadId ? { ...l, ...updated } : l)));
    setSelectedLead((cur) => (cur?.id === leadId ? { ...cur, ...updated } : cur));
  }, [user?.tenantId, token]);

  const handleLeadDelete = useCallback(async (leadId) => {
    await deleteLead(user.tenantId, token, leadId);
    setLeads((cur) => cur.filter((l) => l.id !== leadId));
    setSelectedLead(null);
  }, [user?.tenantId, token]);

  if (loading) return <SkeletonLoader />;

  if (error) {
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
        />
      )}

      <OverviewCards
        conversationsUsed={dashData?.conversations_used_this_month ?? 0}
        conversationsLimit={dashData?.monthly_conversation_limit ?? 50}
        leadCount={dashData?.leads_count ?? leads.length}
        automationCount={enabledAutomations.length}
        plan={dashData?.plan ?? user.plan}
        onNavigate={onNavigate}
        hotLeadsCount={dashData?.hot_leads_count ?? 0}
      />

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
            <WidgetEmbed
              apiKey={dashData?.widget_api_key}
              tenantId={user.tenantId}
              widgetConfig={dashData?.widget_config}
            />
          </div>
        </div>
        <QuickActions onNavigate={onNavigate} />
      </div>

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
