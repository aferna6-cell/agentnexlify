import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchTenant, updateTenantSettings, fetchAiFeedback, deleteAiFeedback, startWebsiteCrawl, getCrawlStatus } from "../utils/api";
import SkeletonLoader from "../components/SkeletonLoader";

export default function SettingsPage({ onNavigate }) {
  const { user, token, logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState({
    business_name: "",
    business_type: "",
    city: "",
    owner_name: "",
    notification_phone: "",
    sms_notifications_enabled: false,
    google_review_link: "",
    review_request_config: { enabled: false, delay_hours: 24, method: "email" },
    website_url: "",
  });
  const [email, setEmail] = useState("");
  const [livePlan, setLivePlan] = useState(user?.plan || "free");
  const [feedback, setFeedback] = useState([]);
  const [crawlStatus, setCrawlStatus] = useState(null);
  const [crawling, setCrawling] = useState(false);

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const tenant = await fetchTenant(user.tenantId, token);
      setForm({
        business_name: tenant.business_name || "",
        business_type: tenant.business_type || "",
        city: tenant.city || "",
        owner_name: tenant.owner_name || "",
        notification_phone: tenant.notification_phone || "",
        sms_notifications_enabled: tenant.sms_notifications_enabled || false,
        google_review_link: tenant.google_review_link || "",
        review_request_config: tenant.review_request_config || { enabled: false, delay_hours: 24, method: "email" },
        website_url: tenant.website_url || "",
      });
      setEmail(tenant.owner_email || "");
      if (tenant.plan) setLivePlan(tenant.plan);
    } catch (err) {
      console.error("Failed to load settings", err);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (user?.tenantId && token) {
      fetchAiFeedback(user.tenantId, token)
        .then((data) => setFeedback(data.feedback || []))
        .catch((err) => console.warn("AI feedback fetch failed:", err.message));
    }
  }, [user?.tenantId, token]);

  // Load crawl status
  useEffect(() => {
    if (user?.tenantId && token) {
      getCrawlStatus(user.tenantId, token)
        .then((data) => setCrawlStatus(data))
        .catch((err) => console.warn("Crawl status fetch failed:", err.message));
    }
  }, [user?.tenantId, token]);

  const handleScanWebsite = async () => {
    if (!user?.tenantId || !form.website_url) return;
    setCrawling(true);
    try {
      // Save website_url first if changed
      await updateTenantSettings(user.tenantId, token, { website_url: form.website_url });
      const result = await startWebsiteCrawl(user.tenantId, token);
      setCrawlStatus(result);
    } catch (err) {
      setCrawlStatus({ crawl_status: "failed", error_message: err.message });
    } finally {
      setCrawling(false);
    }
  };

  const handleDeleteFeedback = async (id) => {
    try {
      await deleteAiFeedback(user.tenantId, token, id);
      setFeedback((prev) => prev.filter((f) => f.id !== id));
    } catch (err) {
      console.warn("Delete feedback failed:", err.message);
    }
  };

  const handleChange = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    setSaved(false);
  };

  const handleSave = async () => {
    if (!user?.tenantId) return;
    setSaving(true);
    try {
      await updateTenantSettings(user.tenantId, token, form);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Failed to save settings", err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <SkeletonLoader />;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Settings</h1>
        <p>Manage your account and business information</p>
      </div>

      <div className="settings-page-grid">
        {/* Business Info */}
        <div className="settings-card">
          <h3>Business Information</h3>
          <div className="settings-field">
            <label>Business Name</label>
            <input value={form.business_name} onChange={handleChange("business_name")} placeholder="Your Business" />
          </div>
          <div className="settings-field">
            <label>Business Type</label>
            <input value={form.business_type} onChange={handleChange("business_type")} placeholder="e.g. Real Estate" />
          </div>
          <div className="settings-field">
            <label>City</label>
            <input value={form.city} onChange={handleChange("city")} placeholder="Your city" />
          </div>
          <div className="settings-field">
            <label>Owner Name</label>
            <input value={form.owner_name} onChange={handleChange("owner_name")} placeholder="Your name" />
          </div>
          <button className="btn-primary" onClick={handleSave} disabled={saving} style={{ marginTop: "0.75rem" }}>
            {saving ? "Saving..." : saved ? "Saved!" : "Save Changes"}
          </button>
        </div>

        {/* Website Scanning */}
        <div className="settings-card">
          <h3>Website AI Scanner</h3>
          <p className="settings-card-desc">
            Add your website URL and we'll scan it to automatically train your AI assistant about your business.
          </p>
          <div className="settings-field">
            <label>Website URL</label>
            <input
              value={form.website_url}
              onChange={handleChange("website_url")}
              placeholder="https://yourbusiness.com"
            />
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginTop: "0.75rem" }}>
            <button
              className="btn-primary"
              onClick={handleScanWebsite}
              disabled={crawling || !form.website_url}
            >
              {crawling ? "Scanning..." : "Scan Website"}
            </button>
            <button className="btn-primary" onClick={handleSave} disabled={saving} style={{ background: "transparent", border: "1px solid var(--border-color)", color: "var(--text-primary)" }}>
              {saving ? "Saving..." : saved ? "Saved!" : "Save URL"}
            </button>
          </div>
          {crawlStatus && crawlStatus.crawl_status !== "none" && (
            <div style={{
              marginTop: "0.75rem",
              padding: "10px 14px",
              borderRadius: 8,
              fontSize: "0.85rem",
              background: crawlStatus.crawl_status === "completed" ? "rgba(34,197,94,0.08)" :
                          crawlStatus.crawl_status === "failed" ? "rgba(239,68,68,0.08)" :
                          "rgba(59,130,246,0.08)",
              border: `1px solid ${
                crawlStatus.crawl_status === "completed" ? "rgba(34,197,94,0.2)" :
                crawlStatus.crawl_status === "failed" ? "rgba(239,68,68,0.2)" :
                "rgba(59,130,246,0.2)"
              }`,
            }}>
              {crawlStatus.crawl_status === "completed" && (
                <span>AI knowledge base updated with content from {crawlStatus.pages_found} page{crawlStatus.pages_found !== 1 ? "s" : ""}. Your AI assistant now knows your business!</span>
              )}
              {crawlStatus.crawl_status === "crawling" && (
                <span>Scanning your website... This may take a minute.</span>
              )}
              {crawlStatus.crawl_status === "pending" && (
                <span>Scan queued. Starting shortly...</span>
              )}
              {crawlStatus.crawl_status === "failed" && (
                <span style={{ color: "var(--red, #ef4444)" }}>
                  {crawlStatus.error_message || "Scan failed. Please check the URL and try again."}
                </span>
              )}
              {crawlStatus.crawled_at && (
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
                  Last scanned: {new Date(crawlStatus.crawled_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Account */}
        <div className="settings-card">
          <h3>Account</h3>
          <div className="settings-field">
            <label>Email</label>
            <input value={email} disabled style={{ opacity: 0.6 }} />
            <span className="settings-field-hint">Contact support to change your email</span>
          </div>
          <div className="settings-field">
            <label>Plan</label>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <span className="settings-plan-badge">{livePlan.charAt(0).toUpperCase() + livePlan.slice(1)}</span>
              <button className="btn-secondary btn-sm" onClick={() => onNavigate?.("billing")}>
                Manage Plan
              </button>
            </div>
          </div>
        </div>

        {/* SMS Notifications */}
        <div className="settings-card">
          <h3>SMS Notifications</h3>
          <p className="settings-card-desc">Get texted when new leads come in.</p>
          <div className="settings-field">
            <label>Phone Number</label>
            <input
              value={form.notification_phone}
              onChange={handleChange("notification_phone")}
              placeholder="+1 (555) 123-4567"
            />
          </div>
          <div className="settings-field" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={form.sms_notifications_enabled}
              onChange={(e) => {
                setForm((f) => ({ ...f, sms_notifications_enabled: e.target.checked }));
                setSaved(false);
              }}
              id="sms-toggle"
              style={{ width: "auto" }}
            />
            <label htmlFor="sms-toggle" style={{ margin: 0, cursor: "pointer" }}>
              Enable SMS notifications for new leads
            </label>
          </div>
          <button className="btn-primary" onClick={handleSave} disabled={saving} style={{ marginTop: "0.75rem" }}>
            {saving ? "Saving..." : saved ? "Saved!" : "Save Changes"}
          </button>
        </div>

        {/* Google Review Link */}
        <div className="settings-card">
          <h3>Google Review Link</h3>
          <p className="settings-card-desc">Paste your Google review URL here. Used by the Review Request automation template.</p>
          <div className="settings-field">
            <label>Review URL</label>
            <input
              value={form.google_review_link}
              onChange={handleChange("google_review_link")}
              placeholder="https://g.page/r/your-business/review"
            />
            <span className="settings-field-hint">
              Find this in Google Business Profile under "Ask for reviews"
            </span>
          </div>
          <button className="btn-primary" onClick={handleSave} disabled={saving} style={{ marginTop: "0.75rem" }}>
            {saving ? "Saving..." : saved ? "Saved!" : "Save Changes"}
          </button>
        </div>

        {/* Auto Review Requests */}
        <div className="settings-card">
          <h3>Auto Review Requests</h3>
          <p className="settings-card-desc">
            Automatically ask customers for a review after their appointment is completed.
            {!form.google_review_link && (
              <span style={{ color: "var(--yellow, #facc15)", display: "block", marginTop: 4 }}>
                Set your Google Review Link above first.
              </span>
            )}
          </p>
          <div className="settings-field" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={form.review_request_config.enabled}
              onChange={(e) => {
                setForm((f) => ({
                  ...f,
                  review_request_config: { ...f.review_request_config, enabled: e.target.checked },
                }));
                setSaved(false);
              }}
              id="review-req-toggle"
              style={{ width: "auto" }}
              disabled={!form.google_review_link}
            />
            <label htmlFor="review-req-toggle" style={{ margin: 0, cursor: "pointer" }}>
              Enable automatic review requests
            </label>
          </div>
          {form.review_request_config.enabled && (
            <>
              <div className="settings-field">
                <label>Send After</label>
                <select
                  value={form.review_request_config.delay_hours}
                  onChange={(e) => {
                    setForm((f) => ({
                      ...f,
                      review_request_config: { ...f.review_request_config, delay_hours: parseInt(e.target.value) },
                    }));
                    setSaved(false);
                  }}
                  style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)" }}
                >
                  <option value={0}>Immediately</option>
                  <option value={1}>1 hour</option>
                  <option value={24}>24 hours</option>
                  <option value={48}>48 hours</option>
                </select>
              </div>
              <div className="settings-field">
                <label>Send Via</label>
                <select
                  value={form.review_request_config.method}
                  onChange={(e) => {
                    setForm((f) => ({
                      ...f,
                      review_request_config: { ...f.review_request_config, method: e.target.value },
                    }));
                    setSaved(false);
                  }}
                  style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)" }}
                >
                  <option value="email">Email</option>
                  <option value="sms">SMS</option>
                  <option value="both">Email + SMS</option>
                </select>
              </div>
            </>
          )}
          <button className="btn-primary" onClick={handleSave} disabled={saving} style={{ marginTop: "0.75rem" }}>
            {saving ? "Saving..." : saved ? "Saved!" : "Save Changes"}
          </button>
        </div>

        {/* Quick Links */}
        <div className="settings-card">
          <h3>Quick Links</h3>
          <div className="settings-links">
            <button className="settings-link-btn" onClick={() => onNavigate?.("widget")}>Widget Settings</button>
            <button className="settings-link-btn" onClick={() => onNavigate?.("faq")}>FAQ Manager</button>
            <button className="settings-link-btn" onClick={() => onNavigate?.("availability")}>Calendar Availability</button>
          </div>
        </div>

        {/* AI Feedback */}
        <div className="settings-card">
          <h3>AI Response Feedback</h3>
          <p className="settings-card-desc">
            Visitor ratings on your AI assistant's responses. Corrections from thumbs-down feedback are automatically used to improve future responses.
          </p>
          {feedback.length === 0 ? (
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>No feedback yet. Visitors can rate AI responses with thumbs up/down in the chat widget.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
              {feedback.slice(0, 20).map((fb) => (
                <div key={fb.id} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "flex-start",
                  padding: "8px 12px", borderRadius: 8, fontSize: "0.85rem",
                  background: fb.rating === "thumbs_up" ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)",
                  border: `1px solid ${fb.rating === "thumbs_up" ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)"}`,
                }}>
                  <div>
                    <span style={{ marginRight: 8 }}>{fb.rating === "thumbs_up" ? "\u{1F44D}" : "\u{1F44E}"}</span>
                    {fb.correction ? (
                      <span>{fb.correction}</span>
                    ) : (
                      <span style={{ color: "var(--text-muted)" }}>{fb.rating === "thumbs_up" ? "Positive rating" : "Negative rating (no correction)"}</span>
                    )}
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
                      {new Date(fb.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                    </div>
                  </div>
                  <button onClick={() => handleDeleteFeedback(fb.id)} style={{
                    background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "0.8rem",
                  }}>dismiss</button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Danger Zone */}
        <div className="settings-card danger-zone">
          <h3>Danger Zone</h3>
          <p className="settings-card-desc">Logging out will end your current session.</p>
          <button className="btn-danger" onClick={logout}>Log Out</button>
        </div>
      </div>
    </div>
  );
}
