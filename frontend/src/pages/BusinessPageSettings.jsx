import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchBusinessPageSettings, updateBusinessPageSettings } from "../utils/api";
import SkeletonLoader from "../components/SkeletonLoader";

const SITE_URL = "https://agentnexlify.com";

export default function BusinessPageSettings() {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState("");
  const [newService, setNewService] = useState("");
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
  });

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const data = await fetchBusinessPageSettings(user.tenantId, token);
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
      // Only send non-empty slug
      if (!payload.business_slug) delete payload.business_slug;
      const result = await updateBusinessPageSettings(user.tenantId, token, payload);
      // Update slug from server (may have been auto-generated or sanitized)
      if (result.business_slug) {
        setForm((f) => ({ ...f, business_slug: result.business_slug }));
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Failed to save business page settings", err);
      alert(err.message || "Failed to save. Please try again.");
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
        <p>Give your business a professional web presence — no website needed</p>
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
                  <span style={{ color: "#9ca3af", fontSize: "0.85rem", whiteSpace: "nowrap" }}>
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
                <div style={{ marginTop: "0.75rem", padding: "0.75rem", background: "#f0fdf4", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.5rem" }}>
                  <a
                    href={pageUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "#16a34a", fontWeight: 500, fontSize: "0.9rem", wordBreak: "break-all" }}
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
                        background: "#f3f4f6",
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
                          color: "#9ca3af",
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
                        background: "#f9fafb",
                        borderRadius: "8px",
                        gap: "0.5rem",
                      }}
                    >
                      <span style={{ fontSize: "0.85rem", color: "#374151" }}>{label}</span>
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
