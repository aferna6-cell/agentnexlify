import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { fetchLeads, fetchLeadSummary, fetchAutomations, fetchActivity, fetchUsage, fetchWidgetConfig } from "../../utils/api";
import OverviewCards from "./OverviewCards";
import LeadPipeline from "./LeadPipeline";
import ActivityFeed from "./ActivityFeed";
import WidgetEmbed from "./WidgetEmbed";
import QuickActions from "./QuickActions";
import LeadDetailDrawer from "./LeadDetailDrawer";
import SkeletonLoader from "../../components/SkeletonLoader";

export default function Dashboard() {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [leads, setLeads] = useState([]);
  const [summary, setSummary] = useState(null);
  const [automations, setAutomations] = useState([]);
  const [activity, setActivity] = useState([]);
  const [usage, setUsage] = useState(null);
  const [widgetConfig, setWidgetConfig] = useState(null);
  const [selectedLead, setSelectedLead] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!user?.tenantId) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [leadsRes, summaryRes, autoRes, activityRes, usageRes, widgetRes] =
          await Promise.allSettled([
            fetchLeads(user.tenantId, token),
            fetchLeadSummary(user.tenantId, token),
            fetchAutomations(user.tenantId, token),
            fetchActivity(user.tenantId, token),
            fetchUsage(user.tenantId, token),
            fetchWidgetConfig(user.tenantId, token),
          ]);

        if (cancelled) return;

        if (leadsRes.status === "fulfilled") setLeads(leadsRes.value.leads || []);
        if (summaryRes.status === "fulfilled") setSummary(summaryRes.value);
        if (autoRes.status === "fulfilled") setAutomations(autoRes.value.automations || []);
        if (activityRes.status === "fulfilled") setActivity(activityRes.value.activity || []);
        if (usageRes.status === "fulfilled") setUsage(usageRes.value);
        if (widgetRes.status === "fulfilled") setWidgetConfig(widgetRes.value);
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
        <p>Welcome back{user.businessName ? `, ${user.businessName}` : ""}</p>
      </div>

      <OverviewCards
        usage={usage}
        leadCount={leads.length}
        summary={summary}
        automationCount={enabledAutomations.length}
        plan={user.plan}
      />

      <div className="dashboard-main-grid">
        <div className="dashboard-main-content">
          <LeadPipeline leads={leads} onSelectLead={setSelectedLead} />
          <div className="dashboard-bottom-row">
            <ActivityFeed activity={activity} />
            <WidgetEmbed config={widgetConfig} tenantId={user.tenantId} />
          </div>
        </div>
        <QuickActions />
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
