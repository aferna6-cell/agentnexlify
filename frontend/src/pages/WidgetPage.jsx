import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchDashboard } from "../utils/api/dashboard";
import {
  updateWidgetConfig,
  toggleWidgetOnlineStatus,
} from "../utils/api/widget-config";
import { autoGenerateKb } from "../utils/api/onboarding";
import { getWebsiteConnection } from "../utils/api/websiteConnect";
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

export default function WidgetPage({ onNavigate }) {
  const { user, token } = useAuth();
  const [livePlan, setLivePlan] = useState(user?.plan || "free");
  const plan = livePlan;
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [copied, setCopied] = useState(false);
  const [websiteLive, setWebsiteLive] = useState(false);
  const [form, setForm] = useState({
    bot_name: "",
    primary_color: "#00BFFF",
    greeting_message: "",
    teaser_message: "",
    teaser_enabled: true,
    teaser_delay_seconds: 3,
    position: "bottom-right",
    pre_chat_form: null,
    enable_ai_fallback: false,
    enable_structured_lead_parser: false,
  });
  const [isOnline, setIsOnline] = useState(true);
  const [togglingOnline, setTogglingOnline] = useState(false);
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
      try {
        const connect = await getWebsiteConnection(token);
        setWebsiteLive(
          (connect?.connection?.status || connect?.status) === "connected",
        );
      } catch {
        setWebsiteLive(false);
      }
      if (dash.plan) setLivePlan(dash.plan);
      setApiKey(dash.widget_api_key || "");
      if (dash.widget_config) {
        setForm({
          bot_name: dash.widget_config.bot_name || "",
          primary_color: dash.widget_config.primary_color || "#00BFFF",
          greeting_message: dash.widget_config.greeting_message || "",
          teaser_message: dash.widget_config.teaser_message || "",
          teaser_enabled: dash.widget_config.teaser_enabled !== false,
          teaser_delay_seconds: dash.widget_config.teaser_delay_seconds ?? 3,
          position: dash.widget_config.position || "bottom-right",
          pre_chat_form: dash.widget_config.pre_chat_form || null,
          enable_ai_fallback: dash.widget_config.enable_ai_fallback === true,
          enable_structured_lead_parser:
            dash.widget_config.enable_structured_lead_parser === true,
        });
        setIsOnline(dash.widget_config.is_online !== false);
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

  useEffect(() => {
    load();
  }, [load]);

  const handleChange = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    setSaved(false);
  };

  const handleBrandingChange = (field) => (e) => {
    const val =
      e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setBranding((b) => ({ ...b, [field]: val }));
    setSaved(false);
  };

  const handleSave = async () => {
    if (!user?.tenantId) return;
    setSaving(true);
    try {
      // Build branding payload - only include non-empty values
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

  const handleToggleOnline = async () => {
    if (!user?.tenantId) return;
    setTogglingOnline(true);
    try {
      await toggleWidgetOnlineStatus(user.tenantId, token, !isOnline);
      setIsOnline(!isOnline);
    } catch (err) {
      console.error("Failed to toggle online status", err);
    } finally {
      setTogglingOnline(false);
    }
  };

  const apiBase =
    import.meta.env.VITE_API_BASE_URL ||
    "https://agentnexlify-production.up.railway.app";
  const embedCode = `<script async src="https://app.agentnexlify.com/widget/agentnexlify-widget.js" data-api-key="${apiKey}" data-api-base="${apiBase}"></script>`;

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

      <div className="settings-card" data-testid="widget-connect-status">
        <h3>
          {websiteLive ? "AI receptionist is live" : "Website not verified yet"}
        </h3>
        <p className="settings-card-desc">
          {websiteLive
            ? "We found this tenant's widget key on the connected site."
            : "A widget key here is not the same as being live on your site. Connect and verify the public page."}
        </p>
        <button
          className="btn-secondary"
          type="button"
          onClick={() => onNavigate?.("website_connect")}
        >
          {websiteLive ? "Manage website connection" : "Connect your website"}
        </button>
      </div>

      <div className="widget-page-grid">
        {/* Embed Code */}
        <div className="settings-card">
          <h3>Embed Code</h3>
          <p className="settings-card-desc">
            Copy this snippet and paste it before the closing &lt;/body&gt; tag
            on your website.
          </p>
          <div className="embed-code-block">
            <code>{embedCode}</code>
          </div>
          <div
            style={{
              display: "flex",
              gap: "0.5rem",
              marginTop: "0.75rem",
              flexWrap: "wrap",
            }}
          >
            <button className="btn-primary" onClick={handleCopy}>
              {copied ? "Copied!" : "Copy Embed Code"}
            </button>
            <a
              className="btn-secondary"
              href={`mailto:?subject=${encodeURIComponent("Chat widget install instructions")}&body=${encodeURIComponent(`Hi,\n\nPlease add this code snippet before the closing </body> tag on our website:\n\n${embedCode}\n\nThis will add our AI chat widget to the site. No other changes are needed.\n\nThanks!`)}`}
              style={{
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.35rem",
              }}
            >
              Email to Developer
            </a>
          </div>
        </div>

        {/* Online / Offline Toggle */}
        <div className="settings-card">
          <h3>Widget Status</h3>
          <p className="settings-card-desc">
            When offline, visitors see a contact form instead of live chat.
          </p>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              margin: "0.75rem 0",
            }}
          >
            <button
              className={isOnline ? "btn-primary" : "btn-secondary"}
              onClick={handleToggleOnline}
              disabled={togglingOnline}
              style={{ minWidth: 120 }}
            >
              {togglingOnline
                ? "Switching..."
                : isOnline
                  ? "Online"
                  : "Offline"}
            </button>
            <span
              style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}
            >
              {isOnline
                ? "Widget is live - visitors can chat with your AI assistant."
                : "Widget is offline - visitors will see a contact form."}
            </span>
          </div>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "6px 12px",
              borderRadius: "6px",
              fontSize: "0.8rem",
              fontWeight: 500,
              background: isOnline
                ? "var(--green-dim)"
                : "rgba(239, 68, 68, 0.12)",
              color: isOnline ? "var(--green)" : "#ef4444",
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: isOnline ? "var(--green)" : "#ef4444",
              }}
            />
            {isOnline ? "Live Chat Active" : "Offline Mode"}
          </div>
        </div>

        {/* Auto-Setup from Website */}
        <AutoKbSection
          tenantId={user?.tenantId}
          token={token}
          onSuccess={load}
        />

        {/* Customization */}
        <div className="settings-card">
          <h3>Customization</h3>
          <div className="settings-field">
            <label>Bot Name</label>
            <input
              value={form.bot_name}
              onChange={handleChange("bot_name")}
              placeholder="AI Assistant"
            />
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
            <label
              style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
            >
              <input
                type="checkbox"
                checked={form.teaser_enabled}
                onChange={(e) => {
                  setForm((f) => ({ ...f, teaser_enabled: e.target.checked }));
                  setSaved(false);
                }}
                style={{ width: 16, height: 16, cursor: "pointer" }}
              />
              Show teaser bubble
            </label>
          </div>
          {form.teaser_enabled && (
            <>
              <div className="settings-field">
                <label>
                  Teaser Message
                  <span
                    style={{
                      float: "right",
                      fontSize: "0.75rem",
                      color:
                        (form.teaser_message || "").length > 140
                          ? "#f87171"
                          : "#888",
                    }}
                  >
                    {(form.teaser_message || "").length}/150
                  </span>
                </label>
                <textarea
                  value={form.teaser_message}
                  onChange={handleChange("teaser_message")}
                  placeholder="e.g. Have questions? Ask me anything!"
                  rows={2}
                  maxLength={150}
                />
              </div>
              <div className="settings-field">
                <label>Delay before showing (seconds)</label>
                <input
                  type="number"
                  min={0}
                  max={60}
                  value={form.teaser_delay_seconds}
                  onChange={(e) => {
                    setForm((f) => ({
                      ...f,
                      teaser_delay_seconds: Math.min(
                        60,
                        Math.max(0, parseInt(e.target.value) || 0),
                      ),
                    }));
                    setSaved(false);
                  }}
                  style={{ width: 80 }}
                />
              </div>
              {form.teaser_message && (
                <div className="settings-field">
                  <label>Preview</label>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-end",
                      gap: "0.5rem",
                      padding: "0.75rem",
                      background: "rgba(255,255,255,0.05)",
                      borderRadius: 8,
                    }}
                  >
                    <div
                      style={{
                        background: "#fff",
                        color: "#333",
                        borderRadius: "10px 10px 2px 10px",
                        padding: "8px 12px",
                        fontSize: "0.8rem",
                        maxWidth: 220,
                        boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
                      }}
                    >
                      {form.teaser_message}
                    </div>
                    <div
                      style={{
                        width: 44,
                        height: 44,
                        borderRadius: "50%",
                        background: form.primary_color || "#00BFFF",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
                      }}
                    >
                      <svg
                        viewBox="0 0 24 24"
                        width="20"
                        height="20"
                        fill="white"
                      >
                        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z" />
                      </svg>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div className="settings-field">
            <label
              style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
            >
              <input
                type="checkbox"
                checked={form.enable_ai_fallback}
                onChange={(e) => {
                  setForm((f) => ({
                    ...f,
                    enable_ai_fallback: e.target.checked,
                  }));
                  setSaved(false);
                }}
                style={{ width: 16, height: 16, cursor: "pointer" }}
              />
              AI deep fallback
            </label>
            <p
              style={{
                fontSize: "0.75rem",
                color: "#888",
                marginTop: "0.25rem",
                marginBottom: 0,
                lineHeight: 1.4,
              }}
            >
              When the basic chat can&rsquo;t answer a question from your
              knowledge base, a more capable agent with web access takes over.
              Adds 2-5s latency only for those cases. Costs approximately $0.05
              per fallback invocation.
            </p>
          </div>
          <div className="settings-field">
            <label
              style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
            >
              <input
                type="checkbox"
                checked={form.enable_structured_lead_parser}
                onChange={(e) => {
                  setForm((f) => ({
                    ...f,
                    enable_structured_lead_parser: e.target.checked,
                  }));
                  setSaved(false);
                }}
                style={{ width: 16, height: 16, cursor: "pointer" }}
              />
              Smart lead enrichment
            </label>
            <p
              style={{
                fontSize: "0.75rem",
                color: "#888",
                marginTop: "0.25rem",
                marginBottom: 0,
                lineHeight: 1.4,
              }}
            >
              Uses a managed AI agent to fill in name, email, phone, and
              interest fields the basic parser missed. Runs in the background.
              Zero latency impact. Adds ~$0.002 per chat message.
            </p>
          </div>
          <div className="settings-field">
            <label>Primary Color</label>
            <div
              style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}
            >
              <input
                type="color"
                value={form.primary_color}
                onChange={handleChange("primary_color")}
                style={{
                  width: 40,
                  height: 32,
                  border: "none",
                  background: "none",
                  cursor: "pointer",
                }}
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
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Branding */}
        <div className="settings-card branding-section">
          <h3>Branding</h3>
          <p className="settings-card-desc">
            White-label your widget with custom branding
          </p>

          {/* Logo - Growth+ */}
          <div
            className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}
          >
            <label>
              Logo URL{" "}
              {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}
            </label>
            <input
              value={branding.logo_url}
              onChange={handleBrandingChange("logo_url")}
              placeholder="https://example.com/logo.png"
              disabled={!canAccess(plan, "growth")}
            />
          </div>

          {/* Secondary + Accent colors - Growth+ */}
          <div className="branding-color-group">
            <div
              className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}
            >
              <label>
                Secondary Color{" "}
                {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}
              </label>
              <div
                style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}
              >
                <input
                  type="color"
                  value={branding.secondary_color || "#6b7280"}
                  onChange={handleBrandingChange("secondary_color")}
                  disabled={!canAccess(plan, "growth")}
                  style={{
                    width: 40,
                    height: 32,
                    border: "none",
                    background: "none",
                    cursor: "pointer",
                  }}
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
            <div
              className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}
            >
              <label>
                Accent Color{" "}
                {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}
              </label>
              <div
                style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}
              >
                <input
                  type="color"
                  value={branding.accent_color || "#00BFFF"}
                  onChange={handleBrandingChange("accent_color")}
                  disabled={!canAccess(plan, "growth")}
                  style={{
                    width: 40,
                    height: 32,
                    border: "none",
                    background: "none",
                    cursor: "pointer",
                  }}
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

          {/* Widget title - Growth+ */}
          <div
            className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}
          >
            <label>
              Widget Title{" "}
              {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}
            </label>
            <input
              value={branding.widget_title}
              onChange={handleBrandingChange("widget_title")}
              placeholder="My Company Chat"
              disabled={!canAccess(plan, "growth")}
            />
          </div>

          {/* Font - Growth+ */}
          <div
            className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}
          >
            <label>
              Font Family{" "}
              {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}
            </label>
            <select
              value={branding.font_family}
              onChange={handleBrandingChange("font_family")}
              disabled={!canAccess(plan, "growth")}
            >
              <option value="">Default (System)</option>
              {FONT_OPTIONS.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </div>

          {/* Powered-by text - Growth+ */}
          <div
            className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}
          >
            <label>
              Powered-by Text{" "}
              {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}
            </label>
            <input
              value={branding.powered_by_text}
              onChange={handleBrandingChange("powered_by_text")}
              placeholder="Powered by AgentNexLiFy"
              disabled={!canAccess(plan, "growth")}
            />
          </div>

          {/* Powered-by URL - Growth+ */}
          <div
            className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}
          >
            <label>
              Powered-by URL{" "}
              {!canAccess(plan, "growth") && <UpgradeHint plan="Growth" />}
            </label>
            <input
              value={branding.powered_by_url}
              onChange={handleBrandingChange("powered_by_url")}
              placeholder="https://yourcompany.com"
              disabled={!canAccess(plan, "growth")}
            />
          </div>

          {/* Hide powered-by - Growth+ */}
          <div
            className={`settings-field ${!canAccess(plan, "growth") ? "branding-disabled" : ""}`}
          >
            <label
              style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
            >
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

          {/* Custom CSS - Professional+ */}
          <div
            className={`settings-field ${!canAccess(plan, "professional") ? "branding-disabled" : ""}`}
          >
            <label>
              Custom CSS{" "}
              {!canAccess(plan, "professional") && (
                <UpgradeHint plan="Professional" />
              )}
            </label>
            <textarea
              value={branding.custom_css}
              onChange={handleBrandingChange("custom_css")}
              placeholder=".anx-header { border-radius: 0; }"
              rows={4}
              disabled={!canAccess(plan, "professional")}
              style={{
                fontFamily: "'SF Mono', 'Fira Code', monospace",
                fontSize: "12px",
              }}
            />
          </div>
        </div>

        {/* Pre-Chat Form */}
        <div className="settings-card" style={{ gridColumn: "1 / -1" }}>
          <h3>Pre-Chat Form</h3>
          <p className="settings-card-desc">
            Collect visitor information before starting the chat. Fields are
            shown when the widget first opens.
          </p>
          <div
            className="settings-field"
            style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
          >
            <input
              type="checkbox"
              checked={
                Array.isArray(form.pre_chat_form) &&
                form.pre_chat_form.length > 0
              }
              onChange={(e) => {
                setForm((f) => ({
                  ...f,
                  pre_chat_form: e.target.checked
                    ? [
                        {
                          name: "name",
                          label: "Your name",
                          type: "text",
                          required: true,
                        },
                        {
                          name: "email",
                          label: "Email address",
                          type: "email",
                          required: true,
                        },
                      ]
                    : null,
                }));
                setSaved(false);
              }}
              id="prechat-toggle"
              style={{ width: 16, height: 16, cursor: "pointer" }}
            />
            <label
              htmlFor="prechat-toggle"
              style={{ margin: 0, cursor: "pointer" }}
            >
              Enable pre-chat form
            </label>
          </div>
          {Array.isArray(form.pre_chat_form) &&
            form.pre_chat_form.length > 0 && (
              <div style={{ marginTop: "12px" }}>
                {form.pre_chat_form.map((field, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: "flex",
                      gap: "8px",
                      alignItems: "center",
                      marginBottom: "8px",
                      padding: "8px 12px",
                      background: "rgba(255,255,255,0.04)",
                      borderRadius: "8px",
                      border: "1px solid var(--border)",
                    }}
                  >
                    <input
                      value={field.label}
                      onChange={(e) => {
                        const updated = [...form.pre_chat_form];
                        updated[idx] = {
                          ...updated[idx],
                          label: e.target.value,
                        };
                        setForm((f) => ({ ...f, pre_chat_form: updated }));
                        setSaved(false);
                      }}
                      placeholder="Field label"
                      style={{ flex: 1 }}
                    />
                    <select
                      value={field.type}
                      onChange={(e) => {
                        const updated = [...form.pre_chat_form];
                        updated[idx] = {
                          ...updated[idx],
                          type: e.target.value,
                        };
                        setForm((f) => ({ ...f, pre_chat_form: updated }));
                        setSaved(false);
                      }}
                      style={{
                        padding: "6px 8px",
                        borderRadius: 6,
                        border: "1px solid var(--border)",
                        background: "var(--bg-secondary)",
                        color: "var(--text-primary)",
                        width: 100,
                      }}
                    >
                      <option value="text">Text</option>
                      <option value="email">Email</option>
                      <option value="phone">Phone</option>
                      <option value="select">Dropdown</option>
                    </select>
                    <label
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                        fontSize: "0.8rem",
                        color: "var(--text-muted)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={field.required}
                        onChange={(e) => {
                          const updated = [...form.pre_chat_form];
                          updated[idx] = {
                            ...updated[idx],
                            required: e.target.checked,
                          };
                          setForm((f) => ({ ...f, pre_chat_form: updated }));
                          setSaved(false);
                        }}
                        style={{ width: "auto" }}
                      />
                      Required
                    </label>
                    <button
                      onClick={() => {
                        const updated = form.pre_chat_form.filter(
                          (_, i) => i !== idx,
                        );
                        setForm((f) => ({
                          ...f,
                          pre_chat_form: updated.length > 0 ? updated : null,
                        }));
                        setSaved(false);
                      }}
                      style={{
                        background: "rgba(239,68,68,0.15)",
                        color: "#f87171",
                        border: "none",
                        borderRadius: 6,
                        padding: "4px 8px",
                        cursor: "pointer",
                        fontSize: "0.8rem",
                      }}
                    >
                      Remove
                    </button>
                  </div>
                ))}
                <button
                  onClick={() => {
                    setForm((f) => ({
                      ...f,
                      pre_chat_form: [
                        ...(f.pre_chat_form || []),
                        {
                          name: `field_${Date.now()}`,
                          label: "",
                          type: "text",
                          required: false,
                        },
                      ],
                    }));
                    setSaved(false);
                  }}
                  style={{
                    background: "rgba(59,130,246,0.15)",
                    color: "#60a5fa",
                    border: "1px solid rgba(59,130,246,0.3)",
                    borderRadius: 6,
                    padding: "6px 14px",
                    cursor: "pointer",
                    fontSize: "0.8rem",
                    marginTop: "4px",
                  }}
                >
                  + Add Field
                </button>
              </div>
            )}
        </div>

        {/* Save button (full width) */}
        <div className="settings-card" style={{ gridColumn: "1 / -1" }}>
          <button
            className="btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Saving..." : saved ? "Saved!" : "Save All Changes"}
          </button>
        </div>

        {/* QR Code Generator */}
        <div className="settings-card">
          <h3>QR Codes</h3>
          <p className="settings-card-desc">
            Generate QR codes for your chat widget or review page. Print and
            display them in your business.
          </p>
          <QRCodeSection
            tenantId={user?.tenantId}
            token={token}
            apiKey={form.api_key}
          />
        </div>

        {/* Live Preview */}
        <div className="settings-card widget-preview-card">
          <h3>Preview</h3>
          <div
            className="widget-preview"
            style={{ borderColor: form.primary_color, fontFamily: previewFont }}
          >
            <div
              className="widget-preview-header"
              style={{ background: form.primary_color }}
            >
              <div
                style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
              >
                {branding.logo_url ? (
                  <img
                    src={branding.logo_url}
                    alt="Logo"
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: "50%",
                      objectFit: "cover",
                    }}
                    onError={(e) => {
                      e.target.style.display = "none";
                    }}
                  />
                ) : (
                  <span
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: "50%",
                      background: "rgba(255,255,255,0.2)",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 14,
                      fontWeight: 700,
                    }}
                  >
                    {(branding.widget_title || form.bot_name || "A")
                      .charAt(0)
                      .toUpperCase()}
                  </span>
                )}
                <span>
                  {branding.widget_title || form.bot_name || "AI Assistant"}
                </span>
              </div>
            </div>
            <div className="widget-preview-body">
              <div className="widget-preview-msg ai">
                {form.greeting_message || "Hi! How can I help you today?"}
              </div>
              <div
                className="widget-preview-msg user"
                style={{ background: form.primary_color }}
              >
                I'd like to learn more about your services
              </div>
            </div>
            {!branding.hide_powered_by && (
              <div
                style={{
                  textAlign: "center",
                  padding: "4px",
                  fontSize: "10px",
                  color: "var(--text-muted)",
                  borderTop: "1px solid var(--border)",
                }}
              >
                {branding.powered_by_text || "Powered by AgentNexLiFy"}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function AutoKbSection({ tenantId, token, onSuccess }) {
  const [url, setUrl] = useState("");
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    if (!tenantId || !url.trim()) return;
    setGenerating(true);
    setError("");
    setResult(null);
    try {
      const data = await autoGenerateKb(tenantId, token, url.trim());
      setResult(data);
      // Refresh the parent page data so updated KB shows up
      if (onSuccess) onSuccess();
    } catch (err) {
      setError(
        err.message ||
          "Failed to generate knowledge base. Please check the URL and try again.",
      );
    } finally {
      setGenerating(false);
    }
  };

  const isValidUrl =
    url.trim().startsWith("http://") || url.trim().startsWith("https://");

  return (
    <div className="settings-card" style={{ gridColumn: "1 / -1" }}>
      <h3>Auto-Setup from Website</h3>
      <p className="settings-card-desc">
        Paste your website URL and we will crawl it to automatically generate
        your chatbot's knowledge base, FAQs, and custom instructions.
      </p>

      <div
        style={{
          display: "flex",
          gap: "0.75rem",
          alignItems: "flex-start",
          flexWrap: "wrap",
        }}
      >
        <input
          type="url"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            setError("");
            setResult(null);
          }}
          placeholder="https://yourbusiness.com"
          disabled={generating}
          style={{
            flex: 1,
            minWidth: 240,
            padding: "10px 14px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: "var(--bg-secondary)",
            color: "var(--text-primary)",
            fontSize: "0.9rem",
            outline: "none",
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && isValidUrl && !generating)
              handleGenerate();
          }}
        />
        <button
          className="btn-primary"
          onClick={handleGenerate}
          disabled={generating || !isValidUrl}
          style={{ minWidth: 200, padding: "10px 20px", whiteSpace: "nowrap" }}
        >
          {generating ? (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <span
                style={{
                  display: "inline-block",
                  width: 14,
                  height: 14,
                  border: "2px solid rgba(255,255,255,0.3)",
                  borderTopColor: "#fff",
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                }}
              />
              Crawling & generating...
            </span>
          ) : (
            "Generate Knowledge Base"
          )}
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div
          style={{
            marginTop: "1rem",
            padding: "12px 16px",
            borderRadius: 8,
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            color: "#f87171",
            fontSize: "0.85rem",
          }}
        >
          {error}
        </div>
      )}

      {/* Success state */}
      {result && (
        <div
          style={{
            marginTop: "1rem",
            padding: "16px",
            borderRadius: 8,
            background: "rgba(34, 197, 94, 0.08)",
            border: "1px solid rgba(34, 197, 94, 0.25)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              marginBottom: "0.5rem",
            }}
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="#22c55e">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
            </svg>
            <span
              style={{ color: "#22c55e", fontWeight: 600, fontSize: "0.9rem" }}
            >
              Knowledge base generated successfully!
            </span>
          </div>
          <div
            style={{
              display: "flex",
              gap: "1.5rem",
              flexWrap: "wrap",
              fontSize: "0.85rem",
              color: "var(--text-secondary)",
            }}
          >
            <span>
              {result.pages_crawled || 0} page
              {(result.pages_crawled || 0) !== 1 ? "s" : ""} crawled
            </span>
            <span>
              {(result.faqs || []).length} FAQ
              {(result.faqs || []).length !== 1 ? "s" : ""} created
            </span>
            <span>
              {result.chars_extracted
                ? `${Math.round(result.chars_extracted / 1000)}k`
                : "0"}{" "}
              characters extracted
            </span>
          </div>
        </div>
      )}

      {/* Helpful hint when idle */}
      {!generating && !result && !error && (
        <p
          style={{
            marginTop: "0.75rem",
            fontSize: "0.8rem",
            color: "var(--text-muted)",
          }}
        >
          This will crawl your homepage and linked pages to build an AI
          knowledge base. The process typically takes 30-60 seconds.
        </p>
      )}
    </div>
  );
}

