import { useState } from "react";
import {
  createEmailSequence,
  updateEmailSequence,
} from "../../utils/api/email-sequences";
import { TRIGGER_TYPES } from "./constants";
import {
  inputStyle,
  selectStyle,
  btnPrimary,
  btnSecondary,
  labelStyle,
  overlayStyle,
  modalStyle,
} from "./styles";
import { Toggle } from "./badges";
import { blankStep, StepRow } from "./StepRow";

export function SequenceModal({ sequence, tenantId, token, onClose, onSaved }) {
  const isEdit = !!sequence?.id;

  const [name, setName] = useState(sequence?.name || "");
  const [triggerType, setTriggerType] = useState(
    sequence?.trigger_type || "lead_captured",
  );
  const [isActive, setIsActive] = useState(sequence?.is_active !== false);
  const [steps, setSteps] = useState(() => {
    if (sequence?.steps?.length)
      return sequence.steps.map((s) => ({
        ...s,
        _localId: s.id || Math.random().toString(36).slice(2),
      }));
    return [blankStep(1)];
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleStepChange = (updated) => {
    setSteps((prev) =>
      prev.map((s) => (s._localId === updated._localId ? updated : s)),
    );
  };

  const handleStepDelete = (target) => {
    setSteps((prev) => {
      const filtered = prev.filter((s) => s._localId !== target._localId);
      return filtered.map((s, i) => ({ ...s, step_order: i + 1 }));
    });
  };

  const handleAddStep = () => {
    setSteps((prev) => [...prev, blankStep(prev.length + 1)]);
  };

  const handleSave = async () => {
    if (!name.trim()) {
      setError("Sequence name is required.");
      return;
    }
    if (!steps.length) {
      setError("Add at least one step.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const payload = {
        name: name.trim(),
        trigger_type: triggerType,
        is_active: isActive,
        steps: steps.map((s, i) => ({
          step_order: i + 1,
          delay_days: s.delay_days || 0,
          delay_hours: s.delay_hours || 0,
          subject: s.subject || "",
          body: s.body || "",
          email_type: s.email_type || "email",
          is_active: s.is_active !== false,
        })),
      };

      if (isEdit) {
        await updateEmailSequence(sequence.id, token, payload);
      } else {
        await createEmailSequence(tenantId, token, payload);
      }
      onSaved();
    } catch (e) {
      setError(e.message || "Failed to save sequence.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={overlayStyle}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div style={modalStyle}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 24,
          }}
        >
          <h2
            style={{
              margin: 0,
              fontSize: "1.2rem",
              color: "var(--text-primary)",
            }}
          >
            {isEdit ? "Edit Sequence" : "New Email Sequence"}
          </h2>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--text-secondary)",
              fontSize: "1.4rem",
              lineHeight: 1,
            }}
          >
            &times;
          </button>
        </div>

        {error && (
          <div
            style={{
              background: "rgba(248,113,113,0.12)",
              border: "1px solid rgba(248,113,113,0.25)",
              borderRadius: 8,
              padding: "10px 14px",
              marginBottom: 20,
              color: "#f87171",
              fontSize: "0.875rem",
            }}
          >
            {error}
          </div>
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 16,
            marginBottom: 16,
          }}
        >
          <div style={{ gridColumn: "1 / -1" }}>
            <label style={labelStyle}>Sequence Name</label>
            <input
              type="text"
              style={inputStyle}
              placeholder="e.g., New Lead Welcome Series"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label style={labelStyle}>Trigger Type</label>
            <select
              style={selectStyle}
              value={triggerType}
              onChange={(e) => setTriggerType(e.target.value)}
            >
              {TRIGGER_TYPES.map((t) => (
                <option key={t.key} value={t.key}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "flex-end",
              paddingBottom: 2,
            }}
          >
            <Toggle
              checked={isActive}
              onChange={setIsActive}
              label="Active (start enrolling immediately)"
            />
          </div>
        </div>

        <div
          style={{
            borderTop: "1px solid var(--border)",
            paddingTop: 20,
            marginBottom: 16,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 14,
            }}
          >
            <h3
              style={{
                margin: 0,
                fontSize: "1rem",
                color: "var(--text-primary)",
              }}
            >
              Steps ({steps.length})
            </h3>
            <button style={btnSecondary} onClick={handleAddStep}>
              + Add Step
            </button>
          </div>

          {steps.length === 0 && (
            <div
              style={{
                textAlign: "center",
                padding: "24px",
                color: "var(--text-secondary)",
                fontSize: "0.875rem",
              }}
            >
              No steps yet. Click "Add Step" to build your sequence.
            </div>
          )}

          {steps.map((step, i) => (
            <StepRow
              key={step._localId}
              step={step}
              index={i}
              onChange={handleStepChange}
              onDelete={handleStepDelete}
            />
          ))}

          {steps.length > 0 && (
            <button
              style={{ ...btnSecondary, width: "100%", marginTop: 4 }}
              onClick={handleAddStep}
            >
              + Add Another Step
            </button>
          )}
        </div>

        <div
          style={{
            display: "flex",
            gap: 12,
            justifyContent: "flex-end",
            paddingTop: 8,
            borderTop: "1px solid var(--border)",
          }}
        >
          <button style={btnSecondary} onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button style={btnPrimary} onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : isEdit ? "Save Changes" : "Create Sequence"}
          </button>
        </div>
      </div>
    </div>
  );
}
