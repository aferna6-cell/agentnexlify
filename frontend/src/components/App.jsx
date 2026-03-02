import { useState, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import LoginPage from "./LoginPage";
import Sidebar from "./Sidebar";
import SkeletonLoader from "./SkeletonLoader";
import Dashboard from "../pages/Dashboard";
import ComingSoon from "../pages/Dashboard/ComingSoon";

function Leads() { return <ComingSoon title="Leads" />; }
function Conversations() { return <ComingSoon title="Conversations" />; }
function Automations() { return <ComingSoon title="Automations" />; }
function Widget() { return <ComingSoon title="Widget" />; }
function FaqManager() { return <ComingSoon title="FAQ Manager" />; }
function Billing() { return <ComingSoon title="Billing" />; }
function Settings() { return <ComingSoon title="Settings" />; }

const pages = {
  dashboard: Dashboard,
  leads: Leads,
  conversations: Conversations,
  automations: Automations,
  widget: Widget,
  faq: FaqManager,
  billing: Billing,
  settings: Settings,
};

export default function App() {
  const { user } = useAuth();
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [loading, setLoading] = useState(false);

  const handleNavigate = useCallback(
    (page) => {
      if (page === currentPage) return;
      setLoading(true);
      setTimeout(() => {
        setCurrentPage(page);
        setLoading(false);
      }, 200);
    },
    [currentPage]
  );

  if (!user) return <LoginPage />;

  const PageComponent = pages[currentPage] || Dashboard;

  return (
    <div className="app">
      <Sidebar currentPage={currentPage} onNavigate={handleNavigate} />
      <main className="content">
        {loading ? <SkeletonLoader /> : <PageComponent onNavigate={handleNavigate} />}
      </main>
    </div>
  );
}
