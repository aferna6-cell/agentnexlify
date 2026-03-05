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
  });
  const [email, setEmail] = useState("");

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
      });
      setEmail(tenant.owner_email || "");
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
              <span className="settings-plan-badge">{(user?.plan || "free").charAt(0).toUpperCase() + (user?.plan || "free").slice(1)}</span>
              <button className="btn-secondary btn-sm" onClick={() => onNavigate?.("billing")}>
                Manage Plan
              </button>
            </div>
          </div>
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
