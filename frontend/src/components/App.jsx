import { useState, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
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
  billing: BillingPage,
  integrations: IntegrationsPage,
  settings: SettingsPage,
};

export default function App() {
  const { user } = useAuth();
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [pageData, setPageData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activePlan, setActivePlan] = useState(null);

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
  );
}
