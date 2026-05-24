import { EMAIL_TYPES } from "./constants";
import {
  inputStyle,
  selectStyle,
  textareaStyle,
  btnDanger,
  labelStyle,
} from "./styles";
import { Toggle } from "./badges";

export function blankStep(order) {
  return {
    _localId: Math.random().toString(36).slice(2),
    step_order: order,
    delay_days: 0,
    delay_hours: 0,
    subject: "",
    body: "",
    email_type: "email",
    is_active: true,
  };
}

export function StepRow({ step, index, onChange, onDelete }) {
  return (
    <div
      style={{
        background: "var(--bg-primary)",
        border: "1px solid var(--border)",
        borderRadius: 10,
        padding: "16px 18px",
        marginBottom: 12,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 14,
        }}
      >
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: "50%",
            background: "var(--accent-dim)",
            color: "var(--accent)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700,
            fontSize: "0.85rem",
            flexShrink: 0,
          }}
        >
          {index + 1}
        </div>
        <span
          style={{
            fontWeight: 600,
            fontSize: "0.9rem",
            color: "var(--text-primary)",
            flex: 1,
          }}
        >
          Step {index + 1}
        </span>
        <Toggle
          checked={step.is_active !== false}
          onChange={(v) => onChange({ ...step, is_active: v })}
          label="Active"
        />
        <button style={btnDanger} onClick={() => onDelete(step)}>
          Remove
        </button>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 12,
          marginBottom: 12,
        }}
      >
        <div>
          <label style={labelStyle}>Delay Days</label>
          <input
            type="number"
            min={0}
            style={inputStyle}
            value={step.delay_days}
            onChange={(e) =>
              onChange({
                ...step,
                delay_days: parseInt(e.target.value, 10) || 0,
              })
            }
          />
        </div>
        <div>
          <label style={labelStyle}>Delay Hours</label>
          <input
            type="number"
            min={0}
            max={23}
            style={inputStyle}
            value={step.delay_hours}
            onChange={(e) =>
              onChange({
                ...step,
                delay_hours: parseInt(e.target.value, 10) || 0,
              })
            }
          />
        </div>
        <div>
          <label style={labelStyle}>Type</label>
          <select
            style={selectStyle}
            value={step.email_type}
            onChange={(e) => onChange({ ...step, email_type: e.target.value })}
          >
            {EMAIL_TYPES.map((t) => (
              <option key={t.key} value={t.key}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {step.email_type === "email" && (
        <div style={{ marginBottom: 12 }}>
          <label style={labelStyle}>Subject</label>
          <input
            type="text"
            style={inputStyle}
            placeholder="Email subject line"
            value={step.subject}
            onChange={(e) => onChange({ ...step, subject: e.target.value })}
          />
        </div>
      )}

      <div>
        <label style={labelStyle}>
          {step.email_type === "sms" ? "SMS Message" : "Email Body"}
        </label>
        <textarea
          style={textareaStyle}
          placeholder={
            step.email_type === "sms"
              ? "SMS message text..."
              : "Email body content..."
          }
          value={step.body}
          onChange={(e) => onChange({ ...step, body: e.target.value })}
        />
      </div>
    </div>
  );
}