function QRCodeSection({ tenantId, token }) {
  const [qrType, setQrType] = useState("widget");
  const [customUrl, setCustomUrl] = useState("");
  const [qrBlobUrl, setQrBlobUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const API_BASE =
    import.meta.env.VITE_API_BASE_URL ||
    "https://agentnexlify-production.up.railway.app";
  const FRONTEND_BASE = window.location.origin;

  const getQrUrl = () => {
    switch (qrType) {
      case "widget":
        return `${FRONTEND_BASE}/biz${tenantId}`;
      case "booking":
        return `${FRONTEND_BASE}/book/${tenantId}`;
      case "custom":
        return customUrl;
      default:
        return "";
    }
  };

  const qrUrl = getQrUrl();

  const generateQR = useCallback(async () => {
    if (!qrUrl || !tenantId || !token) return;
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/widget/${tenantId}/qr?url=${encodeURIComponent(qrUrl)}&size=300`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!res.ok) return;
      const blob = await res.blob();
      if (qrBlobUrl) URL.revokeObjectURL(qrBlobUrl);
      setQrBlobUrl(URL.createObjectURL(blob));
    } catch (err) {
      console.error("QR generation failed", err);
    } finally {
      setLoading(false);
    }
  }, [qrUrl, tenantId, token, API_BASE]);

  // Auto-generate when type or URL changes
  useEffect(() => {
    if (qrUrl) generateQR();
    return () => {
      if (qrBlobUrl) URL.revokeObjectURL(qrBlobUrl);
    };
  }, [qrType, customUrl]);

  const handleDownload = () => {
    if (!qrBlobUrl) return;
    const a = document.createElement("a");
    a.href = qrBlobUrl;
    a.download = `qr-${qrType}-${Date.now()}.png`;
    a.click();
  };

  const qrTypes = [
    { value: "widget", label: "Business Page" },
    { value: "booking", label: "Booking Page" },
    { value: "custom", label: "Custom URL" },
  ];

  return (
    <div>
      <div
        style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}
      >
        {qrTypes.map((t) => (
          <button
            key={t.value}
            onClick={() => setQrType(t.value)}
            style={{
              padding: "6px 14px",
              borderRadius: 6,
              border:
                qrType === t.value
                  ? "1px solid var(--accent)"
                  : "1px solid var(--border)",
              background:
                qrType === t.value
                  ? "rgba(99,102,241,0.15)"
                  : "var(--bg-secondary)",
              color:
                qrType === t.value ? "var(--accent)" : "var(--text-secondary)",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {qrType === "custom" && (
        <input
          type="url"
          value={customUrl}
          onChange={(e) => setCustomUrl(e.target.value)}
          placeholder="https://your-url.com"
          className="settings-input"
          style={{ marginBottom: 16, width: "100%" }}
        />
      )}

      {qrUrl && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 20,
            flexWrap: "wrap",
          }}
        >
          <div
            style={{
              width: 160,
              height: 160,
              background: "#fff",
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              overflow: "hidden",
            }}
          >
            {loading && (
              <span style={{ color: "#666", fontSize: 12 }}>Generating...</span>
            )}
            {qrBlobUrl && !loading && (
              <img
                src={qrBlobUrl}
                alt="QR Code"
                style={{ width: 150, height: 150 }}
              />
            )}
          </div>
          <div>
            <p
              style={{
                fontSize: 13,
                color: "var(--text-secondary)",
                margin: "0 0 8px",
              }}
            >
              Points to:{" "}
              <code style={{ fontSize: 12, color: "var(--accent)" }}>
                {qrUrl}
              </code>
            </p>
            <button
              className="btn-primary"
              onClick={handleDownload}
              disabled={!qrBlobUrl}
              style={{ fontSize: 13, padding: "6px 14px" }}
            >
              Download PNG
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
