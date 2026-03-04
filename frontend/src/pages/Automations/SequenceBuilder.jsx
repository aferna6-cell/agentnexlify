import { useState } from "react";

const TRIGGER_OPTIONS = [
  { value: "new_lead", label: "New Lead Created" },
  { value: "lead_stage_change", label: "Lead Stage Changes" },
  { value: "no_response_24h", label: "No Response (24 hours)" },
];

const DELAY_UNITS = [
  { value: 1, label: "minutes" },
  { value: 60, label: "hours" },
  { value: 1440, label: "days" },
];

const TEMPLATE_VARS = ["{{name}}", "{{business_name}}", "{{email}}"];

const overlayStyle = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
  animation: "fadeIn 0.2s ease",
};

const modalStyle = {
  background: "var(--bg-card)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  width: "640px",
  maxHeight: "85vh",
  overflowY: "auto",
  padding: "28px",
  display: "flex",
  flexDirection: "column",
  gap: "20px",
};

const inputStyle = {
  width: "100%",
  padding: "10px 12px",
  background: "var(--bg-primary)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  color: "var(--text-primary)",
  fontSize: "14px",
  outline: "none",
  boxSizing: "border-box",
};

const selectStyle = {
  ...inputStyle,
  cursor: "pointer",
};

const labelStyle = {
  color: "var(--text-secondary)",
  fontSize: "12px",
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  marginBottom: "6px",
  display: "block",
};

const stepCardStyle = {
  background: "var(--bg-primary)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  padding: "16px",
  display: "flex",
  flexDirection: "column",
  gap: "12px",
  position: "relative",
};

const btnPrimary = {
  padding: "10px 20px",
  background: "var(--accent)",
  color: "#000",
  border: "none",
  borderRadius: "var(--radius-sm)",
  cursor: "pointer",
  fontWeight: 600,
  fontSize: "14px",
};

const btnSecondary = {
  padding: "8px 14px",
  background: "transparent",
  color: "var(--text-secondary)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  cursor: "pointer",
  fontSize: "13px",
};

function emptyStep(order) {
  return {
    step_order: order,
    delay_minutes: 0,
    delay_value: 0,
    delay_unit: 1,
    action_type: "email",
    subject_template: "",
    body_template: "",
  };
}

