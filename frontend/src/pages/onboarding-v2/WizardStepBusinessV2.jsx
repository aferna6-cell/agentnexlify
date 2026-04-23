import { useState } from "react";
import { saveStep } from "../../utils/api/onboardingV2";

const TIMEZONES = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Phoenix",
  "America/Anchorage",
  "America/Adak",
  "Pacific/Honolulu",
];

function tzLabel(tz) {
  return tz
    .replace("America/", "")
    .replace("Pacific/", "Pacific/")
    .replace(/_/g, " ");
}

function isUrlShaped(val) {
  return val.startsWith("http://") || val.startsWith("https://");
}

export default function WizardStepBusinessV2({
  wizardData,
  user,
  token,
  onNext,
}) {
  const [form, setForm] = useState({
    businessName: wizardData.businessName || user?.businessName || "",
    websiteUrl: wizardData.websiteUrl || "",
    serviceArea: wizardData.serviceArea || "",
    timezone:
      wizardData.timezone ||
      Intl.DateTimeFormat().resolvedOptions().timeZone ||
      "America/New_York",
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.businessName.trim()) {
      setError("Business name is required.");
      return;
    }
    if (!form.websiteUrl.trim()) {
      setError(
        "Website URL is required — we use it to auto-fill your AI knowledge base.",
      );
      return;
    }
    if (!isUrlShaped(form.websiteUrl.trim())) {
      setError("Website URL must start with http:// or https://");
      return;
    }
    setError("");
    setSaving(true);
    try {
      await saveStep(token, 1, {
        business_name: form.businessName,
        website_url: form.websiteUrl,
        service_area: form.serviceArea,
        timezone: form.timezone,
      });
      onNext({ ...form });
    } catch (err) {
      setError(err.message || "Failed to save. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <h2 style={headingStyle}>Tell us about your business</h2>
      <p style={subStyle}>
        Your website lets our AI auto-fill services, FAQs, and hours in the next
        step.
      </p>

      {error && <div style={errorStyle}>{error}</div>}

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <label style={labelStyle}>
          Business name *
          <input
            style={inputStyle}
            value={form.businessName}
            onChange={set("businessName")}
            placeholder="Acme Plumbing"
            autoComplete="organization"
          />
        </label>

        <label style={labelStyle}>
          Website URL *
          <input
            style={inputStyle}
            value={form.websiteUrl}
            onChange={set("websiteUrl")}
            placeholder="https://acmeplumbing.com"
            inputMode="url"
            autoComplete="url"
          />
          <span style={hintStyle}>
            Required — used to auto-fill your AI knowledge base
          </span>
        </label>

        <label style={labelStyle}>
          Service area
          <input
            style={inputStyle}
            value={form.serviceArea}
            onChange={set("serviceArea")}
            placeholder="Austin, TX and surrounding areas"
          />
        </label>

        <label style={labelStyle}>
          Timezone
          <select
            style={inputStyle}
            value={form.timezone}
            onChange={set("timezone")}
          >
            {TIMEZONES.map((tz) => (
              <option key={tz} value={tz}>
                {tzLabel(tz)}
              </option>
            ))}
          </select>
          <span style={hintStyle}>Auto-detected — change if needed</span>
        </label>
      </div>

      <button type="submit" disabled={saving} style={btnStyle(saving)}>
        {saving ? "Saving..." : "Continue"}
      </button>
    </form>
  );
}

const headingStyle = {
  fontSize: "1.4rem",
  fontWeight: 700,
  marginBottom: 8,
  marginTop: 0,
};
const subStyle = {
  color: "rgba(255,255,255,0.5)",
  marginBottom: 28,
  fontSize: "0.9rem",
  marginTop: 0,
};
const errorStyle = {
  background: "rgba(220,38,38,0.15)",
  border: "1px solid rgba(220,38,38,0.3)",
  color: "#fca5a5",
  padding: "10px 14px",
  borderRadius: 8,
  marginBottom: 16,
  fontSize: "0.9rem",
};
const labelStyle = {
  display: "flex",
  flexDirection: "column",
  gap: 6,
  fontSize: "0.9rem",
  fontWeight: 500,
  color: "rgba(255,255,255,0.85)",
};
const hintStyle = {
  color: "rgba(255,255,255,0.4)",
  fontSize: "0.78rem",
  fontWeight: 400,
};
const inputStyle = {
  background: "rgba(255,255,255,0.06)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 8,
  padding: "12px 14px",
  color: "#e2e8f0",
  fontSize: "1rem",
  width: "100%",
  boxSizing: "border-box",
  minHeight: 48,
  outline: "none",
};
const btnStyle = (disabled) => ({
  marginTop: 32,
  width: "100%",
  padding: "16px",
  minHeight: 52,
  background: disabled ? "rgba(99,102,241,0.4)" : "#6366f1",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  fontSize: "1rem",
  fontWeight: 600,
  cursor: disabled ? "not-allowed" : "pointer",
  transition: "background 0.15s ease",
});
