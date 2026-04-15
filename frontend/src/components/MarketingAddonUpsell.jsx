import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";

const FEATURES = [
  { icon: "🔍", title: "SEO Audit Hub", desc: "Website audit, GEO visibility, keyword tracking" },
  { icon: "📣", title: "Social Media", desc: "Schedule posts, AI content, calendar view" },
  { icon: "📧", title: "Campaign Blasts", desc: "Email/SMS campaigns with audience targeting" },
  { icon: "📊", title: "Marketing Dashboard", desc: "Performance metrics and growth trends" },
  { icon: "🧪", title: "A/B Testing", desc: "Subject lines, send times, body content" },
  { icon: "⚡", title: "Automation Rules", desc: "14 triggers, 10 actions, execution logs" },
  { icon: "📜", title: "Trigger Logs", desc: "Full history of every rule execution" },
];

export default function MarketingAddonUpsell({ pageKey }) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const apiUrl = import.meta.env.VITE_API_URL || "";

  const handleSubscribe = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await fetch(
        `${apiUrl}/api/v1/billing/marketing-addon/checkout`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        throw new Error("No checkout URL returned");
      }
    } catch (exc) {
      setError(exc.message || "Failed to start checkout");
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", padding: "0 24px" }}>
      <div
        style={{
          background: "var(--bg-secondary)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: "48px 40px",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--accent)", letterSpacing: 1.2 }}>
          MARKETING SUITE ADD-ON
        </div>
        <h1 style={{ fontSize: 36, margin: "12px 0 8px", color: "var(--text-primary)" }}>
          Unlock the full marketing stack
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 16, marginBottom: 24 }}>
          {pageKey
            ? `"${pageKey.replace(/_/g, " ")}" is part of the Marketing Suite add-on.`
            : "Upgrade to unlock 7 marketing features."}
        </p>

        <div
          style={{
            display: "inline-flex",
            alignItems: "baseline",
            gap: 8,
            padding: "16px 32px",
            background: "var(--bg-primary)",
            borderRadius: 8,
            marginBottom: 32,
          }}
        >
          <span style={{ fontSize: 48, fontWeight: 700, color: "var(--text-primary)" }}>
            $49.99
          </span>
          <span style={{ color: "var(--text-secondary)" }}>/month</span>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: 16,
            textAlign: "left",
            marginBottom: 32,
          }}
        >
          {FEATURES.map((f) => (
            <div
              key={f.title}
              style={{
                padding: 16,
                background: "var(--bg-primary)",
                borderRadius: 8,
                border: "1px solid var(--border)",
              }}
            >
              <div style={{ fontSize: 24, marginBottom: 8 }}>{f.icon}</div>
              <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                {f.title}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{f.desc}</div>
            </div>
          ))}
        </div>

        <button
          onClick={handleSubscribe}
          disabled={loading}
          style={{
            padding: "14px 40px",
            fontSize: 16,
            fontWeight: 600,
            background: "var(--accent)",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            cursor: loading ? "wait" : "pointer",
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "Loading Stripe…" : "Subscribe for $49.99/mo →"}
        </button>

        {error && (
          <div style={{ marginTop: 16, color: "var(--red)", fontSize: 14 }}>
            {error}
          </div>
        )}

        <p style={{ marginTop: 24, fontSize: 12, color: "var(--text-secondary)" }}>
          Cancel anytime. Separate from your primary plan subscription.
        </p>
      </div>
    </div>
  );
}

export const MARKETING_ADDON_GATED_KEYS = new Set([
  "local_seo",
  "social_media",
  "campaigns",
  "marketing_dashboard",
  "ab_tests",
  "automation_rules",
  "trigger_logs",
]);
