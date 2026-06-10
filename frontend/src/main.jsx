import React, { useEffect, lazy, Suspense } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate, useParams } from "react-router-dom";
import CookieConsent from "./components/CookieConsent";
import { HelmetProvider } from "react-helmet-async";
import { AuthProvider, useAuth } from "./context/AuthContext";
import App from "./components/App";
import ErrorBoundary from "./components/ErrorBoundary";
import Home from "./pages/Home";
import SignupPage from "./pages/SignupPage";
import "./index.css";

// Lazy-load secondary public pages - not needed on initial landing
const FreeWidget = lazy(() => import("./pages/FreeWidget"));
const DentalChatbot = lazy(() => import("./pages/DentalChatbot"));
const AutoShopChatbot = lazy(() => import("./pages/AutoShopChatbot"));
const SalonChatbot = lazy(() => import("./pages/SalonChatbot"));
const MedicalOfficeChatbot = lazy(() => import("./pages/MedicalOfficeChatbot"));
const RestaurantChatbot = lazy(() => import("./pages/RestaurantChatbot"));
const TermsOfService = lazy(() => import("./pages/TermsOfService"));
const PrivacyPolicy = lazy(() => import("./pages/PrivacyPolicy"));
const HelpPage = lazy(() => import("./pages/HelpPage"));
const Contact = lazy(() => import("./pages/Contact"));
const IntercomAlternative = lazy(() => import("./pages/IntercomAlternative"));
const LiveChatAlternative = lazy(() => import("./pages/LiveChatAlternative"));
const TidioAlternative = lazy(() => import("./pages/TidioAlternative"));
const AcceptInvitePage = lazy(() => import("./pages/AcceptInvitePage"));
const BusinessPage = lazy(() => import("./pages/BusinessPage"));
const ClientPortalPublicPage = lazy(() => import("./pages/ClientPortalPublicPage"));
const ClientLoginPage = lazy(() => import("./pages/ClientLoginPage"));
const ClientDashboardPage = lazy(() => import("./pages/ClientDashboardPage"));
const ForgotPasswordPage = lazy(() => import("./pages/ForgotPasswordPage"));
const ResetPasswordPage = lazy(() => import("./pages/ResetPasswordPage"));
const AuthCallbackPage = lazy(() => import("./pages/AuthCallbackPage"));
// OnboardingWizardPage kept for direct access; /onboarding route uses OnboardingRedirect below
const OnboardingWizardPage = lazy(() => import("./pages/OnboardingWizardPage"));


const CALENDLY_URL = "https://calendly.com/aidanfernandes31/15-minute-agent-nexliffy-demo";

