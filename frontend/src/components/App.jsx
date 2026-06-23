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
import { fetchOsPendingDeliverables } from "../utils/api/os";
import DemoBanner from "./DemoBanner";
import LoginPage from "./LoginPage";
import MarketingUpsell, {
  MARKETING_GATED_KEYS,
  MARKETING_PLANS,
} from "./MarketingUpsell";
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

// Lazy-load all dashboard pages - each becomes its own chunk
const Dashboard = lazy(() => import("../pages/Dashboard"));
const LeadsPage = lazy(() => import("../pages/LeadsPage"));
const ClientList = lazy(() => import("../pages/Dashboard/ClientList"));
const ClientProfile = lazy(() => import("../pages/Dashboard/ClientProfile"));
const Calendar = lazy(() => import("../pages/Calendar"));
const Availability = lazy(() => import("../pages/Availability"));
const ConversationsPage = lazy(() => import("../pages/ConversationsPage"));
const WidgetPage = lazy(() => import("../pages/WidgetPage"));
const FaqManagerPage = lazy(() => import("../pages/FaqManagerPage"));
const BillingPage = lazy(() => import("../pages/BillingPage"));
const SettingsPage = lazy(() => import("../pages/SettingsPage"));
const SettingsInboundChannels = lazy(
  () => import("../pages/SettingsInboundChannels"),
);
const IntegrationsPage = lazy(() => import("../pages/IntegrationsPage"));
const AnalyticsPage = lazy(() => import("../pages/AnalyticsPage"));
const AgentOS = lazy(() => import("../pages/AgentOS"));
const TeamPage = lazy(() => import("../pages/TeamPage"));
const BusinessPageSettings = lazy(
  () => import("../pages/BusinessPageSettings"),
);
const MCPSetupPage = lazy(() => import("../pages/MCPSetupPage"));
const LocalSEOPage = lazy(() => import("../pages/LocalSEOPage"));
const SocialMediaPage = lazy(() => import("../pages/SocialMediaPage"));
const MarketingCampaignsPage = lazy(
  () => import("../pages/MarketingCampaignsPage"),
);
const MarketingDashboardPage = lazy(
  () => import("../pages/MarketingDashboardPage"),
);
const AutomationRulesPage = lazy(() => import("../pages/AutomationRulesPage"));
const TriggerLogsPage = lazy(() => import("../pages/TriggerLogsPage"));
const InvoicesPage = lazy(() => import("../pages/InvoicesPage"));
const DocumentsPage = lazy(() => import("../pages/DocumentsPage"));
const PipelinePage = lazy(() => import("../pages/PipelinePage"));
const SupportPage = lazy(() => import("../pages/SupportPage"));
const AdminAnalyticsPage = lazy(() => import("../pages/AdminAnalyticsPage"));
const AdminHealthPage = lazy(() => import("../pages/AdminHealthPage"));
const AdminPromotionsPage = lazy(() => import("../pages/AdminPromotionsPage"));
const AdminFunnelPage = lazy(() => import("../pages/AdminFunnelPage"));
const AdminTenantHealthPage = lazy(
  () => import("../pages/AdminTenantHealthPage"),
);
const IntegrationsKeysPage = lazy(
  () => import("../pages/Settings/IntegrationsKeysPage"),
);
const ReferralPage = lazy(() => import("../pages/ReferralPage"));

const pages = {
  dashboard: Dashboard,
  analytics: AnalyticsPage,
  agent_os: AgentOS,
  leads: LeadsPage,
  clients: ClientList,
  client_profile: ClientProfile,
  calendar: Calendar,
  availability: Availability,
  conversations: ConversationsPage,
  widget: WidgetPage,
  faq: FaqManagerPage,
  team: TeamPage,
  billing: BillingPage,
  integrations: IntegrationsPage,
  settings: SettingsPage,
  inbound_channels: SettingsInboundChannels,
  business_page: BusinessPageSettings,
  mcp_setup: MCPSetupPage,
  local_seo: LocalSEOPage,
  social_media: SocialMediaPage,
  campaigns: MarketingCampaignsPage,
  marketing_dashboard: MarketingDashboardPage,
  automation_rules: AutomationRulesPage,
  trigger_logs: TriggerLogsPage,
  invoices: InvoicesPage,
  documents: DocumentsPage,
  pipeline: PipelinePage,
  support: SupportPage,
  integration_keys: IntegrationsKeysPage,
  admin_analytics: AdminAnalyticsPage,
  admin_health: AdminHealthPage,
  admin_promotions: AdminPromotionsPage,
  admin_funnel: AdminFunnelPage,
  admin_tenant_health: AdminTenantHealthPage,
  referral: ReferralPage,
};

