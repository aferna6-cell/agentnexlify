import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchTenant, updateTenantSettings, fetchKnowledgeStats } from "../utils/api/dashboard";
import { fetchAiFeedback, deleteAiFeedback, startWebsiteCrawl, getCrawlStatus } from "../utils/api/widget-config";
import { fetchTagDefinitions, createTagDefinition, updateTagDefinition, deleteTagDefinition } from "../utils/api/tags";
import { searchAvailableNumbers, provisionPhoneNumber, releasePhoneNumber } from "../utils/api/phone";
import { fetchFieldDefinitions, createFieldDefinition, deleteFieldDefinition } from "../utils/api/misc";
import { toggleClientLogin } from "../utils/api/portal";
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
    textback_enabled: false,
    textback_message: "Hi! Sorry we missed your call at {business_name}. How can we help? Reply here and we'll get back to you right away.",
    textback_quiet_start: "22:00",
    textback_quiet_end: "08:00",
  });
  const [email, setEmail] = useState("");
  const [livePlan, setLivePlan] = useState(user?.plan || "free");
  const [feedback, setFeedback] = useState([]);
  const [knowledgeStats, setKnowledgeStats] = useState(null);
  const [crawlStatus, setCrawlStatus] = useState(null);
  const [crawling, setCrawling] = useState(false);
  const [businessSlug, setBusinessSlug] = useState(null);
  const [businessPageEnabled, setBusinessPageEnabled] = useState(false);
  const [clientLoginEnabled, setClientLoginEnabled] = useState(false);
  const [togglingClientLogin, setTogglingClientLogin] = useState(false);
  const [tagDefs, setTagDefs] = useState([]);
  const [newTagName, setNewTagName] = useState("");
  const [newTagColor, setNewTagColor] = useState("#6b7280");
  const [savingTag, setSavingTag] = useState(false);

  // Custom Fields state
  const [customFieldDefs, setCustomFieldDefs] = useState([]);
  const [cfLoadError, setCfLoadError] = useState(null);
  const [newFieldName, setNewFieldName] = useState("");
  const [newFieldType, setNewFieldType] = useState("text");
  const [newFieldOptions, setNewFieldOptions] = useState("");
  const [newFieldRequired, setNewFieldRequired] = useState(false);
  const [savingField, setSavingField] = useState(false);
  const [deletingFieldId, setDeletingFieldId] = useState(null);

  // Phone provisioning state
  const [provisionedPhone, setProvisionedPhone] = useState(null);
  const [phoneAreaCode, setPhoneAreaCode] = useState("");
  const [availableNumbers, setAvailableNumbers] = useState([]);
  const [searchingNumbers, setSearchingNumbers] = useState(false);
  const [provisioningPhone, setProvisioningPhone] = useState(false);
  const [releasingPhone, setReleasingPhone] = useState(false);
  const [phoneError, setPhoneError] = useState(null);
  const [phoneSuccess, setPhoneSuccess] = useState(null);

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
        textback_enabled: tenant.textback_enabled || false,
        textback_message: tenant.textback_message || "Hi! Sorry we missed your call at {business_name}. How can we help? Reply here and we'll get back to you right away.",
        textback_quiet_start: tenant.textback_quiet_start || "22:00",
        textback_quiet_end: tenant.textback_quiet_end || "08:00",
      });
      setEmail(tenant.owner_email || "");
      setBusinessSlug(tenant.business_slug || null);
      setBusinessPageEnabled(!!tenant.business_page_enabled);
      setClientLoginEnabled(!!tenant.client_login_enabled);
      if (tenant.plan) setLivePlan(tenant.plan);
      // phone_number is stored in notification_phone; only track it as "provisioned"
      // if it was set via Twilio (starts with + international format)
      const maybeProvisioned = tenant.notification_phone || "";
      setProvisionedPhone(maybeProvisioned.startsWith("+") ? maybeProvisioned : null);
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
      fetchKnowledgeStats(user.tenantId, token)
        .then((data) => setKnowledgeStats(data))
        .catch((err) => console.warn("Knowledge stats fetch failed:", err.message));
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

  // Load tag definitions
  useEffect(() => {
    if (user?.tenantId && token) {
      fetchTagDefinitions(user.tenantId, token)
        .then((data) => setTagDefs(data.tags || []))
        .catch((err) => console.warn("Tag definitions fetch failed:", err.message));
    }
  }, [user?.tenantId, token]);

  // Load custom field definitions
  useEffect(() => {
    if (user?.tenantId && token) {
      setCfLoadError(null);
      fetchFieldDefinitions(user.tenantId, token)
        .then((data) => setCustomFieldDefs(Array.isArray(data) ? data : (data.fields || [])))
        .catch((err) => {
          console.warn("Custom field definitions fetch failed:", err.message);
          setCfLoadError("Could not load custom fields.");
        });
    }
  }, [user?.tenantId, token]);

  const handleAddCustomField = async () => {
    if (!newFieldName.trim()) return;
    setSavingField(true);
    try {
      const options = newFieldType === "dropdown"
        ? newFieldOptions.split(",").map((s) => s.trim()).filter(Boolean)
        : [];
      const created = await createFieldDefinition(user.tenantId, token, {
        name: newFieldName.trim(),
        field_type: newFieldType,
        options,
        is_required: newFieldRequired,
      });
      setCustomFieldDefs((prev) => [...prev, created]);
      setNewFieldName("");
      setNewFieldType("text");
      setNewFieldOptions("");
      setNewFieldRequired(false);
    } catch (err) {
      console.warn("Create custom field failed:", err.message);
      alert(err.message || "Failed to create field");
    } finally {
      setSavingField(false);
    }
  };

  const handleDeleteCustomField = async (fieldId) => {
    setDeletingFieldId(fieldId);
    try {
      await deleteFieldDefinition(user.tenantId, token, fieldId);
      setCustomFieldDefs((prev) => prev.filter((f) => f.id !== fieldId));
    } catch (err) {
      console.warn("Delete custom field failed:", err.message);
      alert(err.message || "Failed to delete field");
    } finally {
      setDeletingFieldId(null);
    }
  };

  const handleScanWebsite = async () => {
    if (!user?.tenantId) return;
    // Need either a website URL or an active business page
    if (!form.website_url && !(businessSlug && businessPageEnabled)) return;
    setCrawling(true);
    try {
      // Save website_url first if provided
      if (form.website_url) {
        await updateTenantSettings(user.tenantId, token, { website_url: form.website_url });
      }
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

  const handleAddTag = async () => {
    if (!newTagName.trim()) return;
    setSavingTag(true);
    try {
      const tag = await createTagDefinition(user.tenantId, token, {
        tag_name: newTagName.trim(),
        tag_color: newTagColor,
      });
      setTagDefs((prev) => [...prev, tag]);
      setNewTagName("");
      setNewTagColor("#6b7280");
    } catch (err) {
      console.warn("Create tag failed:", err.message);
    } finally {
      setSavingTag(false);
    }
  };

  const handleToggleTag = async (tag) => {
    try {
      await updateTagDefinition(user.tenantId, token, tag.id, {
        is_enabled: !tag.is_enabled,
      });
      setTagDefs((prev) =>
        prev.map((t) => (t.id === tag.id ? { ...t, is_enabled: !t.is_enabled } : t))
      );
    } catch (err) {
      console.warn("Toggle tag failed:", err.message);
    }
  };

  const handleDeleteTag = async (tagId) => {
    try {
      await deleteTagDefinition(user.tenantId, token, tagId);
      setTagDefs((prev) => prev.filter((t) => t.id !== tagId));
    } catch (err) {
      console.warn("Delete tag failed:", err.message);
    }
  };

  const handleSearchNumbers = async () => {
    if (!phoneAreaCode.trim()) return;
    setPhoneError(null);
    setPhoneSuccess(null);
    setAvailableNumbers([]);
    setSearchingNumbers(true);
    try {
      const res = await searchAvailableNumbers(user.tenantId, token, phoneAreaCode.trim());
      setAvailableNumbers(res.numbers || []);
      if (!res.numbers || res.numbers.length === 0) {
        setPhoneError("No available numbers found for that area code. Try a different code.");
      }
    } catch (err) {
      setPhoneError(err.message || "Failed to search for numbers.");
    } finally {
      setSearchingNumbers(false);
    }
  };

  const handleProvision = async () => {
    if (!phoneAreaCode.trim()) return;
    setPhoneError(null);
    setPhoneSuccess(null);
    setProvisioningPhone(true);
    try {
      const res = await provisionPhoneNumber(user.tenantId, token, phoneAreaCode.trim());
      setProvisionedPhone(res.phone_number);
      setAvailableNumbers([]);
      setPhoneAreaCode("");
      setPhoneSuccess(`Number ${res.phone_number} provisioned successfully.`);
      // Update local form so the notification_phone field reflects new number
      setForm((f) => ({ ...f, notification_phone: res.phone_number }));
    } catch (err) {
      setPhoneError(err.message || "Failed to provision number. Please try again.");
    } finally {
      setProvisioningPhone(false);
    }
  };

  const handleReleasePhone = async () => {
    if (!window.confirm("Are you sure you want to release this phone number? This cannot be undone.")) return;
    setPhoneError(null);
    setPhoneSuccess(null);
    setReleasingPhone(true);
    try {
      await releasePhoneNumber(user.tenantId, token);
      setProvisionedPhone(null);
      setAvailableNumbers([]);
      setPhoneSuccess("Phone number released.");
      setForm((f) => ({ ...f, notification_phone: "" }));
    } catch (err) {
      setPhoneError(err.message || "Failed to release number. Please try again.");
    } finally {
      setReleasingPhone(false);
    }
  };

  const handleChange = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    setSaved(false);
  };

  const handleToggleClientLogin = async () => {
    if (!user?.tenantId || togglingClientLogin) return;
    setTogglingClientLogin(true);
    try {
      const data = await toggleClientLogin(user.tenantId, token);
      setClientLoginEnabled(data.client_login_enabled);
    } catch (err) {
      console.error("Failed to toggle client login", err);
    } finally {
      setTogglingClientLogin(false);
    }
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
            <select
              value={form.business_type}
              onChange={handleChange("business_type")}
              style={{ padding: "8px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg-secondary)", color: "var(--text-primary)" }}
            >
              <option value="">Select type...</option>
              <option value="restaurant">Restaurant / Food Service</option>
              <option value="home_services">Home Services (Plumbing, HVAC, etc.)</option>
              <option value="real_estate">Real Estate</option>
              <option value="health_wellness">Health & Wellness</option>
              <option value="legal">Legal Services</option>
              <option value="retail">Retail / E-commerce</option>
              <option value="automotive">Automotive</option>
              <option value="beauty">Beauty / Salon / Spa</option>
              <option value="fitness">Fitness / Gym</option>
              <option value="construction">Construction / Contractor</option>
              <option value="cleaning">Cleaning Services</option>
              <option value="landscaping">Landscaping / Lawn Care</option>
              <option value="professional">Professional Services</option>
              <option value="other">Other</option>
            </select>
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
              disabled={crawling || (!form.website_url && !(businessSlug && businessPageEnabled))}
            >
              {crawling ? "Scanning..." : form.website_url ? "Scan Website" : "Scan Business Page"}
            </button>
            <button className="btn-primary" onClick={handleSave} disabled={saving} style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--text-primary)" }}>
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
          {/* Fallback: no website URL and no successful crawl */}
          {!form.website_url && (!crawlStatus || crawlStatus.crawl_status === "none" || crawlStatus.crawl_status === "failed") && (
            <div style={{
              marginTop: "0.75rem",
              padding: "10px 14px",
              borderRadius: 8,
              fontSize: "0.85rem",
              background: "rgba(250,204,21,0.08)",
              border: "1px solid rgba(250,204,21,0.2)",
            }}>
              <strong>No website?</strong> You can still train your AI assistant:
              <ul style={{ margin: "6px 0 0", paddingLeft: 18, lineHeight: 1.6 }}>
                <li>
                  <button className="settings-link-btn" onClick={() => onNavigate?.("faq")} style={{ fontSize: "0.85rem", padding: 0, textDecoration: "underline" }}>
                    Add FAQs manually
                  </button> - teach your AI about your services, pricing, and policies.
                </li>
                <li>
                  <button className="settings-link-btn" onClick={() => onNavigate?.("business-page")} style={{ fontSize: "0.85rem", padding: 0, textDecoration: "underline" }}>
                    Set up your Business Page
                  </button> - we'll auto-scan it to train your AI.
                </li>
              </ul>
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
                  style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg-secondary)", color: "var(--text-primary)" }}
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
                  style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg-secondary)", color: "var(--text-primary)" }}
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

        {/* Missed Call Text-Back */}
        <div className="settings-card">
          <h3>Missed Call Text-Back</h3>
          <p className="settings-card-desc">
            Automatically send a text message when you miss a phone call, so potential customers get an instant response.
          </p>
          <div className="settings-field" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={form.textback_enabled}
              onChange={(e) => {
                setForm((f) => ({ ...f, textback_enabled: e.target.checked }));
                setSaved(false);
              }}
              id="textback-toggle"
              style={{ width: "auto" }}
            />
            <label htmlFor="textback-toggle" style={{ margin: 0, cursor: "pointer" }}>
              Enable missed call text-back
            </label>
          </div>
          {form.textback_enabled && (
            <>
              <div className="settings-field">
                <label>Greeting Message</label>
                <textarea
                  value={form.textback_message}
                  onChange={(e) => {
                    setForm((f) => ({ ...f, textback_message: e.target.value }));
                    setSaved(false);
                  }}
                  rows={3}
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    borderRadius: 6,
                    border: "1px solid var(--border)",
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    resize: "vertical",
                    fontFamily: "inherit",
                    fontSize: "0.9rem",
                  }}
                  placeholder="Hi! Sorry we missed your call..."
                />
                <span className="settings-field-hint">
                  Use {"{business_name}"} to insert your business name automatically
                </span>
              </div>
              <div className="settings-field">
                <label>Quiet Hours</label>
                <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "0 0 8px" }}>
                  Don't send text-backs during these hours (e.g., late night). Missed calls during quiet hours will be texted when quiet hours end.
                </p>
                <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Start</span>
                    <input
                      type="time"
                      value={form.textback_quiet_start}
                      onChange={(e) => {
                        setForm((f) => ({ ...f, textback_quiet_start: e.target.value }));
                        setSaved(false);
                      }}
                      style={{
                        padding: "6px 10px",
                        borderRadius: 6,
                        border: "1px solid var(--border)",
                        background: "var(--bg-secondary)",
                        color: "var(--text-primary)",
                        fontSize: "0.9rem",
                      }}
                    />
                  </div>
                  <span style={{ color: "var(--text-muted)", marginTop: 18 }}>to</span>
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>End</span>
                    <input
                      type="time"
                      value={form.textback_quiet_end}
                      onChange={(e) => {
                        setForm((f) => ({ ...f, textback_quiet_end: e.target.value }));
                        setSaved(false);
                      }}
                      style={{
                        padding: "6px 10px",
                        borderRadius: 6,
                        border: "1px solid var(--border)",
                        background: "var(--bg-secondary)",
                        color: "var(--text-primary)",
                        fontSize: "0.9rem",
                      }}
                    />
                  </div>
                </div>
              </div>
            </>
          )}
          <button className="btn-primary" onClick={handleSave} disabled={saving} style={{ marginTop: "0.75rem" }}>
            {saving ? "Saving..." : saved ? "Saved!" : "Save Changes"}
          </button>
        </div>

        {/* Business Phone Number */}
        <div className="settings-card">
          <h3>Business Phone Number</h3>
          <p className="settings-card-desc">
            Provision a dedicated business phone number to enable the AI Answering Service,
            Missed Call Text-Back, and Two-Way SMS with your leads.
          </p>

          {phoneError && (
            <div style={{
              marginBottom: 12, padding: "8px 12px", borderRadius: 6, fontSize: "0.85rem",
              background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
              color: "var(--red, #ef4444)",
            }}>
              {phoneError}
            </div>
          )}

          {phoneSuccess && (
            <div style={{
              marginBottom: 12, padding: "8px 12px", borderRadius: 6, fontSize: "0.85rem",
              background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.2)",
              color: "var(--green, #4ade80)",
            }}>
              {phoneSuccess}
            </div>
          )}

          {provisionedPhone ? (
            /* Already has a number */
            <div>
              <div style={{
                padding: "12px 14px", borderRadius: 8,
                background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.2)",
                marginBottom: 12,
              }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4 }}>
                  Active phone number
                </div>
                <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--green, #4ade80)", letterSpacing: 1 }}>
                  {provisionedPhone}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
                  Calls and SMS are routed through this number to your AI assistant.
                </div>
              </div>
              <button
                className="btn-danger"
                onClick={handleReleasePhone}
                disabled={releasingPhone}
                style={{ fontSize: "0.85rem" }}
              >
                {releasingPhone ? "Releasing..." : "Release Number"}
              </button>
            </div>
          ) : (
            /* No number — show search UI */
            <div>
              <div className="settings-field">
                <label>Area Code</label>
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    value={phoneAreaCode}
                    onChange={(e) => {
                      setPhoneAreaCode(e.target.value.replace(/\D/g, "").slice(0, 3));
                      setAvailableNumbers([]);
                      setPhoneError(null);
                    }}
                    placeholder="e.g. 512"
                    maxLength={3}
                    style={{ width: 100, flex: "none" }}
                    onKeyDown={(e) => { if (e.key === "Enter") handleSearchNumbers(); }}
                  />
                  <button
                    className="btn-secondary"
                    onClick={handleSearchNumbers}
                    disabled={searchingNumbers || !phoneAreaCode.trim()}
                  >
                    {searchingNumbers ? "Searching..." : "Search Available"}
                  </button>
                </div>
                <span className="settings-field-hint">
                  Enter your preferred area code to find local numbers.
                </span>
              </div>

              {availableNumbers.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: 8 }}>
                    {availableNumbers.length} number{availableNumbers.length !== 1 ? "s" : ""} available
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
                    {availableNumbers.map((n) => (
                      <div key={n.phone_number} style={{
                        display: "flex", justifyContent: "space-between", alignItems: "center",
                        padding: "8px 12px", borderRadius: 8,
                        background: "var(--bg-secondary)", border: "1px solid var(--border)",
                      }}>
                        <div>
                          <span style={{ fontWeight: 600, color: "var(--text-primary)", marginRight: 8 }}>
                            {n.friendly_name}
                          </span>
                          {n.locality && (
                            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                              {n.locality}{n.region ? `, ${n.region}` : ""}
                            </span>
                          )}
                        </div>
                        <div style={{ display: "flex", gap: 6, fontSize: "0.72rem" }}>
                          {n.capabilities?.voice && (
                            <span style={{ padding: "2px 6px", borderRadius: 4, background: "rgba(59,130,246,0.15)", color: "#60a5fa" }}>Voice</span>
                          )}
                          {n.capabilities?.sms && (
                            <span style={{ padding: "2px 6px", borderRadius: 4, background: "rgba(34,197,94,0.15)", color: "#4ade80" }}>SMS</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  <button
                    className="btn-primary"
                    onClick={handleProvision}
                    disabled={provisioningPhone}
                  >
                    {provisioningPhone ? "Provisioning..." : "Provision First Available Number"}
                  </button>
                  <span className="settings-field-hint" style={{ display: "block", marginTop: 6 }}>
                    This will purchase the first available number and configure it for your account.
                  </span>
                </div>
              )}

              {!availableNumbers.length && !searchingNumbers && (
                <div style={{
                  marginTop: 10, padding: "10px 14px", borderRadius: 8, fontSize: "0.83rem",
                  background: "rgba(59,130,246,0.07)", border: "1px solid rgba(59,130,246,0.2)",
                  color: "var(--text-secondary)",
                }}>
                  A provisioned number enables: AI Answering Service, Missed Call Text-Back, and Two-Way SMS.
                  Search above to get started.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Booking Page */}
        {businessSlug && (
          <div className="settings-card">
            <h3>Booking Page</h3>
            <p className="settings-card-desc">
              Share this link with customers so they can book appointments directly. Embed the widget on any website to let visitors book without leaving your page.
            </p>

            {/* Booking URL */}
            <div className="settings-field">
              <label>Booking URL</label>
              <div style={{ display: "flex", gap: 8, alignItems: "stretch" }}>
                <input
                  readOnly
                  value={`https://agentnexlify-production.up.railway.app/api/v1/book/${businessSlug}`}
                  style={{ flex: 1, fontFamily: "monospace", fontSize: "0.82rem", color: "var(--text-secondary)" }}
                  onClick={(e) => e.target.select()}
                />
                <button
                  className="btn-secondary"
                  onClick={() => {
                    navigator.clipboard.writeText(`https://agentnexlify-production.up.railway.app/api/v1/book/${businessSlug}`)
                      .catch(() => { /* clipboard unavailable in insecure context */ });
                  }}
                  style={{ whiteSpace: "nowrap", flexShrink: 0 }}
                >
                  Copy Link
                </button>
              </div>
            </div>

            {/* Embed Code */}
            <div className="settings-field" style={{ marginTop: 12 }}>
              <label>Embed Code (iframe)</label>
              <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                <textarea
                  readOnly
                  rows={4}
                  value={`<iframe\n  src="https://agentnexlify-production.up.railway.app/api/v1/book/${businessSlug}"\n  width="100%"\n  height="600"\n  frameborder="0"\n  style="border:none;border-radius:12px;"\n></iframe>`}
                  style={{
                    flex: 1,
                    fontFamily: "monospace",
                    fontSize: "0.78rem",
                    color: "var(--text-secondary)",
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border)",
                    borderRadius: 6,
                    padding: "8px 10px",
                    resize: "none",
                    lineHeight: 1.5,
                  }}
                  onClick={(e) => e.target.select()}
                />
                <button
                  className="btn-secondary"
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `<iframe\n  src="https://agentnexlify-production.up.railway.app/api/v1/book/${businessSlug}"\n  width="100%"\n  height="600"\n  frameborder="0"\n  style="border:none;border-radius:12px;"\n></iframe>`
                    ).catch(() => { /* clipboard unavailable in insecure context */ });
                  }}
                  style={{ whiteSpace: "nowrap", flexShrink: 0 }}
                >
                  Copy Code
                </button>
              </div>
              <span className="settings-field-hint">
                Paste this into your website's HTML to embed the booking form.
              </span>
            </div>
          </div>
        )}

        {/* Quick Links */}
        <div className="settings-card">
          <h3>Quick Links</h3>
          <div className="settings-links">
            <button className="settings-link-btn" onClick={() => onNavigate?.("widget")}>Widget Settings</button>
            <button className="settings-link-btn" onClick={() => onNavigate?.("faq")}>FAQ Manager</button>
            <button className="settings-link-btn" onClick={() => onNavigate?.("availability")}>Calendar Availability</button>
          </div>
        </div>

        {/* Conversation Tags */}
        <div className="settings-card">
          <h3>Conversation Tags</h3>
          <p className="settings-card-desc">
            Define tags for AI auto-categorization of conversations. System tags are built-in; add custom tags for your business needs.
          </p>

          {/* Tag list */}
          {tagDefs.length === 0 ? (
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: 8 }}>
              No tags defined yet. Add custom tags below, or the AI will use default categories when auto-tagging conversations.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
              {tagDefs.map((tag) => (
                <div key={tag.id} style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "8px 12px", borderRadius: 8,
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                  opacity: tag.is_enabled ? 1 : 0.5,
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{
                      width: 10, height: 10, borderRadius: "50%",
                      background: tag.tag_color || "#6b7280",
                      flexShrink: 0,
                    }} />
                    <span style={{ fontSize: "0.9rem", color: "var(--text-primary)" }}>{tag.tag_name}</span>
                    <span style={{
                      fontSize: "0.7rem", padding: "2px 6px", borderRadius: 4,
                      background: tag.is_system ? "rgba(59,130,246,0.15)" : "rgba(139,92,246,0.15)",
                      color: tag.is_system ? "rgba(96,165,250,1)" : "rgba(167,139,250,1)",
                    }}>
                      {tag.is_system ? "system" : "custom"}
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <button
                      onClick={() => handleToggleTag(tag)}
                      style={{
                        background: "none", border: "none", cursor: "pointer",
                        fontSize: "0.8rem",
                        color: tag.is_enabled ? "rgba(34,197,94,0.9)" : "var(--text-muted)",
                      }}
                      title={tag.is_enabled ? "Disable tag" : "Enable tag"}
                    >
                      {tag.is_enabled ? "enabled" : "disabled"}
                    </button>
                    {!tag.is_system && (
                      <button
                        onClick={() => handleDeleteTag(tag.id)}
                        style={{
                          background: "none", border: "none", cursor: "pointer",
                          color: "var(--text-muted)", fontSize: "0.8rem",
                        }}
                        title="Delete custom tag"
                      >
                        delete
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Add custom tag form */}
          <div style={{
            marginTop: 16, padding: "12px 14px", borderRadius: 8,
            background: "var(--bg-secondary)", border: "1px solid var(--border)",
          }}>
            <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "block", marginBottom: 8 }}>
              Add custom tag
            </label>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="color"
                value={newTagColor}
                onChange={(e) => setNewTagColor(e.target.value)}
                style={{
                  width: 32, height: 32, padding: 0, border: "1px solid var(--border)",
                  borderRadius: 6, cursor: "pointer", background: "transparent",
                }}
                title="Tag color"
              />
              <input
                value={newTagName}
                onChange={(e) => setNewTagName(e.target.value)}
                placeholder="e.g. pricing-inquiry"
                onKeyDown={(e) => { if (e.key === "Enter") handleAddTag(); }}
                style={{ flex: 1 }}
              />
              <button
                className="btn-primary"
                onClick={handleAddTag}
                disabled={savingTag || !newTagName.trim()}
                style={{ whiteSpace: "nowrap" }}
              >
                {savingTag ? "Adding..." : "Add Tag"}
              </button>
            </div>
          </div>
        </div>

        {/* Custom Fields */}
        <div className="settings-card">
          <h3>Custom Fields</h3>
          <p className="settings-card-desc">
            Add custom fields to collect additional information on each lead.
            Fields appear in the lead detail panel and can be filled in for any contact.
          </p>

          {cfLoadError && (
            <p style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 8 }}>{cfLoadError}</p>
          )}

          {/* Existing fields list */}
          {customFieldDefs.length === 0 && !cfLoadError ? (
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: 8 }}>
              No custom fields yet. Add fields below to track additional information on your leads,
              such as "Preferred contact time", "Project type", or "Lead source".
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
              {customFieldDefs.map((field) => (
                <div key={field.id} style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "9px 14px",
                  borderRadius: 8,
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: "0.9rem", color: "var(--text-primary)", fontWeight: 500 }}>
                      {field.name}
                    </span>
                    <span style={{
                      fontSize: "0.7rem",
                      padding: "2px 8px",
                      borderRadius: 4,
                      background: "rgba(0,191,255,0.12)",
                      color: "var(--accent, #00bfff)",
                      fontWeight: 600,
                      textTransform: "uppercase",
                    }}>
                      {field.field_type}
                    </span>
                    {field.is_required && (
                      <span style={{
                        fontSize: "0.7rem",
                        padding: "2px 8px",
                        borderRadius: 4,
                        background: "rgba(239,68,68,0.12)",
                        color: "#f87171",
                        fontWeight: 600,
                      }}>
                        Required
                      </span>
                    )}
                    {field.field_type === "dropdown" && field.options && field.options.length > 0 && (
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        ({field.options.join(", ")})
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => handleDeleteCustomField(field.id)}
                    disabled={deletingFieldId === field.id}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                      fontSize: "0.8rem",
                      padding: "2px 4px",
                    }}
                    title="Delete field"
                  >
                    {deletingFieldId === field.id ? "..." : "delete"}
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add field form */}
          <div style={{
            marginTop: 16,
            padding: "14px 16px",
            borderRadius: 8,
            background: "var(--bg-secondary)",
            border: "1px solid var(--border)",
          }}>
            <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "block", marginBottom: 10 }}>
              Add a new field
            </label>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-start" }}>
              <input
                value={newFieldName}
                onChange={(e) => setNewFieldName(e.target.value)}
                placeholder="Field name (e.g. Project Type)"
                style={{ flex: "2 1 160px", minWidth: 140 }}
                onKeyDown={(e) => { if (e.key === "Enter") handleAddCustomField(); }}
              />
              <select
                value={newFieldType}
                onChange={(e) => { setNewFieldType(e.target.value); setNewFieldOptions(""); }}
                style={{
                  flex: "1 1 110px",
                  padding: "8px 10px",
                  borderRadius: 6,
                  border: "1px solid var(--border)",
                  background: "var(--bg-primary)",
                  color: "var(--text-primary)",
                  fontSize: "0.9rem",
                }}
              >
                <option value="text">Text</option>
                <option value="number">Number</option>
                <option value="dropdown">Dropdown</option>
                <option value="date">Date</option>
                <option value="checkbox">Checkbox</option>
              </select>
              {newFieldType === "dropdown" && (
                <input
                  value={newFieldOptions}
                  onChange={(e) => setNewFieldOptions(e.target.value)}
                  placeholder="Options: Yes, No, Maybe"
                  style={{ flex: "3 1 180px", minWidth: 150 }}
                  title="Enter comma-separated options"
                />
              )}
              <label style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                cursor: "pointer",
                color: "var(--text-secondary)",
                fontSize: "0.85rem",
                whiteSpace: "nowrap",
                alignSelf: "center",
              }}>
                <input
                  type="checkbox"
                  checked={newFieldRequired}
                  onChange={(e) => setNewFieldRequired(e.target.checked)}
                  style={{ width: "auto" }}
                />
                Required
              </label>
              <button
                className="btn-primary"
                onClick={handleAddCustomField}
                disabled={savingField || !newFieldName.trim()}
                style={{ whiteSpace: "nowrap", alignSelf: "flex-start" }}
              >
                {savingField ? "Adding..." : "Add Field"}
              </button>
            </div>
            {newFieldType === "dropdown" && (
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "8px 0 0" }}>
                Enter comma-separated options for the dropdown (e.g. "Option A, Option B, Option C")
              </p>
            )}
          </div>
        </div>

        {/* AI Knowledge Sources */}
        {knowledgeStats && (
          <div className="settings-card">
            <h3>AI Knowledge Sources</h3>
            <p className="settings-card-desc">
              What your AI chatbot currently knows. The more sources, the better your AI can help visitors.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, marginTop: 12 }}>
              <div style={{ padding: "12px 16px", borderRadius: 8, background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: knowledgeStats.faq_count > 0 ? "#22c55e" : "var(--text-muted)" }}>
                  {knowledgeStats.faq_count}
                </div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>FAQ Entries</div>
                {knowledgeStats.faq_count === 0 && (
                  <button onClick={() => onNavigate && onNavigate("faq")} style={{ fontSize: 12, color: "var(--accent)", background: "none", border: "none", cursor: "pointer", padding: 0, marginTop: 4 }}>
                    Add FAQs
                  </button>
                )}
              </div>
              <div style={{ padding: "12px 16px", borderRadius: 8, background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: knowledgeStats.website_pages_crawled > 0 ? "#22c55e" : "var(--text-muted)" }}>
                  {knowledgeStats.website_pages_crawled}
                </div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Website Pages Crawled</div>
                {knowledgeStats.website_crawl_status && (
                  <div style={{ fontSize: 11, color: knowledgeStats.website_crawl_status === "completed" ? "#22c55e" : "#f59e0b", marginTop: 2 }}>
                    Status: {knowledgeStats.website_crawl_status}
                  </div>
                )}
              </div>
              <div style={{ padding: "12px 16px", borderRadius: 8, background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: knowledgeStats.feedback_corrections_count > 0 ? "#f59e0b" : "var(--text-muted)" }}>
                  {knowledgeStats.feedback_corrections_count}
                </div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>AI Corrections</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>From thumbs-down feedback</div>
              </div>
              {knowledgeStats.active_chat_flow && (
                <div style={{ padding: "12px 16px", borderRadius: 8, background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: 16, fontWeight: 600, color: "#8b5cf6" }}>Active</div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Chat Flow: {knowledgeStats.active_chat_flow}</div>
                </div>
              )}
              {knowledgeStats.menu_items_count > 0 && (
                <div style={{ padding: "12px 16px", borderRadius: 8, background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: 24, fontWeight: 700, color: "#22c55e" }}>{knowledgeStats.menu_items_count}</div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Menu Items</div>
                </div>
              )}
              {knowledgeStats.job_postings_count > 0 && (
                <div style={{ padding: "12px 16px", borderRadius: 8, background: "var(--bg-secondary)", border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: 24, fontWeight: 700, color: "#22c55e" }}>{knowledgeStats.job_postings_count}</div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Active Job Postings</div>
                </div>
              )}
            </div>
          </div>
        )}

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

        {/* Client Portal Login */}
        <div className="settings-card">
          <h3>Client Portal Login</h3>
          <p className="settings-card-desc">
            Allow your clients to create an account and log in to see their appointments, invoices, documents, and service history.
            Clients register through their portal link and can then access their account anytime.
          </p>
          <div className="settings-field" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={clientLoginEnabled}
              onChange={handleToggleClientLogin}
              disabled={togglingClientLogin}
              style={{ width: 18, height: 18, cursor: "pointer" }}
            />
            <label style={{ cursor: "pointer" }} onClick={handleToggleClientLogin}>
              {togglingClientLogin ? "Updating..." : clientLoginEnabled ? "Client login enabled" : "Client login disabled"}
            </label>
          </div>
          {clientLoginEnabled && businessSlug && (
            <div style={{
              marginTop: 10, padding: "10px 14px", borderRadius: 8, fontSize: "0.83rem",
              background: "rgba(99,102,241,0.07)", border: "1px solid rgba(99,102,241,0.2)",
              color: "var(--text-secondary)",
            }}>
              Your clients can log in at: <strong style={{ color: "var(--text-primary)" }}>
                {window.location.origin}/client/login/{businessSlug}
              </strong>
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