/* Minimal loading spinner for lazy-loaded public pages */
function PageLoader() {
  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
      <div style={{
        width: 36, height: 36, border: "3px solid rgba(255,255,255,0.1)",
        borderTopColor: "#6366f1", borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

/* Renders Home and scrolls to a given anchor after mount */
function HomeSection({ anchor }) {
  useEffect(() => {
    const el = document.getElementById(anchor);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  }, [anchor]);
  return <Home />;
}

/* Maps /industries/:vertical to existing vertical chatbot components */
const VERTICAL_MAP = {
  dental: DentalChatbot,
  "auto-shop": AutoShopChatbot,
  salon: SalonChatbot,
  medical: MedicalOfficeChatbot,
  restaurant: RestaurantChatbot,
};

function IndustryRoute() {
  const { vertical } = useParams();
  const Page = VERTICAL_MAP[vertical];
  if (Page) return <Page />;
  return <Navigate to="/" replace />;
}

/* Maps /compare/:competitor to existing comparison components */
const COMPARE_MAP = {
  intercom: IntercomAlternative,
  livechat: LiveChatAlternative,
  tidio: TidioAlternative,
};

function CompareRoute() {
  const { competitor } = useParams();
  const Page = COMPARE_MAP[competitor];
  if (Page) return <Page />;
  return <Navigate to="/" replace />;
}

/* /onboarding - renders the wizard for authenticated users, redirects to signup otherwise.
   Handles the AuthProvider race condition where user is null on first render
   while the JWT is still being parsed. */
function OnboardingRoute() {
  const { user, token } = useAuth();
  // Token exists but user not yet parsed - still loading
  if (token && user === null) return null;
  // Authenticated → render wizard
  if (user) return <OnboardingWizardPage />;
  // Not authenticated → signup
  return <Navigate to="/signup" replace />;
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <HelmetProvider>
      <ErrorBoundary>
        <BrowserRouter>
          <Suspense fallback={<PageLoader />}>
            <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/free-widget" element={<FreeWidget />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/auth/callback" element={<AuthCallbackPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/terms" element={<TermsOfService />} />
            <Route path="/privacy" element={<PrivacyPolicy />} />
            <Route path="/help" element={<HelpPage />} />
            <Route path="/contact" element={<Contact />} />
            {/* Vertical chatbot pages (canonical URLs) */}
            <Route path="/dental-chatbot" element={<DentalChatbot />} />
            <Route path="/auto-shop-chatbot" element={<AutoShopChatbot />} />
            <Route path="/salon-booking-chatbot" element={<SalonChatbot />} />
            <Route path="/medical-office-chatbot" element={<MedicalOfficeChatbot />} />
            <Route path="/restaurant-chatbot" element={<RestaurantChatbot />} />
            {/* Comparison pages (canonical URLs) */}
            <Route path="/intercom-alternative" element={<IntercomAlternative />} />
            <Route path="/livechat-alternative" element={<LiveChatAlternative />} />
            <Route path="/tidio-alternative" element={<TidioAlternative />} />
            {/* Marketing paths - scroll to Home anchor sections */}
            <Route path="/pricing" element={<HomeSection anchor="pricing" />} />
            <Route path="/features" element={<HomeSection anchor="features" />} />
            <Route path="/about" element={<HomeSection anchor="about-us" />} />
            <Route path="/demo" element={<RedirectExternal url={CALENDLY_URL} />} />
            {/* Alias routes for /industries/:vertical and /compare/:competitor */}
            <Route path="/industries/:vertical" element={<IndustryRoute />} />
            <Route path="/compare/:competitor" element={<CompareRoute />} />
            {/* Team invite accept page (public, no auth) */}
            <Route path="/invite/:token" element={<AcceptInvitePage />} />
            {/* Client portal - login, dashboard, and magic-link portal */}
            <Route path="/client/login/:slug" element={<ClientLoginPage />} />
            <Route path="/client/dashboard/:slug" element={<ClientDashboardPage />} />
            <Route path="/client/:token" element={<ClientPortalPublicPage />} />
            {/* Public business pages - no auth, standalone */}
            <Route path="/biz/:slug" element={<BusinessPage />} />
            {/* /setup - onboarding wizard for new tenants. Routed through
                OnboardingRoute (same as /onboarding): mounting the wizard
                bare lost the AuthProvider race on cold load — user is null
                for a tick while the token parses, and the wizard's own
                redirect bounced logged-in users to /signup. */}
            <Route path="/setup" element={<AuthProvider><OnboardingRoute /></AuthProvider>} />
            {/* /onboarding - onboarding wizard for authenticated users, signup otherwise */}
            <Route path="/onboarding" element={<AuthProvider><OnboardingRoute /></AuthProvider>} />
            {/* Everything else falls to auth-gated dashboard */}
            <Route path="*" element={<AuthProvider><App /></AuthProvider>} />
            </Routes>
            <CookieConsent />
          </Suspense>
        </BrowserRouter>
      </ErrorBoundary>
    </HelmetProvider>
  </React.StrictMode>
);

/* Redirect to external URL (Calendly) */
function RedirectExternal({ url }) {
  useEffect(() => { window.location.href = url; }, [url]);
  return null;
}
