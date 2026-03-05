import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchDashboard, updateWidgetConfig } from "../utils/api";
import SkeletonLoader from "../components/SkeletonLoader";

const POSITIONS = [
  { value: "bottom-right", label: "Bottom Right" },
  { value: "bottom-left", label: "Bottom Left" },
];

export default function WidgetPage() {
  const { user, token } = useAuth();
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

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const dash = await fetchDashboard(user.tenantId, token);
      setApiKey(dash.widget_api_key || "");
      if (dash.widget_config) {
        setForm({
          bot_name: dash.widget_config.bot_name || "",
          primary_color: dash.widget_config.primary_color || "#00BFFF",
          greeting_message: dash.widget_config.greeting_message || "",
          position: dash.widget_config.position || "bottom-right",
        });
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

  const handleSave = async () => {
    if (!user?.tenantId) return;
    setSaving(true);
    try {
      await updateWidgetConfig(user.tenantId, token, form);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Failed to save widget config", err);
    } finally {
      setSaving(false);
    }
  };

  const embedCode = `<script src="https://app.agentnexlify.com/widget/agentnexlify-widget.js" data-api-key="${apiKey}"></script>`;

  const handleCopy = () => {
    navigator.clipboard.writeText(embedCode).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (loading) return <SkeletonLoader />;

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
          <button className="btn-primary" onClick={handleSave} disabled={saving} style={{ marginTop: "0.75rem" }}>
            {saving ? "Saving..." : saved ? "Saved!" : "Save Changes"}
          </button>
        </div>

        {/* Live Preview */}
        <div className="settings-card widget-preview-card">
          <h3>Preview</h3>
          <div className="widget-preview" style={{ borderColor: form.primary_color }}>
            <div className="widget-preview-header" style={{ background: form.primary_color }}>
              <span>{form.bot_name || "AI Assistant"}</span>
            </div>
            <div className="widget-preview-body">
              <div className="widget-preview-msg ai">
                {form.greeting_message || "Hi! How can I help you today?"}
              </div>
              <div className="widget-preview-msg user">
                I'd like to learn more about your services
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
