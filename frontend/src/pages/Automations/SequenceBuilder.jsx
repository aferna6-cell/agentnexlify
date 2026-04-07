import { useState, useEffect, useRef } from "react";
import DOMPurify from "dompurify";
import { useAuth } from "../../context/AuthContext";
import {
  fetchEmailTemplates,
  createEmailTemplate,
} from "../../utils/api/automations";

const TRIGGER_OPTIONS = [
  { value: "new_lead", label: "New Lead Created" },
  { value: "lead_stage_change", label: "Lead Stage Changes" },
  { value: "no_response_24h", label: "No Response (24 hours)" },
  { value: "appointment_completed", label: "Appointment Completed" },
];

const DELAY_UNITS = [
  { value: 1, label: "minutes" },
  { value: 60, label: "hours" },
  { value: 1440, label: "days" },
];

const TEMPLATE_VARS = [
  { token: "{{name}}", label: "Name" },
  { token: "{{business_name}}", label: "Business" },
  { token: "{{email}}", label: "Email" },
  { token: "{{phone}}", label: "Phone" },
  { token: "{{review_link}}", label: "Review Link" },
];

const FORMAT_ACTIONS = [
  { label: "B", tag: "strong", title: "Bold" },
  { label: "I", tag: "em", title: "Italic" },
  { label: "H2", tag: "h2", title: "Heading" },
  { label: "P", tag: "p", title: "Paragraph" },
  { label: "Link", tag: "a", title: "Insert link" },
  { label: "BR", tag: "br", title: "Line break" },
];

const SAMPLE_CONTEXT = {
  "{{name}}": "Alex Johnson",
  "{{business_name}}": "Your Business",
  "{{email}}": "alex@example.com",
  "{{phone}}": "(555) 123-4567",
  "{{review_link}}": "https://g.page/your-business/review",
};

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
  width: "860px",
  maxWidth: "95vw",
  maxHeight: "90vh",
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

const selectStyle = { ...inputStyle, cursor: "pointer" };

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
  color: "var(--accent-contrast)",
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

const toolbarBtn = {
  padding: "4px 8px",
  background: "var(--bg-card)",
  color: "var(--text-secondary)",
  border: "1px solid var(--border)",
  borderRadius: "3px",
  cursor: "pointer",
  fontSize: "12px",
  fontWeight: 600,
  minWidth: "28px",
  lineHeight: 1,
};

const catColors = {
  welcome: "#22c55e",
  follow_up: "#3b82f6",
  reminder: "#eab308",
  review: "#a855f7",
  promotion: "#ec4899",
  custom: "#94a3b8",
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

function renderWithSampleData(text) {
  let result = text || "";
  for (const [k, v] of Object.entries(SAMPLE_CONTEXT)) {
    result = result.split(k).join(v);
  }
  return result;
}

/* ---------- Sample data for template preview ---------- */
const SAMPLE_DATA = {
  name: "Alex Johnson",
  first_name: "Alex",
  email: "alex@example.com",
  phone: "(555) 123-4567",
  business_name: "Your Business",
  business_phone: "(555) 987-6543",
  appointment_date: "Friday, April 10, 2026",
  appointment_time: "2:00 PM",
  review_link: "https://g.page/your-business/review",
  unsubscribe_url: "#",
  status: "New Lead",
  service: "General Consultation",
};

function sanitizeHtml(html) {
  if (!html) return "";
  return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
}

function resolveTemplateVars(text) {
  if (!text) return text;
  const sanitized = sanitizeHtml(text);
  return sanitized.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    const val = SAMPLE_DATA[key];
    if (val !== undefined)
      return `<span style="background:#dbeafe;color:#1e40af;padding:1px 4px;border-radius:3px;font-size:0.9em;" title="Sample: {{${key}}}">${val}</span>`;
    return `<span style="background:#fef3c7;color:#92400e;padding:1px 4px;border-radius:3px;font-size:0.9em;" title="Unknown variable">{{${key}}}</span>`;
  });
}

