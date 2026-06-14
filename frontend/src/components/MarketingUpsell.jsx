/* Plan upsell for marketing features.
 *
 * The $49.99 Marketing Suite add-on was retired 2026-06-10 - these features
 * are included with the Growth plan (autopilot) and above, and the primary
 * way to use them is through your AI marketing staff in Agent OS.
 */
import React from "react";

const FEATURES = [
  { title: "SEO Audit Hub", desc: "Website audit, GEO visibility, keyword tracking" },
  { title: "Social Media", desc: "Schedule posts, AI content, calendar view" },
  { title: "Campaign Blasts", desc: "Email/SMS campaigns with audience targeting" },
  { title: "Marketing Dashboard", desc: "Performance metrics and growth trends" },
  { title: "A/B Testing", desc: "Subject lines, send times, body content" },
  { title: "Automation Rules", desc: "14 triggers, 10 actions, execution logs" },
  { title: "Trigger Logs", desc: "Full history of every rule execution" },
];

// Plans whose tenants see marketing pages instead of this upsell.
export const MARKETING_PLANS = new Set(["autopilot", "professional", "enterprise"]);

export const MARKETING_GATED_KEYS = new Set([
  "marketing_dashboard",
  "local_seo",
  "social_media",
  "campaigns",
  "ab_tests",
  "automation_rules",
  "trigger_logs",
]);

export default function MarketingUpsell({ pageKey, onNavigate }) {
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
          INCLUDED WITH GROWTH
        </div>
        <h1 style={{ fontSize: 36, margin: "12px 0 8px", color: "var(--text-primary)" }}>
          Marketing comes with your AI staff
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 16, marginBottom: 32 }}>
          {pageKey
            ? `"${pageKey.replace(/_/g, " ")}" is included with the Growth plan and above.`
            : "Marketing tools are included with the Growth plan and above."}{" "}
          Upgrade and your marketing team in Agent OS handles SEO, social posts,
          campaigns, and automations for you.
        </p>

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
              <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                {f.title}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{f.desc}</div>
            </div>
          ))}
        </div>

        <button
          onClick={() => onNavigate && onNavigate("billing")}
          style={{
            padding: "14px 40px",
            fontSize: 16,
            fontWeight: 600,
            background: "var(--accent)",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            cursor: "pointer",
          }}
        >
          See plans →
        </button>
      </div>
    </div>
  );
}
