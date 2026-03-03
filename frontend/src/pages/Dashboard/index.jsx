import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { fetchDashboard, fetchLeads, fetchAutomations, fetchActivity } from "../../utils/api";
import OverviewCards from "./OverviewCards";
import LeadPipeline from "./LeadPipeline";
import ActivityFeed from "./ActivityFeed";
import WidgetEmbed from "./WidgetEmbed";
import QuickActions from "./QuickActions";
import LeadDetailDrawer from "./LeadDetailDrawer";
import SkeletonLoader from "../../components/SkeletonLoader";

export default function Dashboard({ onNavigate, onPlanLoaded }) {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [leads, setLeads] = useState([]);
  const [dashData, setDashData] = useState(null);
  const [automations, setAutomations] = useState([]);
  const [activity, setActivity] = useState([]);
  const [selectedLead, setSelectedLead] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!user?.tenantId) return;
    let cancelled = false;

    async function load() {
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

        if (cancelled) return;

        if (dashRes.status === "fulfilled") {
          setDashData(dashRes.value);
          if (onPlanLoaded) onPlanLoaded(dashRes.value.plan);
        }
        if (leadsRes.status === "fulfilled") setLeads(leadsRes.value.leads || []);
        if (autoRes.status === "fulfilled") setAutomations(autoRes.value.automations || []);
        if (activityRes.status === "fulfilled") setActivity(activityRes.value.activity || []);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
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

      <OverviewCards
        conversationsUsed={dashData?.conversations_used_this_month ?? 0}
        conversationsLimit={dashData?.monthly_conversation_limit ?? 50}
        leadCount={dashData?.leads_count ?? leads.length}
        automationCount={enabledAutomations.length}
        plan={dashData?.plan ?? user.plan}
      />

      <div className="dashboard-main-grid">
        <div className="dashboard-main-content">
          <LeadPipeline leads={leads} onSelectLead={setSelectedLead} />
          <div className="dashboard-bottom-row">
            <ActivityFeed activity={activity} />
            <WidgetEmbed
              apiKey={dashData?.widget_api_key}
              tenantId={user.tenantId}
            />
          </div>
        </div>
        <QuickActions onNavigate={onNavigate} />
      </div>

      {selectedLead && (
        <LeadDetailDrawer
          lead={selectedLead}
          onClose={() => setSelectedLead(null)}
        />
      )}
    </div>
  );
}
