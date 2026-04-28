// frontend/src/pages/wizard/WizardStepEmbed.jsx
import { useState, useEffect } from "react";

const CDN_URL = "https://agentnexlify.com/widget/agentnexlify-widget.js";
const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export default function WizardStepEmbed({ wizardData, token, tenantId }) {
  const [copied, setCopied] = useState(false);
  const [apiKey, setApiKey] = useState(null);

  useEffect(() => {
    if (!token || !tenantId) return;
    fetch(`${API_BASE}/api/v1/auth/dashboard/${tenantId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.widget_api_key) {
          setApiKey(data.widget_api_key);
        }
      })
      .catch((e) => { console.warn('Widget key fetch failed:', e?.message); });
  }, [token, tenantId]);

  const snippet = apiKey
    ? `<script src="${CDN_URL}"\n        data-api-key="${apiKey}"\n        async>\n</script>`
    : "<!-- Loading your embed code… -->";

  function handleCopy() {
    if (!apiKey) return;
    navigator.clipboard.writeText(snippet).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
  }

  return (
    <div style={{ textAlign: "center" }}>
      {/* Success banner */}
      <div style={{ background: "rgba(134,239,172,0.1)", border: "1px solid rgba(134,239,172,0.3)", borderRadius: 14, padding: "28px 20px", marginBottom: 32 }}>
        <div style={{ fontSize: "2.5rem", marginBottom: 8 }}>🎉</div>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, color: "#86efac", marginBottom: 6 }}>Your AI assistant is live!</h2>
        <p style={{ color: "rgba(255,255,255,0.5)", fontSize: "0.9rem", margin: 0 }}>
          Paste this code on your website to activate the chat widget.
        </p>
      </div>

      {/* Embed snippet */}
      <div style={{ textAlign: "left", marginBottom: 32 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <span style={{ fontWeight: 600 }}>Your embed code</span>
          <button onClick={handleCopy} disabled={!apiKey} style={{ ...copyBtnStyle, opacity: apiKey ? 1 : 0.5 }}>
            {copied ? "✓ Copied!" : "Copy Code"}
          </button>
        </div>
        <pre style={{
          background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10,
          padding: 20, fontSize: "0.85rem", color: "#86efac", overflowX: "auto", margin: 0, whiteSpace: "pre",
        }}>
          {snippet}
        </pre>
      </div>

      {/* Installation steps */}
      <div style={{ textAlign: "left", background: "rgba(255,255,255,0.04)", borderRadius: 12, padding: 20, marginBottom: 32 }}>
        <div style={{ fontWeight: 600, marginBottom: 14 }}>How to install</div>
        {[
          "Open your website's HTML file or CMS template",
          "Paste the code above just before the closing </body> tag",
          "Save and refresh your page - the chat widget will appear",
        ].map((step, i) => (
          <div key={i} style={{ display: "flex", gap: 14, marginBottom: i < 2 ? 12 : 0, alignItems: "flex-start" }}>
            <div style={{ width: 24, height: 24, borderRadius: "50%", background: "#6366f1", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.75rem", fontWeight: 700, flexShrink: 0 }}>{i + 1}</div>
            <span style={{ color: "rgba(255,255,255,0.7)", fontSize: "0.9rem", paddingTop: 3 }}>{step}</span>
          </div>
        ))}
      </div>

      {/* CTA buttons */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <a href="/dashboard" style={{ display: "block", padding: "14px", background: "#6366f1", color: "#fff", borderRadius: 10, fontSize: "1rem", fontWeight: 600, textDecoration: "none" }}>
          Go to Dashboard →
        </a>
        {apiKey && (
          <a
            href={`/widget-preview.html?api_key=${encodeURIComponent(apiKey)}`}
            target="_blank"
            rel="noreferrer"
            style={{ display: "block", padding: "12px", background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.8)", borderRadius: 10, fontSize: "0.9rem", fontWeight: 500, textDecoration: "none" }}
          >
            Test your widget ↗
          </a>
        )}
      </div>
    </div>
  );
}

const copyBtnStyle = { padding: "8px 14px", background: "rgba(99,102,241,0.2)", color: "#a5b4fc", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 8, fontSize: "0.85rem", cursor: "pointer", fontWeight: 600, minHeight: 36 };
