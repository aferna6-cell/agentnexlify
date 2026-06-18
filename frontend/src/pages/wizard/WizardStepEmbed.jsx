// frontend/src/pages/wizard/WizardStepEmbed.jsx
//
// Final wizard step. The Agent OS is already live - this step is the
// OPTIONAL website widget install. Because most small-business owners can't
// edit their own site, the escape hatch ("email this to my web person") is
// as prominent as the snippet itself.
import { useState, useEffect } from "react";
import { emailEmbedInstructions } from "../../utils/api/onboarding";

const CDN_URL = "https://agentnexlify.com/widget/agentnexlify-widget.js";
const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

const PLATFORM_GUIDES = [
  {
    name: "WordPress",
    steps: "Appearance → Theme File Editor → footer.php, paste before </body>. Or install the \"Insert Headers and Footers\" plugin and paste it there.",
  },
  {
    name: "Wix",
    steps: "Settings → Custom Code → Add Custom Code → paste the snippet, load on All Pages in Body - end.",
  },
  {
    name: "Squarespace",
    steps: "Settings → Advanced → Code Injection → paste into the Footer box.",
  },
  {
    name: "GoDaddy",
    steps: "Edit Site → add an HTML section → paste the snippet.",
  },
];

export default function WizardStepEmbed({ wizardData, token, tenantId }) {
  const [copied, setCopied] = useState(false);
  const [apiKey, setApiKey] = useState(null);
  const [helperEmail, setHelperEmail] = useState("");
  const [sendState, setSendState] = useState("idle"); // idle | sending | sent | error
  const [openGuide, setOpenGuide] = useState(null);

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

  async function handleSendToHelper(e) {
    e.preventDefault();
    if (!helperEmail.trim()) return;
    setSendState("sending");
    try {
      await emailEmbedInstructions(tenantId, token, helperEmail.trim());
      setSendState("sent");
    } catch {
      setSendState("error");
    }
  }

  return (
    <div style={{ textAlign: "center" }}>
      {/* Success banner - the product is live regardless of the widget */}
      <div style={{ background: "rgba(134,239,172,0.1)", border: "1px solid rgba(134,239,172,0.3)", borderRadius: 14, padding: "28px 20px", marginBottom: 24 }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, color: "#86efac", marginBottom: 6 }}>Your AI staff is on the clock</h2>
        <p style={{ color: "rgba(255,255,255,0.5)", fontSize: "0.9rem", margin: 0 }}>
          Ask them to send invoices, chase leads, and book appointments - starting now.
        </p>
      </div>

      {/* Primary CTA: Agent OS */}
      <a href="/dashboard/agent-os" style={{ display: "block", padding: "16px", background: "#6366f1", color: "#fff", borderRadius: 10, fontSize: "1.05rem", fontWeight: 700, textDecoration: "none", marginBottom: 28 }}>
        Meet your AI staff →
      </a>

      {/* Optional widget install */}
      <div style={{ textAlign: "left", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 14, padding: 20, marginBottom: 16 }}>
        <div style={{ fontWeight: 700, marginBottom: 4 }}>
          Optional: add your AI front desk to your website
        </div>
        <p style={{ color: "rgba(255,255,255,0.45)", fontSize: "0.85rem", marginTop: 0, marginBottom: 16 }}>
          One line of code puts the chat widget on your site so it captures leads 24/7.
          We email you the moment it captures a lead. You can also add it later from the dashboard.
        </p>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>Your embed code</span>
          <button onClick={handleCopy} disabled={!apiKey} style={{ ...copyBtnStyle, opacity: apiKey ? 1 : 0.5 }}>
            {copied ? "✓ Copied!" : "Copy Code"}
          </button>
        </div>
        <pre style={{
          background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10,
          padding: 16, fontSize: "0.8rem", color: "#86efac", overflowX: "auto", margin: "0 0 16px", whiteSpace: "pre",
        }}>
          {snippet}
        </pre>

        {/* Escape hatch: most owners don't edit their own site */}
        <div style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.25)", borderRadius: 10, padding: 14, marginBottom: 16 }}>
          <div style={{ fontWeight: 600, fontSize: "0.88rem", marginBottom: 8 }}>
            Someone else manages your website?
          </div>
          {sendState === "sent" ? (
            <p style={{ color: "#86efac", fontSize: "0.85rem", margin: 0 }}>
              Sent! They'll get the code and step-by-step instructions.
            </p>
          ) : (
            <form onSubmit={handleSendToHelper} style={{ display: "flex", gap: 8 }}>
              <input
                type="email"
                value={helperEmail}
                onChange={(e) => setHelperEmail(e.target.value)}
                placeholder="your web person's email"
                required
                style={{ flex: 1, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: "9px 12px", color: "#e2e8f0", fontSize: "0.85rem", minWidth: 0 }}
              />
              <button
                type="submit"
                disabled={sendState === "sending"}
                style={{ ...copyBtnStyle, whiteSpace: "nowrap" }}
              >
                {sendState === "sending" ? "Sending..." : "Email instructions"}
              </button>
            </form>
          )}
          {sendState === "error" && (
            <p style={{ color: "#f87171", fontSize: "0.8rem", margin: "8px 0 0" }}>
              Couldn't send - check the address and try again.
            </p>
          )}
        </div>

        {/* Platform-specific guides */}
        <div style={{ fontWeight: 600, fontSize: "0.88rem", marginBottom: 8 }}>Where do I paste it?</div>
        {PLATFORM_GUIDES.map((g) => (
          <div key={g.name} style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <button
              onClick={() => setOpenGuide(openGuide === g.name ? null : g.name)}
              style={{ width: "100%", textAlign: "left", background: "none", border: "none", color: "rgba(255,255,255,0.75)", padding: "10px 2px", fontSize: "0.85rem", cursor: "pointer", display: "flex", justifyContent: "space-between" }}
            >
              <span>{g.name}</span>
              <span style={{ color: "rgba(255,255,255,0.35)" }}>{openGuide === g.name ? "−" : "+"}</span>
            </button>
            {openGuide === g.name && (
              <p style={{ color: "rgba(255,255,255,0.5)", fontSize: "0.82rem", margin: "0 2px 12px", lineHeight: 1.5 }}>
                {g.steps}
              </p>
            )}
          </div>
        ))}

        {apiKey && (
          <a
            href={`/widget-preview.html?api_key=${encodeURIComponent(apiKey)}`}
            target="_blank"
            rel="noreferrer"
            style={{ display: "block", marginTop: 16, padding: "11px", textAlign: "center", background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.8)", borderRadius: 10, fontSize: "0.88rem", fontWeight: 500, textDecoration: "none" }}
          >
            Test your widget ↗
          </a>
        )}
      </div>

      <p style={{ color: "rgba(255,255,255,0.45)", fontSize: "0.85rem", margin: 0 }}>
        Your 8 AI department heads are ready - ask them anything about running {wizardData.business_name || "your business"}.
      </p>
    </div>
  );
}

const copyBtnStyle = { padding: "8px 14px", background: "rgba(99,102,241,0.2)", color: "#a5b4fc", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 8, fontSize: "0.85rem", cursor: "pointer", fontWeight: 600, minHeight: 36 };
