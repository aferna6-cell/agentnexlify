import {
  useState,
  useCallback,
  useEffect,
  lazy,
  Suspense,
  Component,
} from "react";
import { useAuth } from "../context/AuthContext";
import { fetchTrialStatus } from "../utils/api/dashboard";
import LoginPage from "./LoginPage";
import NotificationBell from "./NotificationBell";
import Sidebar from "./Sidebar";
import SkeletonLoader from "./SkeletonLoader";

class PageErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidUpdate(prevProps) {
    if (prevProps.pageKey !== this.props.pageKey) {
      this.setState({ hasError: false, error: null });
    }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            padding: 40,
            textAlign: "center",
            color: "var(--text-muted)",
          }}
        >
          <div style={{ fontSize: "1.5rem", marginBottom: 12 }}>
            Something went wrong
          </div>
          <p style={{ marginBottom: 16 }}>
            {this.state.error?.message || "An unexpected error occurred."}
          </p>
          <button
            className="btn-primary"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

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
const AgentControlCenterPage = lazy(
  () => import("../pages/AgentControlCenterPage"),
);
const TeamPage = lazy(() => import("../pages/TeamPage"));
const BusinessPageSettings = lazy(
  () => import("../pages/BusinessPageSettings"),
);
const ReviewsPage = lazy(() => import("../pages/ReviewsPage"));
const ContentStudioPage = lazy(() => import("../pages/ContentStudioPage"));
const ContentRepurposePage = lazy(
  () => import("../pages/ContentRepurposePage"),
);
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
const MarketingCampaignsPage = lazy(
  () => import("../pages/MarketingCampaignsPage"),
);
const MarketingDashboardPage = lazy(
  () => import("../pages/MarketingDashboardPage"),
);
const ABTestsPage = lazy(() => import("../pages/ABTestsPage"));
const AutomationRulesPage = lazy(() => import("../pages/AutomationRulesPage"));
const TriggerLogsPage = lazy(() => import("../pages/TriggerLogsPage"));
const EmailSequencesPage = lazy(() => import("../pages/EmailSequencesPage"));
const InvoicesPage = lazy(() => import("../pages/InvoicesPage"));
const DocumentsPage = lazy(() => import("../pages/DocumentsPage"));
const PipelinePage = lazy(() => import("../pages/PipelinePage"));
const PipelineAutomationsPage = lazy(
  () => import("../pages/PipelineAutomationsPage"),
);
const SmartListsPage = lazy(() => import("../pages/SmartListsPage"));
const FormBuilderPage = lazy(() => import("../pages/FormBuilderPage"));
const CSATPage = lazy(() => import("../pages/CSATPage"));
const WaitlistPage = lazy(() => import("../pages/WaitlistPage"));
const ScoringConfigPage = lazy(() => import("../pages/ScoringConfigPage"));
const TeamActivityPage = lazy(() => import("../pages/TeamActivityPage"));
const SupportPage = lazy(() => import("../pages/SupportPage"));
const AdminAnalyticsPage = lazy(() => import("../pages/AdminAnalyticsPage"));
const AdminPromotionsPage = lazy(() => import("../pages/AdminPromotionsPage"));

const pages = {
  dashboard: Dashboard,
  analytics: AnalyticsPage,
  control_center: AgentControlCenterPage,
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
  content_repurpose: ContentRepurposePage,
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
  marketing_dashboard: MarketingDashboardPage,
  ab_tests: ABTestsPage,
  automation_rules: AutomationRulesPage,
  trigger_logs: TriggerLogsPage,
  email_sequences: EmailSequencesPage,
  invoices: InvoicesPage,
  documents: DocumentsPage,
  pipeline: PipelinePage,
  pipeline_automations: PipelineAutomationsPage,
  smart_lists: SmartListsPage,
  form_builder: FormBuilderPage,
  csat: CSATPage,
  waitlist: WaitlistPage,
  scoring_config: ScoringConfigPage,
  team_activity: TeamActivityPage,
  support: SupportPage,
  admin_analytics: AdminAnalyticsPage,
  admin_promotions: AdminPromotionsPage,
};

