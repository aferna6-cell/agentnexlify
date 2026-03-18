import { useState, useCallback, useEffect, lazy, Suspense } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchTrialStatus } from "../utils/api";
import LoginPage from "./LoginPage";
import NotificationBell from "./NotificationBell";
import Sidebar from "./Sidebar";
import SkeletonLoader from "./SkeletonLoader";

// Lazy-load all dashboard pages — each becomes its own chunk
const Dashboard = lazy(() => import("../pages/Dashboard"));
const LeadsPage = lazy(() => import("../pages/LeadsPage"));
const ClientList = lazy(() => import("../pages/Dashboard/ClientList"));
const ClientProfile = lazy(() => import("../pages/Dashboard/ClientProfile"));
const Calendar = lazy(() => import("../pages/Calendar"));
const Availability = lazy(() => import("../pages/Availability"));
const AutomationsPage = lazy(() => import("../pages/Automations"));
const ConversationsPage = lazy(() => import("../pages/ConversationsPage"));
const WidgetPage = lazy(() => import("../pages/WidgetPage"));
const FaqManagerPage = lazy(() => import("../pages/FaqManagerPage"));
const BillingPage = lazy(() => import("../pages/BillingPage"));
const SettingsPage = lazy(() => import("../pages/SettingsPage"));
const IntegrationsPage = lazy(() => import("../pages/IntegrationsPage"));
const AnalyticsPage = lazy(() => import("../pages/AnalyticsPage"));
const TeamPage = lazy(() => import("../pages/TeamPage"));
const BusinessPageSettings = lazy(() => import("../pages/BusinessPageSettings"));
const ReviewsPage = lazy(() => import("../pages/ReviewsPage"));
const ContentStudioPage = lazy(() => import("../pages/ContentStudioPage"));
const MenuPage = lazy(() => import("../pages/MenuPage"));
const OrdersPage = lazy(() => import("../pages/OrdersPage"));
const JobsPage = lazy(() => import("../pages/JobsPage"));
const ActionItemsPage = lazy(() => import("../pages/ActionItemsPage"));
const SnippetsPage = lazy(() => import("../pages/SnippetsPage"));
const ChatFlowBuilderPage = lazy(() => import("../pages/ChatFlowBuilderPage"));
const MCPSetupPage = lazy(() => import("../pages/MCPSetupPage"));
const BidsPage = lazy(() => import("../pages/BidsPage"));
const ClientPortalPage = lazy(() => import("../pages/ClientPortalPage"));
const CallsPage = lazy(() => import("../pages/CallsPage"));
const LocalSEOPage = lazy(() => import("../pages/LocalSEOPage"));
const SocialMediaPage = lazy(() => import("../pages/SocialMediaPage"));
const MarketingCampaignsPage = lazy(() => import("../pages/MarketingCampaignsPage"));
const InvoicesPage = lazy(() => import("../pages/InvoicesPage"));
const PipelinePage = lazy(() => import("../pages/PipelinePage"));

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
  reviews: ReviewsPage,
  content_studio: ContentStudioPage,
  menu: MenuPage,
  orders: OrdersPage,
  jobs: JobsPage,
  action_items: ActionItemsPage,
  snippets: SnippetsPage,
  chat_flows: ChatFlowBuilderPage,
  mcp_setup: MCPSetupPage,
  bids: BidsPage,
  client_portal: ClientPortalPage,
  calls: CallsPage,
  local_seo: LocalSEOPage,
  social_media: SocialMediaPage,
  campaigns: MarketingCampaignsPage,
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
      .catch((err) => {
        console.warn("Failed to fetch trial status:", err.message || err);
      });
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
        <div style={{
          display: "flex",
          justifyContent: "flex-end",
          alignItems: "center",
          padding: "8px 24px 0",
          flexShrink: 0,
        }}>
          <NotificationBell onNavigate={handleNavigate} />
        </div>
        <main className="content">
          {loading ? (
            <SkeletonLoader />
          ) : (
            <Suspense fallback={<SkeletonLoader />}>
              <PageComponent
                onNavigate={handleNavigate}
                onPlanLoaded={setActivePlan}
                pageData={pageData}
              />
            </Suspense>
          )}
        </main>
      </div>
    </div>
  );
}
