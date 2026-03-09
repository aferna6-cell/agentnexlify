import { useState, useCallback, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchTrialStatus } from "../utils/api";
import LoginPage from "./LoginPage";
import Sidebar from "./Sidebar";
import SkeletonLoader from "./SkeletonLoader";
import Dashboard from "../pages/Dashboard";
import LeadsPage from "../pages/LeadsPage";
import ClientList from "../pages/Dashboard/ClientList";
import ClientProfile from "../pages/Dashboard/ClientProfile";
import Calendar from "../pages/Calendar";
import Availability from "../pages/Availability";
import AutomationsPage from "../pages/Automations";
import ConversationsPage from "../pages/ConversationsPage";
import WidgetPage from "../pages/WidgetPage";
import FaqManagerPage from "../pages/FaqManagerPage";
import BillingPage from "../pages/BillingPage";
import SettingsPage from "../pages/SettingsPage";
import IntegrationsPage from "../pages/IntegrationsPage";
import AnalyticsPage from "../pages/AnalyticsPage";
import TeamPage from "../pages/TeamPage";
import BusinessPageSettings from "../pages/BusinessPageSettings";

const pages = {
  dashboard: Dashboard,
  analytics: AnalyticsPage,
  leads: LeadsPage,
  clients: ClientList,
  client_profile: ClientProfile,
  calendar: Calendar,
  availability: Availability,
  conversations: ConversationsPage,
  automations: AutomationsPage,
  widget: WidgetPage,
  faq: FaqManagerPage,
  team: TeamPage,
  billing: BillingPage,
  integrations: IntegrationsPage,
  settings: SettingsPage,
  business_page: BusinessPageSettings,
};

function TrialBanner({ trialData, onNavigate }) {
  if (!trialData || trialData.plan !== "free" || trialData.days_remaining === null) return null;

  const expired = trialData.is_expired;
  const days = trialData.days_remaining;

  return (
    <div
      style={{
        padding: "10px 20px",
        background: expired ? "#dc2626" : days <= 7 ? "#f59e0b" : "#3b82f6",
        color: expired ? "#fff" : days <= 7 ? "#0a0a0f" : "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        fontSize: "0.85rem",
        fontWeight: 500,
        flexShrink: 0,
      }}
    >
      <span>
        {expired
          ? "Your free trial has expired. Upgrade to keep your AI assistant running."
          : `Free trial: ${days} day${days !== 1 ? "s" : ""} remaining. Upgrade anytime for unlimited access.`}
      </span>
      <button
        onClick={() => onNavigate("billing")}
        style={{
          background: expired ? "#fff" : "rgba(255,255,255,0.2)",
          color: expired ? "#dc2626" : "inherit",
          border: "none",
          padding: "6px 16px",
          borderRadius: "6px",
          cursor: "pointer",
          fontWeight: 600,
          fontSize: "0.8rem",
          whiteSpace: "nowrap",
          marginLeft: "12px",
        }}
      >
        Upgrade Now &rarr;
      </button>
    </div>
  );
}

export default function App() {
  const { user, token } = useAuth();
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [pageData, setPageData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activePlan, setActivePlan] = useState(null);
  const [trialData, setTrialData] = useState(null);

  useEffect(() => {
    if (!user?.tenantId || !token) return;
    fetchTrialStatus(user.tenantId, token)
      .then(setTrialData)
      .catch(() => {});
  }, [user?.tenantId, token]);

  // Refresh trial data when plan changes
  useEffect(() => {
    if (activePlan && activePlan !== "free") {
      setTrialData(null);
    }
  }, [activePlan]);

  const handleNavigate = useCallback(
    (page, data = null) => {
      if (page === currentPage && !data) return;
      setLoading(true);
      setTimeout(() => {
        setCurrentPage(page);
        setPageData(data);
        setLoading(false);
      }, 200);
    },
    [currentPage]
  );

  if (!user) return <LoginPage />;

  const PageComponent = pages[currentPage] || Dashboard;

  return (
    <div className="app">
      <Sidebar currentPage={currentPage} onNavigate={handleNavigate} plan={activePlan} />
      <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
        <TrialBanner trialData={trialData} onNavigate={handleNavigate} />
        <main className="content">
          {loading ? (
            <SkeletonLoader />
          ) : (
            <PageComponent
              onNavigate={handleNavigate}
              onPlanLoaded={setActivePlan}
              pageData={pageData}
            />
          )}
        </main>
      </div>
    </div>
  );
}
