import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchDashboard, updateWidgetConfig } from "../utils/api";
import SkeletonLoader from "../components/SkeletonLoader";

const POSITIONS = [
  { value: "bottom-right", label: "Bottom Right" },
  { value: "bottom-left", label: "Bottom Left" },
];

const FONT_OPTIONS = [
  "Inter",
  "Roboto",
  "Open Sans",
  "Lato",
  "Montserrat",
  "Poppins",
  "Source Sans Pro",
  "Nunito",
  "Raleway",
  "PT Sans",
];

// Plan hierarchy for feature gating
const PLAN_RANK = { free: 0, growth: 1, professional: 2, enterprise: 3 };

function canAccess(userPlan, requiredPlan) {
  return (PLAN_RANK[userPlan] || 0) >= (PLAN_RANK[requiredPlan] || 0);
}

function UpgradeHint({ plan }) {
  return <span className="branding-upgrade-hint">Requires {plan} plan</span>;
}

export default function WidgetPage() {
  const { user, token } = useAuth();
  const [livePlan, setLivePlan] = useState(user?.plan || "free");
  const plan = livePlan;
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [copied, setCopied] = useState(false);
  const [form, setForm] = useState({
    bot_name: "",
    primary_color: "#00BFFF",
    greeting_message: "",
    position: "bottom-right",
  });
  const [branding, setBranding] = useState({
    logo_url: "",
    secondary_color: "",
    accent_color: "",
    font_family: "",
    widget_title: "",
    powered_by_text: "",
    powered_by_url: "",
    hide_powered_by: false,
    custom_css: "",
  });

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const dash = await fetchDashboard(user.tenantId, token);
      if (dash.plan) setLivePlan(dash.plan);
      setApiKey(dash.widget_api_key || "");
      if (dash.widget_config) {
        setForm({
          bot_name: dash.widget_config.bot_name || "",
          primary_color: dash.widget_config.primary_color || "#00BFFF",
          greeting_message: dash.widget_config.greeting_message || "",
          position: dash.widget_config.position || "bottom-right",
        });
        if (dash.widget_config.branding) {
          const b = dash.widget_config.branding;
          setBranding({
            logo_url: b.logo_url || "",
            secondary_color: b.secondary_color || "",
            accent_color: b.accent_color || "",
            font_family: b.font_family || "",
            widget_title: b.widget_title || "",
            powered_by_text: b.powered_by_text || "",
            powered_by_url: b.powered_by_url || "",
            hide_powered_by: b.hide_powered_by || false,
            custom_css: b.custom_css || "",
          });
        }
      }
    } catch (err) {
      console.error("Failed to load widget config", err);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => { load(); }, [load]);

  const handleChange = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    setSaved(false);
  };

  const handleBrandingChange = (field) => (e) => {
    const val = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setBranding((b) => ({ ...b, [field]: val }));
    setSaved(false);
  };

  const handleSave = async () => {
    if (!user?.tenantId) return;
    setSaving(true);
    try {
      // Build branding payload — only include non-empty values
      const brandingPayload = {};
      Object.entries(branding).forEach(([k, v]) => {
        if (v !== "" && v !== null && v !== undefined) {
          brandingPayload[k] = v;
        }
      });
      const payload = { ...form };
      if (Object.keys(brandingPayload).length > 0) {
        payload.branding = brandingPayload;
      }
      await updateWidgetConfig(user.tenantId, token, payload);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Failed to save widget config", err);
    } finally {
      setSaving(false);
    }
  };

  const apiBase = import.meta.env.VITE_API_BASE_URL || "https://agentnexlify-production.up.railway.app";
  const embedCode = `<script src="https://app.agentnexlify.com/widget/agentnexlify-widget.js" data-api-key="${apiKey}" data-api-base="${apiBase}"></script>`;

  const handleCopy = () => {
    navigator.clipboard.writeText(embedCode).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (loading) return <SkeletonLoader />;

  // Preview colors
  const previewPrimary = branding.secondary_color || form.primary_color;
  const previewFont = branding.font_family || "inherit";

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Widget</h1>
        <p>Customize and install your AI chat widget</p>
      </div>

      <div className="widget-page-grid">
        {/* Embed Code */}
        <div className="settings-card">
          <h3>Embed Code</h3>
          <p className="settings-card-desc">
            Copy this snippet and paste it before the closing &lt;/body&gt; tag on your website.
          </p>
          <div className="embed-code-block">
            <code>{embedCode}</code>
          </div>
          <button className="btn-primary" onClick={handleCopy} style={{ marginTop: "0.75rem" }}>
            {copied ? "Copied!" : "Copy Embed Code"}
          </button>
        </div>

        {/* Customization */}
        <div className="settings-card">
          <h3>Customization</h3>
          <div className="settings-field">
            <label>Bot Name</label>
            <input value={form.bot_name} onChange={handleChange("bot_name")} placeholder="AI Assistant" />
          </div>
          <div className="settings-field">
            <label>Greeting Message</label>
            <textarea
              value={form.greeting_message}
              onChange={handleChange("greeting_message")}
              placeholder="Hi! How can I help you today?"
              rows={2}
            />
          </div>
          <div className="settings-field">
            <label>Primary Color</label>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <input
                type="color"
                value={form.primary_color}
                onChange={handleChange("primary_color")}
                style={{ width: 40, height: 32, border: "none", background: "none", cursor: "pointer" }}
              />
              <input
                value={form.primary_color}
                onChange={handleChange("primary_color")}
                style={{ flex: 1 }}
                placeholder="#00BFFF"
              />
            </div>
          </div>
          <div className="settings-field">
            <label>Position</label>
            <select value={form.position} onChange={handleChange("position")}>
              {POSITIONS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Branding */}
        <div className="settings-card branding-section">
          <h3>Branding</h3>
          <p className="settings-card-desc">White-label your widget with custom branding</p>

          {/* Logo — Growth+ */}
          <div className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}>
            <label>Logo URL {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}</label>
            <input
              value={branding.logo_url}
              onChange={handleBrandingChange("logo_url")}
              placeholder="https://example.com/logo.png"
              disabled={!canAccess(plan, "growth")}
            />
          </div>

          {/* Secondary + Accent colors — Growth+ */}
          <div className="branding-color-group">
            <div className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}>
              <label>Secondary Color {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}</label>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <input
                  type="color"
                  value={branding.secondary_color || "#6b7280"}
                  onChange={handleBrandingChange("secondary_color")}
                  disabled={!canAccess(plan, "growth")}
                  style={{ width: 40, height: 32, border: "none", background: "none", cursor: "pointer" }}
                />
                <input
                  value={branding.secondary_color}
                  onChange={handleBrandingChange("secondary_color")}
                  placeholder="#6b7280"
                  disabled={!canAccess(plan, "growth")}
                  style={{ flex: 1 }}
                />
              </div>
            </div>
            <div className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}>
              <label>Accent Color {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}</label>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <input
                  type="color"
                  value={branding.accent_color || "#00BFFF"}
                  onChange={handleBrandingChange("accent_color")}
                  disabled={!canAccess(plan, "growth")}
                  style={{ width: 40, height: 32, border: "none", background: "none", cursor: "pointer" }}
                />
                <input
                  value={branding.accent_color}
                  onChange={handleBrandingChange("accent_color")}
                  placeholder="#00BFFF"
                  disabled={!canAccess(plan, "growth")}
                  style={{ flex: 1 }}
                />
              </div>
            </div>
          </div>

          {/* Widget title — Growth+ */}
          <div className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}>
            <label>Widget Title {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}</label>
            <input
              value={branding.widget_title}
              onChange={handleBrandingChange("widget_title")}
              placeholder="My Company Chat"
              disabled={!canAccess(plan, "growth")}
            />
          </div>

          {/* Font — Growth+ */}
          <div className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}>
            <label>Font Family {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}</label>
            <select
              value={branding.font_family}
              onChange={handleBrandingChange("font_family")}
              disabled={!canAccess(plan, "growth")}
            >
              <option value="">Default (System)</option>
              {FONT_OPTIONS.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>

          {/* Powered-by text — Growth+ */}
          <div className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}>
            <label>Powered-by Text {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}</label>
            <input
              value={branding.powered_by_text}
              onChange={handleBrandingChange("powered_by_text")}
              placeholder="Powered by AgentNexLiFy"
              disabled={!canAccess(plan, "growth")}
            />
          </div>

          {/* Powered-by URL — Growth+ */}
          <div className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}>
            <label>Powered-by URL {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}</label>
            <input
              value={branding.powered_by_url}
              onChange={handleBrandingChange("powered_by_url")}
              placeholder="https://yourcompany.com"
              disabled={!canAccess(plan, "growth")}
            />
          </div>

          {/* Hide powered-by — Growth+ */}
          <div className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}>
            <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <input
                type="checkbox"
                checked={branding.hide_powered_by}
                onChange={handleBrandingChange("hide_powered_by")}
                disabled={!canAccess(plan, "growth")}
              />
              Hide powered-by badge
              {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}
            </label>
          </div>

          {/* Custom CSS — Professional+ */}
          <div className={`settings-field ${!canAccess(plan, "professional") ? "branding-disabled" : ""}`}>
            <label>Custom CSS {!canAccess(plan, "professional") && <UpgradeHint plan="Professional" />}</label>
            <textarea
              value={branding.custom_css}
              onChange={handleBrandingChange("custom_css")}
              placeholder=".anx-header { border-radius: 0; }"
              rows={4}
              disabled={!canAccess(plan, "professional")}
              style={{ fontFamily: "'SF Mono', 'Fira Code', monospace", fontSize: "12px" }}
            />
          </div>
        </div>

        {/* Save button (full width) */}
        <div className="settings-card" style={{ gridColumn: "1 / -1" }}>
          <button className="btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : saved ? "Saved!" : "Save All Changes"}
          </button>
        </div>

        {/* Live Preview */}
        <div className="settings-card widget-preview-card">
          <h3>Preview</h3>
          <div className="widget-preview" style={{ borderColor: form.primary_color, fontFamily: previewFont }}>
            <div className="widget-preview-header" style={{ background: form.primary_color }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                {branding.logo_url ? (
                  <img
                    src={branding.logo_url}
                    alt="Logo"
                    style={{ width: 28, height: 28, borderRadius: "50%", objectFit: "cover" }}
                    onError={(e) => { e.target.style.display = "none"; }}
                  />
                ) : (
                  <span style={{
                    width: 28, height: 28, borderRadius: "50%", background: "rgba(255,255,255,0.2)",
                    display: "inline-flex", alignItems: "center", justifyContent: "center",
                    fontSize: 14, fontWeight: 700,
                  }}>
                    {(branding.widget_title || form.bot_name || "A").charAt(0).toUpperCase()}
                  </span>
                )}
                <span>{branding.widget_title || form.bot_name || "AI Assistant"}</span>
              </div>
            </div>
            <div className="widget-preview-body">
              <div className="widget-preview-msg ai">
                {form.greeting_message || "Hi! How can I help you today?"}
              </div>
              <div className="widget-preview-msg user" style={{ background: form.primary_color }}>
                I'd like to learn more about your services
              </div>
            </div>
            {!branding.hide_powered_by && (
              <div style={{ textAlign: "center", padding: "4px", fontSize: "10px", color: "var(--text-muted)", borderTop: "1px solid var(--border)" }}>
                {branding.powered_by_text || "Powered by AgentNexLiFy"}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
