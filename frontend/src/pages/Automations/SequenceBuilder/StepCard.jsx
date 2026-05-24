import { DELAY_UNITS, FORMAT_ACTIONS, TEMPLATE_VARS } from "./constants";
import {
  inputStyle,
  selectStyle,
  stepCardStyle,
  btnSecondary,
  toolbarBtn,
} from "./styles";
import { renderWithSampleData } from "./utils";
import EmailPreview from "./EmailPreview";
import TemplatePicker from "./TemplatePicker";

export default function StepCard({
  step,
  idx,
  steps,
  previewIdx,
  pickerIdx,
  templates,
  starterTemplates,
  savingTpl,
  tplError,
  setPreviewIdx,
  setPickerIdx,
  setFocusedField,
  updateStep,
  removeStep,
  handleTemplateSelect,
  handleSaveAsTemplate,
  insertFormat,
  insertAtCursor,
}) {
  const isEmail = step.action_type !== "sms";
  const showPreview = previewIdx === idx && isEmail;
  const showPicker = pickerIdx === idx;

  return (
    <div style={stepCardStyle}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "6px",
        }}
      >
        <span
          style={{
            color: "var(--accent)",
            fontWeight: 600,
            fontSize: "13px",
          }}
        >
          Step {idx + 1}
        </span>
        <div style={{ display: "flex", gap: "5px", flexWrap: "wrap" }}>
          {isEmail && (
            <>
              <button
                onClick={() => setPreviewIdx(showPreview ? null : idx)}
                style={{
                  ...btnSecondary,
                  padding: "2px 8px",
                  fontSize: "11px",
                  color: showPreview ? "var(--accent)" : "var(--text-muted)",
                  borderColor: showPreview ? "var(--accent)" : "var(--border)",
                }}
              >
                {showPreview ? "Hide Preview" : "Preview"}
              </button>
              <button
                onClick={() => setPickerIdx(showPicker ? null : idx)}
                style={{
                  ...btnSecondary,
                  padding: "2px 8px",
                  fontSize: "11px",
                }}
              >
                Templates
              </button>
              <button
                onClick={() => handleSaveAsTemplate(idx)}
                disabled={savingTpl || !step.body_template.trim()}
                style={{
                  ...btnSecondary,
                  padding: "2px 8px",
                  fontSize: "11px",
                  opacity: savingTpl || !step.body_template.trim() ? 0.4 : 1,
                }}
              >
                {savingTpl ? "Saving..." : "Save as Template"}
              </button>
            </>
          )}
          {steps.length > 1 && (
            <button
              onClick={() => removeStep(idx)}
              style={{
                ...btnSecondary,
                padding: "2px 8px",
                fontSize: "12px",
                color: "var(--red)",
              }}
            >
              Remove
            </button>
          )}
        </div>
      </div>

      {tplError && (
        <div
          style={{
            color: "var(--red, #ef4444)",
            fontSize: "12px",
            padding: "4px 0",
          }}
        >
          {tplError}
        </div>
      )}

      {showPicker && (
        <TemplatePicker
          templates={templates}
          starterTemplates={starterTemplates}
          onSelect={(t) => handleTemplateSelect(idx, t)}
          onClose={() => setPickerIdx(null)}
        />
      )}

      <div
        style={{
          display: "flex",
          gap: "8px",
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
          Wait
        </span>
        <input
          type="number"
          min="0"
          style={{ ...inputStyle, width: "80px" }}
          value={step.delay_value}
          onChange={(e) =>
            updateStep(idx, "delay_value", parseInt(e.target.value) || 0)
          }
        />
        <select
          style={{ ...selectStyle, width: "110px" }}
          value={step.delay_unit}
          onChange={(e) =>
            updateStep(idx, "delay_unit", parseInt(e.target.value))
          }
        >
          {DELAY_UNITS.map((u) => (
            <option key={u.value} value={u.value}>
              {u.label}
            </option>
          ))}
        </select>
        <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>
          then send
        </span>
        <select
          style={{ ...selectStyle, width: "130px" }}
          value={step.action_type}
          onChange={(e) => updateStep(idx, "action_type", e.target.value)}
        >
          <option value="email">Email</option>
          <option value="sms">SMS</option>
          <option value="ai_email">AI Email</option>
        </select>
      </div>

      {step.action_type === "ai_email" && (
        <div
          style={{
            padding: "10px 12px",
            background: "var(--purple-dim, rgba(99,102,241,0.1))",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            fontSize: "12px",
            color: "var(--text-secondary)",
            lineHeight: 1.5,
          }}
        >
          AI will generate a personalized email based on the customer's
          conversation and your FAQ entries.
        </div>
      )}

      {isEmail && (
        <input
          id={`step-${idx}-subject_template`}
          style={inputStyle}
          value={step.subject_template}
          onChange={(e) => updateStep(idx, "subject_template", e.target.value)}
          onFocus={() => setFocusedField(`step-${idx}-subject_template`)}
          placeholder="Email subject..."
        />
      )}

      <div
        style={{
          display: "flex",
          gap: "4px",
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        {isEmail &&
          FORMAT_ACTIONS.map((f) => (
            <button
              key={f.tag}
              onClick={() => insertFormat(f.tag)}
              title={f.title}
              style={toolbarBtn}
            >
              {f.label}
            </button>
          ))}
        {isEmail && (
          <div
            style={{
              width: "1px",
              height: "18px",
              background: "var(--border)",
              margin: "0 3px",
            }}
          />
        )}
        {TEMPLATE_VARS.map((v) => (
          <button
            key={v.token}
            onClick={() => insertAtCursor(v.token)}
            title={v.token}
            style={{
              padding: "3px 7px",
              background: "var(--accent-dim)",
              color: "var(--accent)",
              border:
                "1px solid color-mix(in srgb, var(--accent) 30%, transparent)",
              borderRadius: "3px",
              cursor: "pointer",
              fontSize: "11px",
              fontFamily: "monospace",
            }}
          >
            {v.label}
          </button>
        ))}
      </div>

      <div
        style={{
          display: "flex",
          gap: "12px",
          flexDirection: showPreview ? "row" : "column",
        }}
      >
        <textarea
          id={`step-${idx}-body_template`}
          style={{
            ...inputStyle,
            minHeight: showPreview ? "200px" : "120px",
            flex: showPreview ? 1 : undefined,
            resize: "vertical",
            fontFamily: "monospace",
            fontSize: "13px",
            lineHeight: 1.5,
          }}
          value={step.body_template}
          onChange={(e) => updateStep(idx, "body_template", e.target.value)}
          onFocus={() => setFocusedField(`step-${idx}-body_template`)}
          placeholder={
            step.action_type === "sms"
              ? "SMS message (1600 char max)..."
              : step.action_type === "ai_email"
                ? "Leave blank for AI-generated content, or provide a fallback template..."
                : "Write your email here. Use the toolbar to format or insert variables..."
          }
        />
        {showPreview && (
          <div style={{ flex: 1 }}>
            <EmailPreview
              body={renderWithSampleData(step.body_template)}
              subject={renderWithSampleData(step.subject_template)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
