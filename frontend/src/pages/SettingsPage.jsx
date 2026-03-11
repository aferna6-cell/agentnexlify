import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchTenant, updateTenantSettings } from "../utils/api";
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
  });
  const [email, setEmail] = useState("");
  const [livePlan, setLivePlan] = useState(user?.plan || "free");

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

        {/* Quick Links */}
        <div className="settings-card">
          <h3>Quick Links</h3>
          <div className="settings-links">
            <button className="settings-link-btn" onClick={() => onNavigate?.("widget")}>Widget Settings</button>
            <button className="settings-link-btn" onClick={() => onNavigate?.("faq")}>FAQ Manager</button>
            <button className="settings-link-btn" onClick={() => onNavigate?.("availability")}>Calendar Availability</button>
          </div>
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