// --------------------------------------------------------------------------
// URL ↔ page-key routing (supports direct navigation and browser back/forward)
// --------------------------------------------------------------------------
const PAGE_TO_PATH = {
  dashboard: "/dashboard/overview",
  analytics: "/dashboard/analytics",
  agent_os: "/dashboard/agent-os",
  leads: "/dashboard/leads",
  clients: "/dashboard/clients",
  client_profile: "/dashboard/client-profile",
  pipeline: "/dashboard/pipeline",
  calendar: "/dashboard/calendar",
  availability: "/dashboard/availability",
  conversations: "/dashboard/conversations",
  widget: "/dashboard/widget",
  faq: "/dashboard/faq",
  team: "/dashboard/team",
  billing: "/dashboard/billing",
  integrations: "/dashboard/integrations",
  settings: "/dashboard/settings",
  inbound_channels: "/dashboard/inbound-channels",
  business_page: "/dashboard/business-page",
  mcp_setup: "/dashboard/mcp-setup",
  local_seo: "/dashboard/local-seo",
  social_media: "/dashboard/social-media",
  campaigns: "/dashboard/campaigns",
  marketing_dashboard: "/dashboard/marketing",
  automation_rules: "/dashboard/automation-rules",
  trigger_logs: "/dashboard/trigger-logs",
  invoices: "/dashboard/invoices",
  documents: "/dashboard/documents",
  support: "/dashboard/support",
  integration_keys: "/settings/integration-keys",
  admin_analytics: "/admin/analytics",
  admin_health: "/admin/health",
  admin_promotions: "/admin/promotions",
  admin_funnel: "/admin/funnel",
  admin_tenant_health: "/admin/tenant-health",
  referral: "/dashboard/referral",
};

const PATH_TO_PAGE = Object.fromEntries(
  Object.entries(PAGE_TO_PATH).map(([key, path]) => [path, key]),
);

function pageFromPath(pathname) {
  if (PATH_TO_PAGE[pathname]) return PATH_TO_PAGE[pathname];
  // Front door: bare /dashboard (old bookmarks, post-login) and unknown
  // /dashboard/* paths land on the Agent OS conversation. The classic
  // dashboard lives at its own exact path, /dashboard/overview.
  if (pathname.startsWith("/dashboard")) return "agent_os";
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
  // Front door: a logged-in user lands on the Agent OS conversation.
  // Every classic page stays deep-linkable via its exact /dashboard/* path.
  const [currentPage, setCurrentPage] = useState(
    () => pageFromPath(window.location.pathname) || "agent_os",
  );
  const [pageData, setPageData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activePlan, setActivePlan] = useState(null);
  const [trialData, setTrialData] = useState(null);
  const [pendingApprovalCount, setPendingApprovalCount] = useState(0);

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

  // Poll pending Agent OS approvals every 30s so the sidebar badge stays
  // current from any page. Cheap GET - count + lightweight summary only.
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    const refresh = () => {
      fetchOsPendingDeliverables(token)
        .then((res) => {
          if (cancelled) return;
          setPendingApprovalCount(res?.count ?? 0);
        })
        .catch(() => {
          // Silent - badge just stays at last known value
        });
    };
    refresh();
    const id = setInterval(refresh, 30000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [token]);

  // Sync page state with browser back/forward buttons
  useEffect(() => {
    const onPop = () => {
      const page = pageFromPath(window.location.pathname) || "agent_os";
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

  // Marketing plan gate - marketing pages require agent_os in the two-plan
  // model (chatbot / agent_os). Backend enforces via plan_gate dependency;
  // this is the UI half.
  const marketingGated =
    MARKETING_GATED_KEYS.has(currentPage) &&
    !MARKETING_PLANS.has(activePlan || user.plan);

  return (
    <div className="app">
      <Sidebar
        currentPage={currentPage}
        onNavigate={handleNavigate}
        plan={activePlan}
        pendingApprovalCount={pendingApprovalCount}
      />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          flex: 1,
          minWidth: 0,
        }}
      >
        <DemoBanner />
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
          ) : marketingGated ? (
            <MarketingUpsell pageKey={currentPage} onNavigate={handleNavigate} />
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
