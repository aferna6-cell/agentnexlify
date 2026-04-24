import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchBusinessPageSettings, updateBusinessPageSettings } from "../utils/api/business-page";
import SkeletonLoader from "../components/SkeletonLoader";
import { notify } from "../utils/notify";

const SITE_URL = "https://agentnexlify.com";

const PLAN_RANK = { free: 0, growth: 1, professional: 2, enterprise: 3 };
function canAccess(userPlan, requiredPlan) {
  return (PLAN_RANK[userPlan] || 0) >= (PLAN_RANK[requiredPlan] || 0);
}

const COLOR_THEMES = [
  { value: "default", label: "Default (White/Blue)", preview: "#3b82f6" },
  { value: "ocean", label: "Ocean", preview: "#0ea5e9" },
  { value: "forest", label: "Forest", preview: "#16a34a" },
  { value: "sunset", label: "Sunset", preview: "#f97316" },
  { value: "slate", label: "Slate", preview: "#64748b" },
  { value: "rose", label: "Rose", preview: "#f43f5e" },
  { value: "amber", label: "Amber", preview: "#f59e0b" },
  { value: "indigo", label: "Indigo", preview: "#6366f1" },
  { value: "emerald", label: "Emerald", preview: "#10b981" },
  { value: "charcoal", label: "Charcoal", preview: "#374151" },
];

const FONT_OPTIONS = [
  "Inter", "Poppins", "Roboto", "Open Sans", "Lato",
  "Montserrat", "Raleway", "Nunito", "Source Sans 3", "DM Sans",
];

function UpgradeBadge({ requiredPlan }) {
  const label = requiredPlan === "enterprise" ? "Enterprise" : "Professional";
  return (
    <span style={{
      display: "inline-block",
      fontSize: "0.7rem",
      fontWeight: 600,
      padding: "2px 8px",
      borderRadius: "10px",
      background: requiredPlan === "enterprise" ? "rgba(245, 158, 11, 0.15)" : "rgba(139, 92, 246, 0.15)",
      color: requiredPlan === "enterprise" ? "var(--yellow)" : "var(--purple)",
      marginLeft: "0.5rem",
      verticalAlign: "middle",
    }}>
      Upgrade to {label}
    </span>
  );
}

function GatedField({ plan, requiredPlan, children, label }) {
  const locked = !canAccess(plan, requiredPlan);
  return (
    <div className="settings-field" style={{ position: "relative", opacity: locked ? 0.55 : 1 }}>
      <label>
        {label}
        {locked && <UpgradeBadge requiredPlan={requiredPlan} />}
      </label>
      <div style={{ pointerEvents: locked ? "none" : "auto" }}>
        {children}
      </div>
    </div>
  );
}

