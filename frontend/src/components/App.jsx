import { useState, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import LoginPage from "./LoginPage";
import Sidebar from "./Sidebar";
import SkeletonLoader from "./SkeletonLoader";
import Dashboard from "../pages/Dashboard";
import ComingSoon from "../pages/Dashboard/ComingSoon";
import LeadsPage from "../pages/LeadsPage";
import ClientList from "../pages/Dashboard/ClientList";
import ClientProfile from "../pages/Dashboard/ClientProfile";
import Calendar from "../pages/Calendar";
import Availability from "../pages/Availability";

import AutomationsPage from "../pages/Automations";

function Conversations() { return <ComingSoon title="Conversations" />; }
function Widget() { return <ComingSoon title="Widget" />; }
function FaqManager() { return <ComingSoon title="FAQ Manager" />; }
function Billing() { return <ComingSoon title="Billing" />; }
function Settings() { return <ComingSoon title="Settings" />; }

const pages = {
  dashboard: Dashboard,
  leads: LeadsPage,
  clients: ClientList,
  client_profile: ClientProfile,
  calendar: Calendar,
  availability: Availability,
  conversations: Conversations,
  automations: AutomationsPage,
  widget: Widget,
  faq: FaqManager,
  billing: Billing,
  settings: Settings,
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