/* ---------- Email Preview ---------- */
function EmailPreview({ body, subject }) {
  const resolvedSubject = resolveTemplateVars(subject);
  const resolvedBody = resolveTemplateVars(body);

  return (
    <div
      style={{
        background: "#ffffff",
        borderRadius: "var(--radius-sm)",
        border: "1px solid var(--border)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "8px 12px",
          background: "#f1f5f9",
          borderBottom: "1px solid #e2e8f0",
          fontSize: "11px",
          color: "#475569",
          lineHeight: 1.6,
        }}
      >
        <div>
          <strong>From:</strong> Your Business &lt;noreply@agentnexlify.com&gt;
        </div>
        <div>
          <strong>To:</strong> Alex Johnson &lt;alex@example.com&gt;
        </div>
        <div>
          <strong>Subject:</strong> {resolvedSubject || "(no subject)"}
        </div>
      </div>
      <div
        style={{
          padding: "4px 12px 0",
          fontSize: "10px",
          color: "#94a3b8",
          fontStyle: "italic",
        }}
      >
        Variables like {"{{name}}"} are shown with sample data
      </div>
      <div
        style={{
          padding: "16px",
          fontSize: "14px",
          lineHeight: 1.6,
          color: "#1e293b",
          maxHeight: "260px",
          overflowY: "auto",
        }}
        dangerouslySetInnerHTML={{
          __html: resolvedBody
            ? DOMPurify.sanitize(resolvedBody)
            : '<p style="color:#94a3b8;font-style:italic">Start typing to see a preview...</p>',
        }}
      />
    </div>
  );
}