// --------------------------------------------------------------------------
// URL ↔ page-key routing (supports direct navigation and browser back/forward)
// --------------------------------------------------------------------------
const PAGE_TO_PATH = {
  dashboard: "/dashboard",
  analytics: "/dashboard/analytics",
  control_center: "/dashboard/agent-control",
  leads: "/dashboard/leads",
  clients: "/dashboard/clients",
  client_profile: "/dashboard/client-profile",
  pipeline: "/dashboard/pipeline",
  pipeline_automations: "/dashboard/pipeline-automations",
  calendar: "/dashboard/calendar",
  availability: "/dashboard/availability",
  conversations: "/dashboard/conversations",
  automations: "/dashboard/automations",
  widget: "/dashboard/widget",
  faq: "/dashboard/faq",
  team: "/dashboard/team",
  billing: "/dashboard/billing",
  integrations: "/dashboard/integrations",
  settings: "/dashboard/settings",
  business_page: "/dashboard/business-page",
  reviews: "/dashboard/reviews",
  content_studio: "/dashboard/content-studio",
  menu: "/dashboard/menu",
  orders: "/dashboard/orders",
  jobs: "/dashboard/jobs",
  action_items: "/dashboard/action-items",
  snippets: "/dashboard/snippets",
  chat_flows: "/dashboard/chat-flows",
  mcp_setup: "/dashboard/mcp-setup",
  bids: "/dashboard/bids",
  client_portal: "/dashboard/client-portal",
  calls: "/dashboard/calls",
  local_seo: "/dashboard/local-seo",
  social_media: "/dashboard/social-media",
  campaigns: "/dashboard/campaigns",
  marketing_dashboard: "/dashboard/marketing",
  ab_tests: "/dashboard/ab-tests",
  automation_rules: "/dashboard/automation-rules",
  trigger_logs: "/dashboard/trigger-logs",
  email_sequences: "/dashboard/sequences",
  invoices: "/dashboard/invoices",
  documents: "/dashboard/documents",
  smart_lists: "/dashboard/smart-lists",
  form_builder: "/dashboard/forms",
  csat: "/dashboard/csat",
  waitlist: "/dashboard/waitlist",
  scoring_config: "/dashboard/scoring",
  team_activity: "/dashboard/team-activity",
  support: "/dashboard/support",
  admin_analytics: "/admin/analytics",
  admin_promotions: "/admin/promotions",
};

const PATH_TO_PAGE = Object.fromEntries(
  Object.entries(PAGE_TO_PATH).map(([key, path]) => [path, key]),
);

function pageFromPath(pathname) {
  if (PATH_TO_PAGE[pathname]) return PATH_TO_PAGE[pathname];
  if (pathname.startsWith("/dashboard")) return "dashboard";
  if (pathname.startsWith("/admin/")) {
    // Map /admin/analytics -> admin_analytics, /admin/promotions -> admin_promotions
    const slug = pathname.replace("/admin/", "").replace(/-/g, "_");
    return `admin_${slug}`;
  }
  return null;
}

function TrialBanner({ trialData, onNavigate }) {
  if (
    !trialData ||
    trialData.plan !== "free" ||
    trialData.days_remaining === null
  )
    return null;

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
  const [currentPage, setCurrentPage] = useState(
    () => pageFromPath(window.location.pathname) || "dashboard",
  );
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

  // Sync page state with browser back/forward buttons
  useEffect(() => {
    const onPop = () => {
      const page = pageFromPath(window.location.pathname) || "dashboard";
      setCurrentPage(page);
      setPageData(null);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const handleNavigate = useCallback(
    (page, data = null) => {
      if (page === currentPage && !data) return;
      const path = PAGE_TO_PATH[page] || "/dashboard";
      window.history.pushState(null, "", path);
      setLoading(true);
      setTimeout(() => {
        setCurrentPage(page);
        setPageData(data);
        setLoading(false);
      }, 200);
    },
    [currentPage],
  );

  if (!user) {
    return <LoginPage />;
  }

  const PageComponent = pages[currentPage] || Dashboard;

  return (
    <div className="app">
      <Sidebar
        currentPage={currentPage}
        onNavigate={handleNavigate}
        plan={activePlan}
      />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          flex: 1,
          minWidth: 0,
        }}
      >
        <TrialBanner trialData={trialData} onNavigate={handleNavigate} />
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            padding: "8px 24px 0",
            flexShrink: 0,
          }}
        >
          <NotificationBell onNavigate={handleNavigate} />
        </div>
        <main className="content">
          {loading ? (
            <SkeletonLoader />
          ) : (
            <PageErrorBoundary pageKey={currentPage}>
              <Suspense fallback={<SkeletonLoader />}>
                <PageComponent
                  onNavigate={handleNavigate}
                  onPlanLoaded={setActivePlan}
                  pageData={pageData}
                />
              </Suspense>
            </PageErrorBoundary>
          )}
        </main>
      </div>
    </div>
  );
}
