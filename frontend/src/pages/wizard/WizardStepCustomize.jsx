// frontend/src/pages/wizard/WizardStepCustomize.jsx
import { useState, useEffect } from "react";
import { fetchDashboard } from "../../utils/api/dashboard";
import { getPresetWidgetDefaults } from "../../utils/businessPresets";

const POSITIONS = [
  { value: "bottom-right", label: "Bottom Right" },
  { value: "bottom-left", label: "Bottom Left" },
];

export default function WizardStepCustomize({ wizardData, onNext, onBack, token, tenantId }) {
  const presetDefaults = getPresetWidgetDefaults(wizardData.business_type, wizardData.business_name);
  const [form, setForm] = useState({
    widget_bot_name: wizardData.widget_bot_name || presetDefaults.widget_bot_name,
    widget_primary_color: wizardData.widget_primary_color || presetDefaults.widget_primary_color,
    widget_greeting_message: wizardData.widget_greeting_message || presetDefaults.widget_greeting_message,
    widget_position: wizardData.widget_position || presetDefaults.widget_position,
  });
  const [apiKey, setApiKey] = useState(null);

  useEffect(() => {
    if (!token || !tenantId) return;
    fetchDashboard(tenantId, token)
      .then(data => {
        if (data?.widget_api_key) {
          setApiKey(data.widget_api_key);
        }
      })
      .catch(err => {
        // Non-fatal: preview won't show, but customization still works
        console.warn("WizardStepCustomize: failed to fetch widget api_key", err);
      });
  }, [token, tenantId]);

  function set(field) {
    return e => setForm(f => ({ ...f, [field]: e.target.value }));
  }

  const previewSrc = apiKey
    ? `/widget-preview.html?api_key=${encodeURIComponent(apiKey)}`
    : null;

  return (
    <div>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 8 }}>Customize your widget</h2>
      <p style={{ color: "rgba(255,255,255,0.5)", marginBottom: 32, fontSize: "0.9rem" }}>
        Match it to your brand. The live preview updates as you save.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 20, marginBottom: 32 }}>
        <label style={labelStyle}>
          Bot Name
          <input style={inputStyle} value={form.widget_bot_name} onChange={set("widget_bot_name")} placeholder="Acme Assistant" maxLength={100} />
        </label>

        <label style={labelStyle}>
          Primary Color
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <input type="color" value={form.widget_primary_color} onChange={set("widget_primary_color")} style={{ width: 48, height: 40, border: "none", background: "none", cursor: "pointer", padding: 0, borderRadius: 6 }} />
            <input style={{ ...inputStyle, flex: 1 }} value={form.widget_primary_color} onChange={set("widget_primary_color")} placeholder="#00BFFF" />
          </div>
        </label>

        <label style={labelStyle}>
          Greeting Message
          <textarea style={{ ...inputStyle, resize: "vertical" }} value={form.widget_greeting_message} onChange={set("widget_greeting_message")} rows={2} maxLength={500} />
        </label>

        <label style={labelStyle}>
          Position
          <select style={inputStyle} value={form.widget_position} onChange={set("widget_position")}>
            {POSITIONS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
          </select>
        </label>
      </div>

      {/* Live preview */}
      {previewSrc && (
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontWeight: 600, marginBottom: 10 }}>Live Preview</div>
          <div style={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, overflow: "hidden", height: 320, background: "#f0f4f8" }}>
            <iframe
              src={previewSrc}
              style={{ width: "100%", height: "100%", border: "none" }}
              title="Widget Preview"
              sandbox="allow-scripts allow-same-origin"
            />
          </div>
          <p style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.4)", marginTop: 6 }}>
            Preview uses your live widget config. Changes take up to 5 minutes to appear here.
          </p>
        </div>
      )}

      {/* Color preview patch — instant visual feedback before cache expires */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: 16, background: "rgba(255,255,255,0.04)", borderRadius: 10, marginBottom: 32 }}>
        <div style={{ width: 48, height: 48, borderRadius: "50%", background: form.widget_primary_color, flexShrink: 0, boxShadow: "0 2px 8px rgba(0,0,0,0.3)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <svg viewBox="0 0 24 24" width="20" height="20" fill="white"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/></svg>
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{form.widget_bot_name}</div>
          <div style={{ color: "rgba(255,255,255,0.5)", fontSize: "0.8rem" }}>{form.widget_greeting_message}</div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 12 }}>
        <button onClick={onBack} style={{ ...btnStyle, background: "rgba(255,255,255,0.08)", flex: 1 }}>&#8592; Back</button>
        <button onClick={() => onNext(form)} style={{ ...btnStyle, flex: 2 }}>Continue &#8594;</button>
      </div>
    </div>
  );
}

const labelStyle = { display: "flex", flexDirection: "column", gap: 6, fontSize: "0.9rem", fontWeight: 500 };
const inputStyle = { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: "10px 14px", color: "#e2e8f0", fontSize: "0.9rem", width: "100%", boxSizing: "border-box" };
const btnStyle = { padding: "14px", background: "#6366f1", color: "#fff", border: "none", borderRadius: 10, fontSize: "1rem", fontWeight: 600, cursor: "pointer" };