/* ---------- Template Picker ---------- */
function TemplatePicker({ templates, starterTemplates, onSelect, onClose }) {
  const [filter, setFilter] = useState("all");
  const all = [
    ...(starterTemplates || []).map((t) => ({ ...t, _src: "built-in" })),
    ...(templates || []).map((t) => ({ ...t, _src: "custom" })),
  ];
  const filtered =
    filter === "all" ? all : all.filter((t) => t.category === filter);
  const cats = [
    "all",
    "welcome",
    "follow_up",
    "reminder",
    "review",
    "promotion",
    "custom",
  ];

  return (
    <div
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-sm)",
        padding: "14px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "10px",
        }}
      >
        <span
          style={{
            color: "var(--text-primary)",
            fontWeight: 600,
            fontSize: "13px",
          }}
        >
          Choose a Template
        </span>
        <button
          onClick={onClose}
          style={{ ...btnSecondary, padding: "2px 8px", fontSize: "14px" }}
        >
          &times;
        </button>
      </div>
      <div
        style={{
          display: "flex",
          gap: "5px",
          flexWrap: "wrap",
          marginBottom: "10px",
        }}
      >
        {cats.map((c) => (
          <button
            key={c}
            onClick={() => setFilter(c)}
            style={{
              padding: "3px 9px",
              background: filter === c ? "var(--accent)" : "var(--bg-primary)",
              color:
                filter === c
                  ? "var(--accent-contrast)"
                  : "var(--text-secondary)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              fontSize: "11px",
              textTransform: "capitalize",
            }}
          >
            {c === "follow_up" ? "Follow-Up" : c}
          </button>
        ))}
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: "8px",
          maxHeight: "240px",
          overflowY: "auto",
        }}
      >
        {filtered.map((t) => (
          <div
            key={t.id}
            onClick={() => onSelect(t)}
            style={{
              background: "var(--bg-primary)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
              padding: "10px",
              cursor: "pointer",
              transition: "border-color 0.15s",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.borderColor = "var(--accent)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.borderColor = "var(--border)")
            }
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "5px",
                marginBottom: "4px",
              }}
            >
              <span
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  background: catColors[t.category] || catColors.custom,
                  flexShrink: 0,
                }}
              />
              <span
                style={{
                  fontSize: "10px",
                  color: "var(--text-muted)",
                  textTransform: "capitalize",
                }}
              >
                {t.category === "follow_up" ? "Follow-Up" : t.category}
              </span>
              {t._src === "built-in" && (
                <span
                  style={{
                    fontSize: "9px",
                    color: "var(--text-muted)",
                    marginLeft: "auto",
                  }}
                >
                  Built-in
                </span>
              )}
            </div>
            <div
              style={{
                color: "var(--text-primary)",
                fontSize: "12px",
                fontWeight: 600,
                marginBottom: "2px",
              }}
            >
              {t.name}
            </div>
            <div
              style={{
                color: "var(--text-muted)",
                fontSize: "11px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {t.subject_template || "(no subject)"}
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div
            style={{
              color: "var(--text-muted)",
              fontSize: "12px",
              padding: "16px",
              textAlign: "center",
              gridColumn: "1 / -1",
            }}
          >
            No templates in this category
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------- Main Component ---------- */
export default function SequenceBuilder({ sequence, onSave, onClose, saving }) {
  const { user, token } = useAuth();
  const isEditing = !!sequence;
  const [name, setName] = useState(sequence?.name || "");
  const [triggerEvent, setTriggerEvent] = useState(
    sequence?.trigger_event || "new_lead",
  );
  const [targetStage, setTargetStage] = useState(
    sequence?.trigger_config?.target_stage || "",
  );
  const [steps, setSteps] = useState(() => {
    if (sequence?.steps?.length) {
      return sequence.steps.map((s) => {
        let unit = 1;
        let val = s.delay_minutes;
        if (val >= 1440 && val % 1440 === 0) {
          unit = 1440;
          val = val / 1440;
        } else if (val >= 60 && val % 60 === 0) {
          unit = 60;
          val = val / 60;
        }
        return { ...s, delay_value: val, delay_unit: unit };
      });
    }
    return [emptyStep(1)];
  });
  const [focusedField, setFocusedField] = useState(null);
  const [previewIdx, setPreviewIdx] = useState(null);
  const [pickerIdx, setPickerIdx] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [starterTemplates, setStarterTemplates] = useState([]);
  const [savingTpl, setSavingTpl] = useState(false);
  const [tplError, setTplError] = useState(null);

  useEffect(() => {
    if (!user?.tenantId) return;
    fetchEmailTemplates(user.tenantId, token)
      .then((d) => {
        setTemplates(d.templates || []);
        setStarterTemplates(d.starter_templates || []);
      })
      .catch((err) => {
        console.warn("Failed to load email templates:", err.message || err);
        // Non-critical: template picker will show empty state
      });
  }, [user?.tenantId, token]);

  const addStep = () => setSteps([...steps, emptyStep(steps.length + 1)]);

  const removeStep = (idx) => {
    if (steps.length <= 1) return;
    const updated = steps
      .filter((_, i) => i !== idx)
      .map((s, i) => ({ ...s, step_order: i + 1 }));
    setSteps(updated);
    if (previewIdx === idx) setPreviewIdx(null);
    else if (previewIdx > idx) setPreviewIdx(previewIdx - 1);
  };

  const updateStep = (idx, field, value) => {
    const updated = [...steps];
    updated[idx] = { ...updated[idx], [field]: value };
    setSteps(updated);
  };

  const insertAtCursor = (text) => {
    if (!focusedField) return;
    const el = document.getElementById(focusedField);
    if (!el) return;
    const start = el.selectionStart || el.value.length;
    const end = el.selectionEnd || start;
    const before = el.value.slice(0, start);
    const after = el.value.slice(end);
    const newVal = before + text + after;
    const parts = focusedField.split("-");
    const idx = parseInt(parts[1]);
    const field = parts[2];
    updateStep(idx, field, newVal);
    setTimeout(() => {
      el.focus();
      const pos = start + text.length;
      el.setSelectionRange(pos, pos);
    }, 0);
  };

  const insertFormat = (tag) => {
    if (!focusedField) return;
    const el = document.getElementById(focusedField);
    if (!el) return;
    const start = el.selectionStart || 0;
    const end = el.selectionEnd || start;
    const selected = el.value.slice(start, end);
    let insert;
    if (tag === "br") insert = "<br>";
    else if (tag === "a")
      insert = `<a href="URL">${selected || "Link text"}</a>`;
    else insert = `<${tag}>${selected}</${tag}>`;
    const newVal = el.value.slice(0, start) + insert + el.value.slice(end);
    const parts = focusedField.split("-");
    const idx = parseInt(parts[1]);
    const field = parts[2];
    updateStep(idx, field, newVal);
    setTimeout(() => {
      el.focus();
      const pos = start + insert.length;
      el.setSelectionRange(pos, pos);
    }, 0);
  };

  const handleTemplateSelect = (stepIdx, tpl) => {
    const updated = [...steps];
    updated[stepIdx] = {
      ...updated[stepIdx],
      subject_template: tpl.subject_template,
      body_template: tpl.body_template,
    };
    setSteps(updated);
    setPickerIdx(null);
  };

  const handleSaveAsTemplate = async (idx) => {
    const step = steps[idx];
    if (!step.body_template.trim()) return;
    setSavingTpl(true);
    setTplError(null);
    try {
      const res = await createEmailTemplate(user.tenantId, token, {
        name: `Template from Step ${idx + 1}`,
        category: "custom",
        subject_template: step.subject_template,
        body_template: step.body_template,
      });
      setTemplates((prev) => [res.template, ...prev]);
    } catch (err) {
      console.warn("Failed to save as template:", err.message || err);
      setTplError("Failed to save template. Please try again.");
    } finally {
      setSavingTpl(false);
    }
  };

  const handleSave = () => {
    if (!name.trim()) return;
    onSave({
      name: name.trim(),
      trigger_event: triggerEvent,
      trigger_config:
        triggerEvent === "lead_stage_change"
          ? { target_stage: targetStage }
          : {},
      steps: steps.map((s) => ({
        step_order: s.step_order,
        delay_minutes: s.delay_value * s.delay_unit,
        action_type: s.action_type,
        subject_template: s.subject_template,
        body_template: s.body_template,
      })),
    });
  };

  return (
    <div
      style={overlayStyle}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div style={modalStyle}>
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h2
            style={{
              color: "var(--text-primary)",
              margin: 0,
              fontSize: "18px",
            }}
          >
            {isEditing ? "Edit Sequence" : "Create Sequence"}
          </h2>
          <button
            onClick={onClose}
            style={{ ...btnSecondary, padding: "4px 10px", fontSize: "16px" }}
          >
            &times;
          </button>
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
          <select
            style={selectStyle}
            value={triggerEvent}
            onChange={(e) => setTriggerEvent(e.target.value)}
          >
            {TRIGGER_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        {triggerEvent === "lead_stage_change" && (
          <div>
            <label style={labelStyle}>Target Stage</label>
            <select
              style={selectStyle}
              value={targetStage}
              onChange={(e) => setTargetStage(e.target.value)}
            >
              <option value="">Select stage...</option>
              <option value="new">New</option>
              <option value="contacted">Contacted</option>
              <option value="appointment_booked">Appointment Booked</option>
              <option value="closed">Closed</option>
              <option value="lost">Lost</option>
            </select>
          </div>
        )}

        {/* Steps */}
        <div>
          <label style={labelStyle}>Steps</label>
          <div
            style={{ display: "flex", flexDirection: "column", gap: "16px" }}
          >
            {steps.map((step, idx) => {
              const isEmail = step.action_type !== "sms";
              const showPreview = previewIdx === idx && isEmail;
              const showPicker = pickerIdx === idx;

              return (
                <div key={idx} style={stepCardStyle}>
                  {/* Step header */}
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
                    <div
                      style={{ display: "flex", gap: "5px", flexWrap: "wrap" }}
                    >
                      {isEmail && (
                        <>
                          <button
                            onClick={() =>
                              setPreviewIdx(showPreview ? null : idx)
                            }
                            style={{
                              ...btnSecondary,
                              padding: "2px 8px",
                              fontSize: "11px",
                              color: showPreview
                                ? "var(--accent)"
                                : "var(--text-muted)",
                              borderColor: showPreview
                                ? "var(--accent)"
                                : "var(--border)",
                            }}
                          >
                            {showPreview ? "Hide Preview" : "Preview"}
                          </button>
                          <button
                            onClick={() =>
                              setPickerIdx(showPicker ? null : idx)
                            }
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
                              opacity:
                                savingTpl || !step.body_template.trim()
                                  ? 0.4
                                  : 1,
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

                  {/* Template save error */}
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

                  {/* Template picker */}
                  {showPicker && (
                    <TemplatePicker
                      templates={templates}
                      starterTemplates={starterTemplates}
                      onSelect={(t) => handleTemplateSelect(idx, t)}
                      onClose={() => setPickerIdx(null)}
                    />
                  )}

                  {/* Delay + type row */}
                  <div
                    style={{
                      display: "flex",
                      gap: "8px",
                      alignItems: "center",
                      flexWrap: "wrap",
                    }}
                  >
                    <span
                      style={{
                        color: "var(--text-secondary)",
                        fontSize: "13px",
                      }}
                    >
                      Wait
                    </span>
                    <input
                      type="number"
                      min="0"
                      style={{ ...inputStyle, width: "80px" }}
                      value={step.delay_value}
                      onChange={(e) =>
                        updateStep(
                          idx,
                          "delay_value",
                          parseInt(e.target.value) || 0,
                        )
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
                    <span
                      style={{ color: "var(--text-muted)", fontSize: "12px" }}
                    >
                      then send
                    </span>
                    <select
                      style={{ ...selectStyle, width: "130px" }}
                      value={step.action_type}
                      onChange={(e) =>
                        updateStep(idx, "action_type", e.target.value)
                      }
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
                      AI will generate a personalized email based on the
                      customer's conversation and your FAQ entries.
                    </div>
                  )}

                  {/* Subject */}
                  {isEmail && (
                    <input
                      id={`step-${idx}-subject_template`}
                      style={inputStyle}
                      value={step.subject_template}
                      onChange={(e) =>
                        updateStep(idx, "subject_template", e.target.value)
                      }
                      onFocus={() =>
                        setFocusedField(`step-${idx}-subject_template`)
                      }
                      placeholder="Email subject..."
                    />
                  )}

                  {/* Formatting toolbar */}
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

                  {/* Body editor + preview side by side */}
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
                      onChange={(e) =>
                        updateStep(idx, "body_template", e.target.value)
                      }
                      onFocus={() =>
                        setFocusedField(`step-${idx}-body_template`)
                      }
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
            })}
          </div>
          <button
            onClick={addStep}
            style={{ ...btnSecondary, marginTop: "12px" }}
          >
            + Add Step
          </button>
        </div>

        {/* Footer */}
        <div
          style={{
            display: "flex",
            gap: "12px",
            justifyContent: "flex-end",
            borderTop: "1px solid var(--border)",
            paddingTop: "16px",
          }}
        >
          <button onClick={onClose} style={btnSecondary}>
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !name.trim()}
            style={{ ...btnPrimary, opacity: saving || !name.trim() ? 0.5 : 1 }}
          >
            {saving
              ? "Saving..."
              : isEditing
                ? "Update Sequence"
                : "Create Sequence"}
          </button>
        </div>
      </div>
    </div>
  );
}
