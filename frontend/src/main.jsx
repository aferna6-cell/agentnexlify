import React, { useEffect } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate, useParams } from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";
import { AuthProvider } from "./context/AuthContext";
import App from "./components/App";
import DentalChatbot from "./pages/DentalChatbot";
import AutoShopChatbot from "./pages/AutoShopChatbot";
import SalonChatbot from "./pages/SalonChatbot";
import MedicalOfficeChatbot from "./pages/MedicalOfficeChatbot";
import RestaurantChatbot from "./pages/RestaurantChatbot";
import Home from "./pages/Home";
import FreeWidget from "./pages/FreeWidget";
import SignupPage from "./pages/SignupPage";
import TermsOfService from "./pages/TermsOfService";
import PrivacyPolicy from "./pages/PrivacyPolicy";
import Contact from "./pages/Contact";
import IntercomAlternative from "./pages/IntercomAlternative";
import LiveChatAlternative from "./pages/LiveChatAlternative";
import TidioAlternative from "./pages/TidioAlternative";
import "./index.css";

const CALENDLY_URL = "https://calendly.com/aidanfernandes31/15-minute-agent-nexliffy-demo";

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

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <HelmetProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/free-widget" element={<FreeWidget />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/terms" element={<TermsOfService />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
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
          {/* Marketing paths — scroll to Home anchor sections */}
          <Route path="/pricing" element={<HomeSection anchor="pricing" />} />
          <Route path="/features" element={<HomeSection anchor="features" />} />
          <Route path="/about" element={<HomeSection anchor="about-us" />} />
          <Route path="/demo" element={<RedirectExternal url={CALENDLY_URL} />} />
          {/* Alias routes for /industries/:vertical and /compare/:competitor */}
          <Route path="/industries/:vertical" element={<IndustryRoute />} />
          <Route path="/compare/:competitor" element={<CompareRoute />} />
          {/* Everything else falls to auth-gated dashboard */}
          <Route path="*" element={<AuthProvider><App /></AuthProvider>} />
        </Routes>
      </BrowserRouter>
    </HelmetProvider>
  </React.StrictMode>
);

/* Redirect to external URL (Calendly) */
function RedirectExternal({ url }) {
  useEffect(() => { window.location.href = url; }, [url]);
  return null;
}