export default function BusinessPageSettings() {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState("");
  const [newService, setNewService] = useState("");
  const [plan, setPlan] = useState("free");
  const [form, setForm] = useState({
    business_slug: "",
    business_description: "",
    business_phone: "",
    business_address: "",
    business_city: "",
    business_state: "",
    business_hours_display: "",
    business_logo_url: "",
    business_cover_url: "",
    business_page_enabled: false,
    business_services: [],
    bp_color_theme: "default",
    bp_font_family: "",
    bp_hide_powered_by: false,
    bp_custom_css: "",
    bp_meta_title: "",
    bp_meta_description: "",
  });

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const data = await fetchBusinessPageSettings(user.tenantId, token);
      setPlan(data.plan || user?.plan || "free");
      setForm({
        business_slug: data.business_slug || "",
        business_description: data.business_description || "",
        business_phone: data.business_phone || "",
        business_address: data.business_address || "",
        business_city: data.business_city || "",
        business_state: data.business_state || "",
        business_hours_display: data.business_hours_display || "",
        business_logo_url: data.business_logo_url || "",
        business_cover_url: data.business_cover_url || "",
        business_page_enabled: data.business_page_enabled || false,
        business_services: data.business_services || [],
        bp_color_theme: data.bp_color_theme || "default",
        bp_font_family: data.bp_font_family || "",
        bp_hide_powered_by: data.bp_hide_powered_by || false,
        bp_custom_css: data.bp_custom_css || "",
        bp_meta_title: data.bp_meta_title || "",
        bp_meta_description: data.bp_meta_description || "",
      });
    } catch (err) {
      console.error("Failed to load business page settings", err);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => { load(); }, [load]);

  const handleChange = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    setSaved(false);
  };

  const handleToggle = () => {
    setForm((f) => ({ ...f, business_page_enabled: !f.business_page_enabled }));
    setSaved(false);
  };

  const addService = () => {
    const s = newService.trim();
    if (!s) return;
    setForm((f) => ({ ...f, business_services: [...(f.business_services || []), s] }));
    setNewService("");
    setSaved(false);
  };

  const removeService = (idx) => {
    setForm((f) => ({
      ...f,
      business_services: f.business_services.filter((_, i) => i !== idx),
    }));
    setSaved(false);
  };

  const handleSave = async () => {
    if (!user?.tenantId) return;
    setSaving(true);
    try {
      const payload = { ...form };
      if (!payload.business_slug) delete payload.business_slug;
      // Don't send empty tier strings
      if (!payload.bp_font_family) delete payload.bp_font_family;
      if (!payload.bp_custom_css) delete payload.bp_custom_css;
      if (!payload.bp_meta_title) delete payload.bp_meta_title;
      if (!payload.bp_meta_description) delete payload.bp_meta_description;
      const result = await updateBusinessPageSettings(user.tenantId, token, payload);
      if (result.business_slug) {
        setForm((f) => ({ ...f, business_slug: result.business_slug }));
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Failed to save business page settings", err);
      notify.error(err.message || "Failed to save. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const pageUrl = form.business_slug ? `${SITE_URL}/biz/${form.business_slug}` : null;

  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(label);
      setTimeout(() => setCopied(""), 2000);
    });
  };

  if (loading) return <SkeletonLoader />;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Business Page</h1>
        <p>Give your business a professional web presence - no website needed</p>
      </div>

      <div className="settings-page-grid">
        {/* Enable / URL */}
        <div className="settings-card">
          <h3>Your Business Page</h3>
          <div className="settings-field" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={form.business_page_enabled}
              onChange={handleToggle}
              id="bp-enabled"
              style={{ width: "auto" }}
            />
            <label htmlFor="bp-enabled" style={{ margin: 0, cursor: "pointer", fontWeight: 600 }}>
              Enable my business page
            </label>
          </div>

          {form.business_page_enabled && (
            <>
              <div className="settings-field" style={{ marginTop: "1rem" }}>
                <label>Page URL Slug</label>
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", whiteSpace: "nowrap" }}>
                    agentnexlify.com/biz/
                  </span>
                  <input
                    value={form.business_slug}
                    onChange={handleChange("business_slug")}
                    placeholder="your-business-name"
                    style={{ flex: 1 }}
                  />
                </div>
                <span className="settings-field-hint">
                  Leave blank to auto-generate from your business name
                </span>
              </div>

              {pageUrl && (
                <div style={{ marginTop: "0.75rem", padding: "0.75rem", background: "var(--green-dim)", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.5rem" }}>
                  <a
                    href={pageUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "var(--green)", fontWeight: 500, fontSize: "0.9rem", wordBreak: "break-all" }}
                  >
                    {pageUrl}
                  </a>
                  <button
                    className="btn-secondary btn-sm"
                    onClick={() => copyToClipboard(pageUrl, "url")}
                    style={{ whiteSpace: "nowrap" }}
                  >
                    {copied === "url" ? "Copied!" : "Copy Link"}
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Business Info */}
        {form.business_page_enabled && (
          <>
            <div className="settings-card">
              <h3>Page Content</h3>
              <div className="settings-field">
                <label>Business Description</label>
                <textarea
                  value={form.business_description}
                  onChange={handleChange("business_description")}
                  placeholder="Tell customers what you do, what makes you unique (2-3 sentences)"
                  rows={3}
                  style={{ width: "100%", resize: "vertical" }}
                />
              </div>
              <div className="settings-field">
                <label>Phone Number</label>
                <input
                  value={form.business_phone}
                  onChange={handleChange("business_phone")}
                  placeholder="(555) 123-4567"
                />
              </div>
              <div className="settings-field">
                <label>Street Address</label>
                <input
                  value={form.business_address}
                  onChange={handleChange("business_address")}
                  placeholder="123 Main St"
                />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <div className="settings-field">
                  <label>City</label>
                  <input
                    value={form.business_city}
                    onChange={handleChange("business_city")}
                    placeholder="Springfield"
                  />
                </div>
                <div className="settings-field">
                  <label>State</label>
                  <input
                    value={form.business_state}
                    onChange={handleChange("business_state")}
                    placeholder="IL"
                  />
                </div>
              </div>
              <div className="settings-field">
                <label>Business Hours</label>
                <textarea
                  value={form.business_hours_display}
                  onChange={handleChange("business_hours_display")}
                  placeholder={"Mon-Fri  8:00 AM - 6:00 PM\nSat      9:00 AM - 2:00 PM\nSun      Closed"}
                  rows={4}
                  style={{ width: "100%", resize: "vertical", fontFamily: "monospace", fontSize: "0.85rem" }}
                />
              </div>
            </div>

            {/* Images */}
            <div className="settings-card">
              <h3>Images</h3>
              <div className="settings-field">
                <label>Logo URL</label>
                <input
                  value={form.business_logo_url}
                  onChange={handleChange("business_logo_url")}
                  placeholder="https://example.com/logo.png"
                />
                <span className="settings-field-hint">
                  Square image works best. If empty, we'll show your business initial.
                </span>
              </div>
              <div className="settings-field">
                <label>Cover Image URL</label>
                <input
                  value={form.business_cover_url}
                  onChange={handleChange("business_cover_url")}
                  placeholder="https://example.com/storefront.jpg"
                />
                <span className="settings-field-hint">
                  Wide image for the hero section. If empty, we'll use a nice gradient.
                </span>
              </div>
            </div>

            {/* Appearance - Professional+ */}
            <div className="settings-card">
              <h3>Appearance</h3>
              <p className="settings-card-desc">Customize the look of your public business page.</p>

              <GatedField plan={plan} requiredPlan="professional" label="Color Theme">
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: "0.5rem" }}>
                  {COLOR_THEMES.map((t) => (
                    <button
                      key={t.value}
                      onClick={() => { setForm((f) => ({ ...f, bp_color_theme: t.value })); setSaved(false); }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        padding: "0.5rem 0.75rem",
                        border: form.bp_color_theme === t.value ? `2px solid ${t.preview}` : "1px solid var(--border)",
                        borderRadius: "8px",
                        background: form.bp_color_theme === t.value ? `${t.preview}08` : "var(--bg-card)",
                        cursor: "pointer",
                        fontSize: "0.8rem",
                        fontFamily: "inherit",
                      }}
                    >
                      <span style={{
                        width: 16, height: 16, borderRadius: "50%",
                        background: t.preview, flexShrink: 0,
                      }} />
                      {t.label}
                    </button>
                  ))}
                </div>
              </GatedField>

              <GatedField plan={plan} requiredPlan="professional" label="Font Family">
                <select
                  value={form.bp_font_family}
                  onChange={handleChange("bp_font_family")}
                  style={{ width: "100%" }}
                >
                  <option value="">System default</option>
                  {FONT_OPTIONS.map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
                <span className="settings-field-hint">
                  Applies a Google Font to your public page
                </span>
              </GatedField>
            </div>

            {/* SEO - Professional+ */}
            <div className="settings-card">
              <h3>SEO</h3>
              <p className="settings-card-desc">Customize how your page appears in search results.</p>

              <GatedField plan={plan} requiredPlan="professional" label="Meta Title">
                <input
                  value={form.bp_meta_title}
                  onChange={handleChange("bp_meta_title")}
                  placeholder="Custom page title for search engines"
                />
                <span className="settings-field-hint">
                  Overrides the default "{'{business name} - {location}'}" title
                </span>
              </GatedField>

              <GatedField plan={plan} requiredPlan="professional" label="Meta Description">
                <textarea
                  value={form.bp_meta_description}
                  onChange={handleChange("bp_meta_description")}
                  placeholder="Brief description for search engine results (150-160 chars ideal)"
                  rows={2}
                  style={{ width: "100%", resize: "vertical" }}
                />
              </GatedField>
            </div>

            {/* Branding - Professional+ */}
            <div className="settings-card">
              <h3>Branding</h3>

              <GatedField plan={plan} requiredPlan="professional" label="Hide 'Powered by AgentNexLiFy'">
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <input
                    type="checkbox"
                    checked={form.bp_hide_powered_by}
                    onChange={() => { setForm((f) => ({ ...f, bp_hide_powered_by: !f.bp_hide_powered_by })); setSaved(false); }}
                    id="bp-hide-powered"
                    style={{ width: "auto" }}
                    disabled={!canAccess(plan, "professional")}
                  />
                  <label htmlFor="bp-hide-powered" style={{ margin: 0, cursor: "pointer", fontSize: "0.9rem" }}>
                    Remove branding footer from public page
                  </label>
                </div>
              </GatedField>
            </div>

            {/* Custom CSS - Enterprise only */}
            <div className="settings-card">
              <h3>Advanced</h3>

              <GatedField plan={plan} requiredPlan="enterprise" label="Custom CSS">
                <textarea
                  value={form.bp_custom_css}
                  onChange={handleChange("bp_custom_css")}
                  placeholder={`.bp-page { /* your custom styles */ }`}
                  rows={6}
                  style={{ width: "100%", resize: "vertical", fontFamily: "monospace", fontSize: "0.8rem" }}
                  disabled={!canAccess(plan, "enterprise")}
                />
                <span className="settings-field-hint">
                  Add custom CSS to fully control your page styling. Use .bp-* class selectors.
                </span>
              </GatedField>
            </div>

            {/* Services */}
            <div className="settings-card">
              <h3>Services</h3>
              <p className="settings-card-desc">List the services you offer. These appear as cards on your page.</p>
              <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
                <input
                  value={newService}
                  onChange={(e) => setNewService(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addService())}
                  placeholder="Add a service..."
                  style={{ flex: 1 }}
                />
                <button className="btn-secondary btn-sm" onClick={addService}>Add</button>
              </div>
              {form.business_services && form.business_services.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                  {form.business_services.map((svc, i) => (
                    <span
                      key={i}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        background: "var(--bg-secondary)",
                        padding: "0.4rem 0.75rem",
                        borderRadius: "20px",
                        fontSize: "0.85rem",
                      }}
                    >
                      {svc}
                      <button
                        onClick={() => removeService(i)}
                        style={{
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          color: "var(--text-muted)",
                          fontSize: "1rem",
                          padding: 0,
                          lineHeight: 1,
                        }}
                      >
                        x
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Share */}
            {pageUrl && (
              <div className="settings-card">
                <h3>Share Your Page</h3>
                <p className="settings-card-desc">Use your business page URL anywhere you'd put a website link.</p>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {[
                    { label: "Google Business Profile", text: `Add ${pageUrl} as your website URL in Google Business Profile` },
                    { label: "Facebook", text: `Use ${pageUrl} as your website on Facebook` },
                    { label: "Text/SMS", text: `Check out our business: ${pageUrl}` },
                    { label: "Business Cards", text: pageUrl },
                  ].map(({ label, text }) => (
                    <div
                      key={label}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "0.6rem 0.75rem",
                        background: "var(--bg-secondary)",
                        borderRadius: "8px",
                        gap: "0.5rem",
                      }}
                    >
                      <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>{label}</span>
                      <button
                        className="btn-secondary btn-sm"
                        onClick={() => copyToClipboard(text, label)}
                        style={{ whiteSpace: "nowrap" }}
                      >
                        {copied === label ? "Copied!" : "Copy"}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Save button */}
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <button className="btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : saved ? "Saved!" : "Save Changes"}
          </button>
          {pageUrl && form.business_page_enabled && (
            <a
              href={pageUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary"
              style={{ textDecoration: "none", textAlign: "center" }}
            >
              Preview Page
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
