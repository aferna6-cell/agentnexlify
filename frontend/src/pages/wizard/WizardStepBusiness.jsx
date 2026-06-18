// frontend/src/pages/wizard/WizardStepBusiness.jsx
import { useState } from "react";

const INDUSTRIES = [
  "other",
  "plumbing", "hvac", "electrical", "roofing", "landscaping",
  "cleaning", "pest_control", "painting", "flooring", "general_contractor",
  "auto_shop", "salon", "spa", "dental", "medical", "veterinary",
  "legal", "accounting", "real_estate", "restaurant", "retail",
];

const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

const TIMEZONES = [
  "America/New_York", "America/Chicago", "America/Denver",
  "America/Los_Angeles", "America/Phoenix", "America/Anchorage", "Pacific/Honolulu",
];

function defaultHours() {
  const h = { timezone: "America/New_York" };
  DAYS.forEach(d => {
    h[d] = d === "saturday" || d === "sunday"
      ? { enabled: false, open: "09:00", close: "17:00" }
      : { enabled: true, open: "09:00", close: "17:00" };
  });
  return h;
}

function industryLabel(value) {
  if (!value || value === "other") return "General business / I'll choose later";
  const labels = {
    auto_shop: "Auto Shop",
    general_contractor: "General Contractor",
    hvac: "HVAC",
    pest_control: "Pest Control",
    real_estate: "Real Estate",
    spa: "Spa",
  };
  return labels[value] || value.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

export default function WizardStepBusiness({ wizardData, onNext }) {
  const [form, setForm] = useState({
    business_name: wizardData.business_name || "",
    business_type: wizardData.business_type || "other",
    city: wizardData.city || "",
    phone: wizardData.phone || "",
    website_url: wizardData.website_url || "",
    hours: wizardData.hours || defaultHours(),
  });
  const [error, setError] = useState("");

  function set(field) {
    return e => setForm(f => ({ ...f, [field]: e.target.value }));
  }

  function setHours(day, field, value) {
    setForm(f => ({
      ...f,
      hours: {
        ...f.hours,
        [day]: { ...f.hours[day], [field]: value },
      },
    }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!form.business_name.trim()) { setError("Business name is required."); return; }
    if (!form.city.trim()) { setError("City is required."); return; }
    setError("");
    onNext(form);
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 8 }}>Tell us about your business</h2>
      <p style={{ color: "rgba(255,255,255,0.5)", marginBottom: 32, fontSize: "0.9rem" }}>
        This helps your AI assistant answer service-area, estimate, and scheduling questions accurately.
      </p>

      {error && <div style={{ background: "#dc2626", color: "#fff", padding: "10px 14px", borderRadius: 8, marginBottom: 16, fontSize: "0.9rem" }}>{error}</div>}

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <label style={labelStyle}>
          Business Name *
          <input style={inputStyle} value={form.business_name} onChange={set("business_name")} placeholder="Acme Plumbing & Heating" required />
        </label>

        <label style={labelStyle}>
          Industry *
          <select style={inputStyle} value={form.business_type} onChange={set("business_type")}>
            {INDUSTRIES.map(i => <option key={i} value={i}>{industryLabel(i)}</option>)}
          </select>
          <span style={hintStyle}>
            Choose your trade so we can seed a better greeting, service suggestions, and dashboard defaults.
          </span>
        </label>

        <label style={labelStyle}>
          City / Service Area or ZIP Codes *
          <input style={inputStyle} value={form.city} onChange={set("city")} placeholder="Austin, TX" required />
        </label>

        <label style={labelStyle}>
          Phone Number
          <input style={inputStyle} value={form.phone} onChange={set("phone")} placeholder="512-555-0100" type="tel" />
        </label>

        <label style={labelStyle}>
          Website URL
          <input style={inputStyle} value={form.website_url} onChange={set("website_url")} placeholder="https://acmeplumbing.com" type="url" />
        </label>

        {/* Hours grid */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>Business Hours</span>
            <select
              style={{ ...inputStyle, width: "auto", padding: "6px 10px", fontSize: "0.8rem", minHeight: 36 }}
              value={form.hours.timezone}
              onChange={e => setForm(f => ({ ...f, hours: { ...f.hours, timezone: e.target.value } }))}
            >
              {TIMEZONES.map(tz => <option key={tz} value={tz}>{tz.replace("America/", "").replace("Pacific/", "Pacific/")}</option>)}
            </select>
          </div>
          {DAYS.map(day => (
            <div key={day} style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 10, marginBottom: 8, fontSize: "0.85rem" }}>
              <input
                type="checkbox"
                checked={form.hours[day]?.enabled || false}
                onChange={e => setHours(day, "enabled", e.target.checked)}
                style={{ width: 16, height: 16, cursor: "pointer", flexShrink: 0 }}
              />
              <span style={{ width: 80, textTransform: "capitalize", color: form.hours[day]?.enabled ? "inherit" : "rgba(255,255,255,0.3)" }}>{day}</span>
              {form.hours[day]?.enabled && (
                <>
                  <input type="time" value={form.hours[day].open} onChange={e => setHours(day, "open", e.target.value)} style={{ ...inputStyle, width: 100, padding: "4px 8px" }} />
                  <span style={{ color: "rgba(255,255,255,0.4)" }}>to</span>
                  <input type="time" value={form.hours[day].close} onChange={e => setHours(day, "close", e.target.value)} style={{ ...inputStyle, width: 100, padding: "4px 8px" }} />
                </>
              )}
              {!form.hours[day]?.enabled && <span style={{ color: "rgba(255,255,255,0.3)" }}>Closed</span>}
            </div>
          ))}
        </div>
      </div>

      <button type="submit" style={btnStyle}>Continue &rarr;</button>
    </form>
  );
}

const labelStyle = { display: "flex", flexDirection: "column", gap: 6, fontSize: "0.9rem", fontWeight: 500 };
const hintStyle = { color: "rgba(255,255,255,0.45)", fontSize: "0.78rem", fontWeight: 400, lineHeight: 1.4 };
const inputStyle = {
  background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 8, padding: "10px 14px", color: "#e2e8f0", fontSize: "0.9rem", width: "100%", boxSizing: "border-box",
};
const btnStyle = {
  marginTop: 32, width: "100%", padding: "14px", background: "#6366f1", color: "#fff",
  border: "none", borderRadius: 10, fontSize: "1rem", fontWeight: 600, cursor: "pointer",
};