export default function SequenceBuilder({ sequence, onSave, onClose, saving }) {
  const isEditing = !!sequence;
  const [name, setName] = useState(sequence?.name || "");
  const [triggerEvent, setTriggerEvent] = useState(sequence?.trigger_event || "new_lead");
  const [targetStage, setTargetStage] = useState(sequence?.trigger_config?.target_stage || "");
  const [steps, setSteps] = useState(() => {
    if (sequence?.steps?.length) {
      return sequence.steps.map((s) => {
        let unit = 1;
        let val = s.delay_minutes;
        if (val >= 1440 && val % 1440 === 0) { unit = 1440; val = val / 1440; }
        else if (val >= 60 && val % 60 === 0) { unit = 60; val = val / 60; }
        return { ...s, delay_value: val, delay_unit: unit };
      });
    }
    return [emptyStep(1)];
  });
  const [focusedField, setFocusedField] = useState(null);

  const addStep = () => {
    setSteps([...steps, emptyStep(steps.length + 1)]);
  };

  const removeStep = (idx) => {
    if (steps.length <= 1) return;
    const updated = steps.filter((_, i) => i !== idx).map((s, i) => ({ ...s, step_order: i + 1 }));
    setSteps(updated);
  };

  const updateStep = (idx, field, value) => {
    const updated = [...steps];
    updated[idx] = { ...updated[idx], [field]: value };
    setSteps(updated);
  };

  const insertVar = (varName) => {
    if (!focusedField) return;
    const el = document.getElementById(focusedField);
    if (!el) return;
    const start = el.selectionStart || el.value.length;
    const before = el.value.slice(0, start);
    const after = el.value.slice(el.selectionEnd || start);
    const newVal = before + varName + after;
    // Find which step/field this belongs to
    const parts = focusedField.split("-");
    const idx = parseInt(parts[1]);
    const field = parts[2];
    updateStep(idx, field, newVal);
    setTimeout(() => {
      el.focus();
      const pos = start + varName.length;
      el.setSelectionRange(pos, pos);
    }, 0);
  };

  const handleSave = () => {
    if (!name.trim()) return;
    const data = {
      name: name.trim(),
      trigger_event: triggerEvent,
      trigger_config: triggerEvent === "lead_stage_change" ? { target_stage: targetStage } : {},
      steps: steps.map((s) => ({
        step_order: s.step_order,
        delay_minutes: s.delay_value * s.delay_unit,
        action_type: s.action_type,
        subject_template: s.subject_template,
        body_template: s.body_template,
      })),
    };
    onSave(data);
  };

  return (
    <div style={overlayStyle} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={modalStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ color: "var(--text-primary)", margin: 0, fontSize: "18px" }}>
            {isEditing ? "Edit Sequence" : "Create Sequence"}
          </h2>
          <button onClick={onClose} style={{ ...btnSecondary, padding: "4px 10px", fontSize: "16px" }}>&times;</button>
        </div>

        {/* Name */}
        <div>
          <label style={labelStyle}>Sequence Name</label>
          <input
            style={inputStyle}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Welcome Email Series"
          />
        </div>

        {/* Trigger */}
        <div>
          <label style={labelStyle}>Trigger</label>
          <select style={selectStyle} value={triggerEvent} onChange={(e) => setTriggerEvent(e.target.value)}>
            {TRIGGER_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {triggerEvent === "lead_stage_change" && (
          <div>
            <label style={labelStyle}>Target Stage</label>
            <select style={selectStyle} value={targetStage} onChange={(e) => setTargetStage(e.target.value)}>
              <option value="">Select stage...</option>
              <option value="contacted">Contacted</option>
              <option value="qualified">Qualified</option>
              <option value="appointment">Appointment</option>
              <option value="closed">Closed</option>
            </select>
          </div>
        )}

        {/* Template variables */}
        <div>
          <label style={labelStyle}>Template Variables</label>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {TEMPLATE_VARS.map((v) => (
              <button
                key={v}
                onClick={() => insertVar(v)}
                style={{
                  padding: "4px 10px",
                  background: "var(--accent-dim)",
                  color: "var(--accent)",
                  border: "1px solid var(--accent)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  fontSize: "12px",
                  fontFamily: "monospace",
                }}
              >
                {v}
              </button>
            ))}
          </div>
          <div style={{ color: "var(--text-muted)", fontSize: "11px", marginTop: "4px" }}>
            Click to insert into the focused field
          </div>
        </div>

        {/* Steps */}
        <div>
          <label style={labelStyle}>Steps</label>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {steps.map((step, idx) => (
              <div key={idx} style={stepCardStyle}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ color: "var(--accent)", fontWeight: 600, fontSize: "13px" }}>
                    Step {idx + 1}
                  </span>
                  {steps.length > 1 && (
                    <button onClick={() => removeStep(idx)} style={{ ...btnSecondary, padding: "2px 8px", fontSize: "12px", color: "var(--red)" }}>
                      Remove
                    </button>
                  )}
                </div>

                {/* Delay */}
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "13px", whiteSpace: "nowrap" }}>Wait</span>
                  <input
                    type="number"
                    min="0"
                    style={{ ...inputStyle, width: "80px" }}
                    value={step.delay_value}
                    onChange={(e) => updateStep(idx, "delay_value", parseInt(e.target.value) || 0)}
                  />
                  <select
                    style={{ ...selectStyle, width: "110px" }}
                    value={step.delay_unit}
                    onChange={(e) => updateStep(idx, "delay_unit", parseInt(e.target.value))}
                  >
                    {DELAY_UNITS.map((u) => (
                      <option key={u.value} value={u.value}>{u.label}</option>
                    ))}
                  </select>
                  <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>then send</span>
                </div>

                {/* Subject */}
                <input
                  id={`step-${idx}-subject_template`}
                  style={inputStyle}
                  value={step.subject_template}
                  onChange={(e) => updateStep(idx, "subject_template", e.target.value)}
                  onFocus={() => setFocusedField(`step-${idx}-subject_template`)}
                  placeholder="Email subject..."
                />

                {/* Body */}
                <textarea
                  id={`step-${idx}-body_template`}
                  style={{ ...inputStyle, minHeight: "100px", resize: "vertical", fontFamily: "inherit" }}
                  value={step.body_template}
                  onChange={(e) => updateStep(idx, "body_template", e.target.value)}
                  onFocus={() => setFocusedField(`step-${idx}-body_template`)}
                  placeholder="Email body (HTML supported)..."
                />
              </div>
            ))}
          </div>
          <button onClick={addStep} style={{ ...btnSecondary, marginTop: "12px" }}>
            + Add Step
          </button>
        </div>

        {/* Actions */}
        <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end", borderTop: "1px solid var(--border)", paddingTop: "16px" }}>
          <button onClick={onClose} style={btnSecondary}>Cancel</button>
          <button
            onClick={handleSave}
            disabled={saving || !name.trim()}
            style={{ ...btnPrimary, opacity: saving || !name.trim() ? 0.5 : 1 }}
          >
            {saving ? "Saving..." : isEditing ? "Update Sequence" : "Create Sequence"}
          </button>
        </div>
      </div>
    </div>
  );
}
