import { useState, useEffect } from "react";
import { useAuth } from "../../../context/AuthContext";
import {
  fetchEmailTemplates,
  createEmailTemplate,
} from "../../../utils/api/automations";
import { TRIGGER_OPTIONS } from "./constants";
import {
  overlayStyle,
  modalStyle,
  inputStyle,
  selectStyle,
  labelStyle,
  btnPrimary,
  btnSecondary,
} from "./styles";
import { emptyStep } from "./utils";
import StepCard from "./StepCard";

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

        <div>
          <label style={labelStyle}>Sequence Name</label>
          <input
            style={inputStyle}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Welcome Email Series"
          />
        </div>

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

        <div>
          <label style={labelStyle}>Steps</label>
          <div
            style={{ display: "flex", flexDirection: "column", gap: "16px" }}
          >
            {steps.map((step, idx) => (
              <StepCard
                key={idx}
                step={step}
                idx={idx}
                steps={steps}
                previewIdx={previewIdx}
                pickerIdx={pickerIdx}
                templates={templates}
                starterTemplates={starterTemplates}
                savingTpl={savingTpl}
                tplError={tplError}
                setPreviewIdx={setPreviewIdx}
                setPickerIdx={setPickerIdx}
                setFocusedField={setFocusedField}
                updateStep={updateStep}
                removeStep={removeStep}
                handleTemplateSelect={handleTemplateSelect}
                handleSaveAsTemplate={handleSaveAsTemplate}
                insertFormat={insertFormat}
                insertAtCursor={insertAtCursor}
              />
            ))}
          </div>
          <button
            onClick={addStep}
            style={{ ...btnSecondary, marginTop: "12px" }}
          >
            + Add Step
          </button>
        </div>

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
