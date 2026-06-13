// frontend/src/pages/wizard/WizardExpressSetup.jsx
//
// The first screen of /setup. Two doors:
//   1. "Set up automatically" - website URL (optional) + industry, one click.
//      Crawls the site into the knowledge base, applies the industry pack and
//      widget defaults server-side, then drops the owner straight into the
//      Agent OS. Under 2 minutes, zero technical steps.
//   2. "Customize step by step" - the full 7-step wizard for people who want it.
// Funnel data (2026-06-11): 0 of 4 tenants ever completed wizard step 1, so
// the express door is the default emphasis.
import { useState } from "react";
import {
  autoGenerateKb,
  completeOnboarding,
  buildWizardPayload,
  trackWizardEvent,
} from "../../utils/api/onboarding";

const INDUSTRIES = [
  { value: "other", label: "General Business / Not Sure Yet" },
  { value: "accounting", label: "Accounting" },
  { value: "auto_shop", label: "Auto Shop" },
  { value: "bakery", label: "Bakery" },
  { value: "bar_nightclub", label: "Bar / Nightclub" },
  { value: "cafe", label: "Café / Coffee Shop" },
  { value: "catering", label: "Catering" },
  { value: "chiropractic", label: "Chiropractic" },
  { value: "cleaning", label: "Cleaning Services" },
  { value: "dental", label: "Dental" },
  { value: "electrical", label: "Electrical" },
  { value: "financial_services", label: "Financial Services / Trading" },
  { value: "fitness", label: "Fitness" },
  { value: "food_truck", label: "Food Truck" },
  { value: "hvac", label: "HVAC" },
  { value: "landscaping", label: "Landscaping" },
  { value: "legal", label: "Legal" },
  { value: "medical", label: "Medical" },
  { value: "moving", label: "Moving" },
  { value: "pest_control", label: "Pest Control" },
  { value: "photography", label: "Photography" },
  { value: "plumbing", label: "Plumbing" },
  { value: "realestate", label: "Real Estate" },
  { value: "restaurant", label: "Restaurant" },
  { value: "roofing", label: "Roofing" },
  { value: "salon", label: "Salon" },
  { value: "tutoring", label: "Tutoring" },
  { value: "veterinary", label: "Veterinary" },
];

export default function WizardExpressSetup({ user, token, onCustomize }) {
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [industry, setIndustry] = useState(user?.businessType || "other");
  const [working, setWorking] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function handleExpress() {
    setError("");
    setWorking(true);
    const tenantId = user?.tenantId;
    const url = websiteUrl.trim();

    try {
      if (url) {
        setStatus("Reading your website so your AI staff knows your business...");
        try {
          await autoGenerateKb(tenantId, token, normalizeUrl(url));
        } catch (e) {
          // Crawl failure is non-fatal - industry pack still applies below.
          console.warn("Express setup: auto-KB failed", e?.message);
        }
      }

      setStatus("Setting up your AI staff...");
      await completeOnboarding(
        tenantId,
        token,
        buildWizardPayload({
          business_name: user?.businessName || "My Business",
          business_type: industry,
          website_url: url ? normalizeUrl(url) : null,
        }),
      );

      trackWizardEvent(tenantId, token, 0, "complete");
      window.location.href = "/dashboard/agent-os";
    } catch (e) {
      setError(e?.message || "Setup failed - try again or customize step by step.");
      setWorking(false);
      setStatus("");
    }
  }

  return (
    <div style={{ textAlign: "center" }}>
      <h2 style={{ fontSize: "1.6rem", fontWeight: 700, marginBottom: 8 }}>
        Meet your AI staff
      </h2>
      <p style={{ color: "rgba(255,255,255,0.55)", marginBottom: 32, fontSize: "0.95rem", lineHeight: 1.5 }}>
        They handle your front desk, leads, invoices, and follow-ups.
        Tell us where your website lives and we'll teach them your business automatically.
      </p>

      <div style={{ textAlign: "left", background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 14, padding: 24, marginBottom: 20 }}>
        <div style={{ fontWeight: 700, marginBottom: 16, fontSize: "1.05rem" }}>
          Set up automatically <span style={{ color: "#a5b4fc", fontWeight: 600, fontSize: "0.8rem" }}>~2 minutes, recommended</span>
        </div>

        <label style={labelStyle}>
          Your website <span style={{ color: "rgba(255,255,255,0.4)", fontWeight: 400 }}>(optional - we'll read it for you)</span>
          <input
            style={inputStyle}
            value={websiteUrl}
            onChange={(e) => setWebsiteUrl(e.target.value)}
            placeholder="yourbusiness.com"
            inputMode="url"
            disabled={working}
          />
        </label>

        <label style={{ ...labelStyle, marginTop: 16 }}>
          What kind of business?
          <select
            style={inputStyle}
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            disabled={working}
          >
            {INDUSTRIES.map((i) => (
              <option key={i.value} value={i.value}>{i.label}</option>
            ))}
          </select>
        </label>

        {status && (
          <p style={{ color: "#a5b4fc", fontSize: "0.85rem", marginTop: 16, marginBottom: 0 }}>{status}</p>
        )}
        {error && (
          <p style={{ color: "#f87171", fontSize: "0.85rem", marginTop: 16, marginBottom: 0 }}>{error}</p>
        )}

        <button
          onClick={handleExpress}
          disabled={working}
          style={{
            width: "100%",
            marginTop: 20,
            padding: "14px",
            background: "#6366f1",
            color: "#fff",
            border: "none",
            borderRadius: 10,
            fontSize: "1rem",
            fontWeight: 600,
            cursor: working ? "wait" : "pointer",
            opacity: working ? 0.7 : 1,
          }}
        >
          {working ? "Setting up..." : "Set up automatically →"}
        </button>
      </div>

      <button
        onClick={onCustomize}
        disabled={working}
        style={{
          width: "100%",
          padding: "13px",
          background: "rgba(255,255,255,0.06)",
          color: "rgba(255,255,255,0.8)",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: 10,
          fontSize: "0.95rem",
          fontWeight: 500,
          cursor: "pointer",
          marginBottom: 16,
        }}
      >
        Customize step by step
      </button>

      <a
        href="/dashboard/agent-os"
        style={{ color: "rgba(255,255,255,0.4)", fontSize: "0.85rem", textDecoration: "none" }}
      >
        Skip for now - go to Agent OS
      </a>
    </div>
  );
}

function normalizeUrl(url) {
  return /^https?:\/\//i.test(url) ? url : `https://${url}`;
}

const labelStyle = { display: "flex", flexDirection: "column", gap: 6, fontSize: "0.9rem", fontWeight: 500 };
const inputStyle = { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: "10px 14px", color: "#e2e8f0", fontSize: "0.9rem", width: "100%", boxSizing: "border-box" };
