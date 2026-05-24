import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import UpgradePrompt, { planBelowRequired } from "../components/UpgradePrompt";
import { fetchDashboard } from "../utils/api/dashboard";
import { TABS } from "./LocalSEO/constants";
import SeoAuditTab from "./LocalSEO/SeoAuditTab";
import GeoScoreTab from "./LocalSEO/GeoScoreTab";
import KeywordsTab from "./LocalSEO/KeywordsTab";
import ProfileTab from "./LocalSEO/ProfileTab";
import CompetitorTab from "./LocalSEO/CompetitorTab";

export default function LocalSEOPage({ onNavigate }) {
  const { user, token } = useAuth();
  const [activeTab, setActiveTab] = useState("audit");
  const [showUpgradePrompt, setShowUpgradePrompt] = useState(false);
  const [livePlan, setLivePlan] = useState(null);

  useEffect(() => {
    if (!user?.tenantId || !token) return;
    fetchDashboard(user.tenantId, token)
      .then((data) => {
        if (data?.plan) setLivePlan(data.plan);
      })
      .catch((err) =>
        console.warn("LocalSEO: failed to fetch plan:", err.message),
      );
  }, [user?.tenantId, token]);

  const effectivePlan = livePlan ?? user?.plan;

  if (!user?.tenantId) {
    return (
      <div className="fade-in">
        <div className="page-header">
          <h1>SEO & Marketing Hub</h1>
        </div>
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            color: "var(--text-muted)",
          }}
        >
          <p>Please log in to access SEO tools.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      {showUpgradePrompt && (
        <UpgradePrompt
          feature="Local SEO & Marketing Hub"
          requiredPlan="professional"
          onClose={() => setShowUpgradePrompt(false)}
          onNavigate={onNavigate}
        />
      )}

      <div className="page-header">
        <div>
          <h1>SEO & Marketing Hub</h1>
          <p>
            Audit your site, track AI visibility, and optimize for search
            engines
          </p>
        </div>
      </div>

      {planBelowRequired(effectivePlan, "professional") && (
        <UpgradePrompt
          feature="Local SEO & Marketing Hub"
          requiredPlan="professional"
          onClose={() => {}}
          onNavigate={onNavigate}
          variant="banner"
        />
      )}

      <div className="wh-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className={`wh-tab${activeTab === tab.key ? " wh-tab-active" : ""}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "audit" && (
        <SeoAuditTab tenantId={user.tenantId} token={token} />
      )}
      {activeTab === "geo" && (
        <GeoScoreTab tenantId={user.tenantId} token={token} />
      )}
      {activeTab === "keywords" && (
        <KeywordsTab tenantId={user.tenantId} token={token} />
      )}
      {activeTab === "competitors" && (
        <CompetitorTab tenantId={user.tenantId} token={token} />
      )}
      {activeTab === "profile" && (
        <ProfileTab tenantId={user.tenantId} token={token} />
      )}
    </div>
  );
}
