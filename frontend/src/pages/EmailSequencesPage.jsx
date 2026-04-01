import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import {
  fetchEmailSequences,
  createEmailSequence,
  getEmailSequence,
  updateEmailSequence,
  deleteEmailSequence,
  addEmailSequenceStep,
  updateEmailSequenceStep,
  deleteEmailSequenceStep,
  fetchEmailSequenceEnrollments,
} from "../utils/api/email-sequences";

/* ---- Constants ---- */

const TRIGGER_TYPES = [
  { key: "lead_captured", label: "Lead Captured" },
  { key: "tag_added", label: "Tag Added" },
  { key: "manual", label: "Manual" },
];

const EMAIL_TYPES = [
  { key: "email", label: "Email" },
  { key: "sms", label: "SMS" },
];

const STATUS_STYLES = {
  active: { label: "Active", color: "var(--green)", bg: "var(--green-dim)" },
  paused: { label: "Paused", color: "var(--yellow, #f59e0b)", bg: "rgba(245, 158, 11, 0.15)" },
  completed: { label: "Completed", color: "var(--text-secondary)", bg: "var(--hover-overlay)" },
  unsubscribed: { label: "Unsubscribed", color: "#f87171", bg: "rgba(248, 113, 113, 0.15)" },
};

const ENROLLMENT_STATUS_STYLES = {
  active: { label: "Active", color: "var(--green)", bg: "var(--green-dim)" },
  paused: { label: "Paused", color: "var(--yellow, #f59e0b)", bg: "rgba(245, 158, 11, 0.15)" },
  completed: { label: "Completed", color: "var(--accent)", bg: "var(--accent-dim)" },
  unsubscribed: { label: "Unsubscribed", color: "#f87171", bg: "rgba(248, 113, 113, 0.15)" },
};

/* ---- Shared styles ---- */

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

const inputStyle = {
  width: "100%",
  padding: "10px 14px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--bg-primary)",
  color: "var(--text-primary)",
  fontSize: "0.9rem",
  boxSizing: "border-box",
};

const selectStyle = {
  ...inputStyle,
  cursor: "pointer",
};

const textareaStyle = {
  ...inputStyle,
  resize: "vertical",
  minHeight: 90,
  fontFamily: "inherit",
};

const btnPrimary = {
  background: "var(--accent)",
  color: "#fff",
  border: "none",
  padding: "10px 20px",
  borderRadius: 8,
  fontWeight: 600,
  cursor: "pointer",
  fontSize: "0.9rem",
};

const btnSecondary = {
  background: "var(--bg-primary)",
  color: "var(--text-secondary)",
  border: "1px solid var(--border)",
  padding: "8px 16px",
  borderRadius: 8,
  cursor: "pointer",
  fontSize: "0.85rem",
};

const btnDanger = {
  background: "rgba(248, 113, 113, 0.12)",
  color: "#f87171",
  border: "1px solid rgba(248, 113, 113, 0.25)",
  padding: "6px 14px",
  borderRadius: 8,
  cursor: "pointer",
  fontSize: "0.82rem",
  fontWeight: 600,
};

const labelStyle = {
  display: "block",
  fontSize: "0.85rem",
  color: "var(--text-secondary)",
  marginBottom: 6,
};

const overlayStyle = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.65)",
  display: "flex",
  alignItems: "flex-start",
  justifyContent: "center",
  zIndex: 1000,
  overflowY: "auto",
  padding: "40px 16px",
};

const modalStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  borderRadius: 16,
  padding: "28px 32px",
  width: "100%",
  maxWidth: 720,
  border: "1px solid var(--border)",
  position: "relative",
};

/* ---- Helper components ---- */

function TriggerBadge({ type }) {
  const t = TRIGGER_TYPES.find((x) => x.key === type);
  const label = t?.label || type;
  const colorMap = {
    lead_captured: { color: "var(--green)", bg: "var(--green-dim)" },
    tag_added: { color: "var(--accent)", bg: "var(--accent-dim)" },
    manual: { color: "var(--text-secondary)", bg: "var(--hover-overlay)" },
  };
  const colors = colorMap[type] || colorMap.manual;
  return (
    <span style={{
      padding: "2px 10px", borderRadius: 12, fontSize: "0.75rem", fontWeight: 600,
      color: colors.color, background: colors.bg,
    }}>
      {label}
    </span>
  );
}

function StatusBadge({ status, map = ENROLLMENT_STATUS_STYLES }) {
  const s = map[status] || map.active;
  return (
    <span style={{
      padding: "2px 10px", borderRadius: 12, fontSize: "0.75rem", fontWeight: 600,
      color: s.color, background: s.bg,
    }}>
      {s.label}
    </span>
  );
}

function Toggle({ checked, onChange, label }) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
      <div
        onClick={() => onChange(!checked)}
        style={{
          width: 38, height: 20, borderRadius: 10, position: "relative", cursor: "pointer",
          background: checked ? "var(--accent)" : "var(--border)",
          transition: "background 0.2s",
          flexShrink: 0,
        }}
      >
        <div style={{
          position: "absolute", top: 3, left: checked ? 19 : 3,
          width: 14, height: 14, borderRadius: "50%", background: "#fff",
          transition: "left 0.2s",
        }} />
      </div>
      {label && <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>{label}</span>}
    </label>
  );
}

function StatCard({ label, value, color }) {
  return (
    <div style={{ ...cardStyle, flex: 1, minWidth: 140 }}>
      <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: "1.8rem", fontWeight: 700, color: color || "var(--text-primary)" }}>
        {value ?? "\u2014"}
      </div>
    </div>
  );
}

function EmptyState({ onCreateFirst }) {
  return (
    <div style={{
      ...cardStyle, textAlign: "center", padding: "56px 32px",
      color: "var(--text-secondary)",
    }}>
      <div style={{ fontSize: "2.5rem", marginBottom: 16 }}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2"
          strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.4, margin: "0 auto" }}>
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <path d="M22 6l-10 7L2 6" />
          <path d="M8 14h3M8 18h8" />
        </svg>
      </div>
      <div style={{ fontSize: "1.15rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: 8 }}>
        No email sequences yet
      </div>
      <p style={{ maxWidth: 380, margin: "0 auto 24px", lineHeight: 1.6, fontSize: "0.9rem" }}>
        Email sequences automatically send a series of emails when a trigger event fires (e.g., a new
        lead is captured). Create your first sequence to start nurturing leads on autopilot.
      </p>
      <button style={btnPrimary} onClick={onCreateFirst}>
        Create First Sequence
      </button>
    </div>
  );
}

function LoadingRows({ count = 4 }) {
  return Array.from({ length: count }).map((_, i) => (
    <tr key={i}>
      {Array.from({ length: 6 }).map((__, j) => (
        <td key={j} style={{ padding: "14px 16px" }}>
          <div style={{
            height: 14, borderRadius: 6,
            background: "var(--hover-overlay)",
            width: j === 0 ? "60%" : j === 5 ? "70%" : "40%",
            animation: "pulse 1.5s ease-in-out infinite",
          }} />
        </td>
      ))}
    </tr>
  ));
}

/* ---- Blank step factory ---- */

function blankStep(order) {
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

/* ---- Step editor row ---- */

function StepRow({ step, index, onChange, onDelete }) {
  return (
    <div style={{
      background: "var(--bg-primary)",
      border: "1px solid var(--border)",
      borderRadius: 10,
      padding: "16px 18px",
      marginBottom: 12,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
        <div style={{
          width: 28, height: 28, borderRadius: "50%",
          background: "var(--accent-dim)", color: "var(--accent)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontWeight: 700, fontSize: "0.85rem", flexShrink: 0,
        }}>
          {index + 1}
        </div>
        <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-primary)", flex: 1 }}>
          Step {index + 1}
        </span>
        <Toggle
          checked={step.is_active !== false}
          onChange={(v) => onChange({ ...step, is_active: v })}
          label="Active"
        />
        <button style={btnDanger} onClick={() => onDelete(step)}>Remove</button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 12 }}>
        <div>
          <label style={labelStyle}>Delay Days</label>
          <input
            type="number"
            min={0}
            style={inputStyle}
            value={step.delay_days}
            onChange={(e) => onChange({ ...step, delay_days: parseInt(e.target.value, 10) || 0 })}
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
            onChange={(e) => onChange({ ...step, delay_hours: parseInt(e.target.value, 10) || 0 })}
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
              <option key={t.key} value={t.key}>{t.label}</option>
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
          placeholder={step.email_type === "sms" ? "SMS message text..." : "Email body content..."}
          value={step.body}
          onChange={(e) => onChange({ ...step, body: e.target.value })}
        />
      </div>
    </div>
  );
}

/* ---- Create / Edit Modal ---- */

function SequenceModal({ sequence, tenantId, token, onClose, onSaved }) {
  const isEdit = !!sequence?.id;

  const [name, setName] = useState(sequence?.name || "");
  const [triggerType, setTriggerType] = useState(sequence?.trigger_type || "lead_captured");
  const [isActive, setIsActive] = useState(sequence?.is_active !== false);
  const [steps, setSteps] = useState(() => {
    if (sequence?.steps?.length) return sequence.steps.map((s) => ({ ...s, _localId: s.id || Math.random().toString(36).slice(2) }));
    return [blankStep(1)];
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleStepChange = (updated) => {
    setSteps((prev) => prev.map((s) => (s._localId === updated._localId ? updated : s)));
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
    if (!name.trim()) { setError("Sequence name is required."); return; }
    if (!steps.length) { setError("Add at least one step."); return; }

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
    <div style={overlayStyle} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={modalStyle}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
          <h2 style={{ margin: 0, fontSize: "1.2rem", color: "var(--text-primary)" }}>
            {isEdit ? "Edit Sequence" : "New Email Sequence"}
          </h2>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", fontSize: "1.4rem", lineHeight: 1 }}>
            &times;
          </button>
        </div>

        {error && (
          <div style={{
            background: "rgba(248,113,113,0.12)", border: "1px solid rgba(248,113,113,0.25)",
            borderRadius: 8, padding: "10px 14px", marginBottom: 20, color: "#f87171", fontSize: "0.875rem",
          }}>
            {error}
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
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
            <select style={selectStyle} value={triggerType} onChange={(e) => setTriggerType(e.target.value)}>
              {TRIGGER_TYPES.map((t) => (
                <option key={t.key} value={t.key}>{t.label}</option>
              ))}
            </select>
          </div>
          <div style={{ display: "flex", alignItems: "flex-end", paddingBottom: 2 }}>
            <Toggle checked={isActive} onChange={setIsActive} label="Active (start enrolling immediately)" />
          </div>
        </div>

        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 20, marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
            <h3 style={{ margin: 0, fontSize: "1rem", color: "var(--text-primary)" }}>
              Steps ({steps.length})
            </h3>
            <button style={btnSecondary} onClick={handleAddStep}>
              + Add Step
            </button>
          </div>

          {steps.length === 0 && (
            <div style={{ textAlign: "center", padding: "24px", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
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

        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", paddingTop: 8, borderTop: "1px solid var(--border)" }}>
          <button style={btnSecondary} onClick={onClose} disabled={saving}>Cancel</button>
          <button style={btnPrimary} onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : isEdit ? "Save Changes" : "Create Sequence"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---- Detail / Enrollments slide-over ---- */

function SequenceDetail({ sequenceId, token, onClose, onEdit }) {
  const [detail, setDetail] = useState(null);
  const [enrollments, setEnrollments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("steps");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [detailRes, enrollRes] = await Promise.all([
          getEmailSequence(sequenceId, token).catch(() => null),
          fetchEmailSequenceEnrollments(sequenceId, token).catch(() => []),
        ]);
        setDetail(detailRes);
        setEnrollments(enrollRes?.enrollments || enrollRes || []);
      } catch {
        // non-critical, leave as empty
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [sequenceId, token]);

  const tabStyle = (active) => ({
    padding: "8px 18px",
    borderRadius: 8,
    border: "none",
    cursor: "pointer",
    fontWeight: 600,
    fontSize: "0.85rem",
    background: active ? "var(--accent-dim)" : "transparent",
    color: active ? "var(--accent)" : "var(--text-secondary)",
  });

  return (
    <div style={overlayStyle} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ ...modalStyle, maxWidth: 760 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <h2 style={{ margin: 0, fontSize: "1.15rem", color: "var(--text-primary)" }}>
            {loading ? "Loading..." : detail?.name || "Sequence Detail"}
          </h2>
          <div style={{ display: "flex", gap: 8 }}>
            <button style={btnSecondary} onClick={onEdit}>Edit</button>
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", fontSize: "1.4rem", lineHeight: 1 }}>
              &times;
            </button>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: 40, color: "var(--text-secondary)" }}>Loading sequence details...</div>
        ) : !detail ? (
          <div style={{ textAlign: "center", padding: 40, color: "var(--text-secondary)" }}>Could not load sequence details.</div>
        ) : (
          <>
            <div style={{ display: "flex", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
              <div style={{ ...cardStyle, padding: "12px 18px", flex: "none" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: 4 }}>Trigger</div>
                <TriggerBadge type={detail.trigger_type} />
              </div>
              <div style={{ ...cardStyle, padding: "12px 18px", flex: "none" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: 4 }}>Steps</div>
                <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>{detail.step_count ?? (detail.steps?.length ?? 0)}</span>
              </div>
              <div style={{ ...cardStyle, padding: "12px 18px", flex: "none" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: 4 }}>Enrollments</div>
                <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>{detail.enrollment_count ?? enrollments.length}</span>
              </div>
              <div style={{ ...cardStyle, padding: "12px 18px", flex: "none" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: 4 }}>Status</div>
                <span style={{ fontWeight: 700, color: detail.is_active ? "var(--green)" : "var(--text-secondary)" }}>
                  {detail.is_active ? "Active" : "Paused"}
                </span>
              </div>
            </div>

            <div style={{ display: "flex", gap: 4, marginBottom: 20, borderBottom: "1px solid var(--border)", paddingBottom: 12 }}>
              <button style={tabStyle(activeTab === "steps")} onClick={() => setActiveTab("steps")}>Steps</button>
              <button style={tabStyle(activeTab === "enrollments")} onClick={() => setActiveTab("enrollments")}>
                Enrollments ({enrollments.length})
              </button>
            </div>

            {activeTab === "steps" && (
              <div>
                {(!detail.steps || detail.steps.length === 0) ? (
                  <div style={{ textAlign: "center", padding: "32px", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                    No steps configured. Click Edit to add steps.
                  </div>
                ) : (
                  detail.steps.map((step, i) => (
                    <div key={step.id || i} style={{
                      background: "var(--bg-primary)", border: "1px solid var(--border)",
                      borderRadius: 10, padding: "14px 18px", marginBottom: 10,
                    }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                        <div style={{
                          width: 26, height: 26, borderRadius: "50%",
                          background: "var(--accent-dim)", color: "var(--accent)",
                          display: "flex", alignItems: "center", justifyContent: "center",
                          fontWeight: 700, fontSize: "0.8rem", flexShrink: 0,
                        }}>
                          {i + 1}
                        </div>
                        <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-primary)", flex: 1 }}>
                          {step.email_type === "sms" ? "SMS" : "Email"} — Step {i + 1}
                        </span>
                        <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                          Delay: {step.delay_days || 0}d {step.delay_hours || 0}h
                        </span>
                        <span style={{
                          padding: "2px 8px", borderRadius: 10, fontSize: "0.72rem", fontWeight: 600,
                          background: step.is_active !== false ? "var(--green-dim)" : "var(--hover-overlay)",
                          color: step.is_active !== false ? "var(--green)" : "var(--text-secondary)",
                        }}>
                          {step.is_active !== false ? "Active" : "Inactive"}
                        </span>
                      </div>
                      {step.subject && (
                        <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 6 }}>
                          <strong style={{ color: "var(--text-primary)" }}>Subject:</strong> {step.subject}
                        </div>
                      )}
                      {step.body && (
                        <div style={{
                          fontSize: "0.82rem", color: "var(--text-secondary)",
                          background: "var(--bg-secondary)", borderRadius: 6,
                          padding: "8px 12px", whiteSpace: "pre-wrap", maxHeight: 100, overflowY: "auto",
                        }}>
                          {step.body}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === "enrollments" && (
              <div>
                {enrollments.length === 0 ? (
                  <div style={{ textAlign: "center", padding: "32px", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                    No leads enrolled yet. Leads are enrolled automatically when the trigger fires, or manually from the Clients page.
                  </div>
                ) : (
                  <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ borderBottom: "1px solid var(--border)" }}>
                          {["Lead", "Email", "Status", "Step", "Enrolled"].map((h) => (
                            <th key={h} style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.78rem", color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {enrollments.map((e) => (
                          <tr key={e.id} style={{ borderBottom: "1px solid var(--border)" }}>
                            <td style={{ padding: "12px", fontSize: "0.875rem", color: "var(--text-primary)", fontWeight: 500 }}>
                              {e.lead_name || "\u2014"}
                            </td>
                            <td style={{ padding: "12px", fontSize: "0.875rem", color: "var(--text-secondary)" }}>
                              {e.lead_email || "\u2014"}
                            </td>
                            <td style={{ padding: "12px" }}>
                              <StatusBadge status={e.status} />
                            </td>
                            <td style={{ padding: "12px", fontSize: "0.875rem", color: "var(--text-secondary)" }}>
                              Step {e.current_step ?? "\u2014"}
                            </td>
                            <td style={{ padding: "12px", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                              {e.enrolled_at ? new Date(e.enrolled_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "\u2014"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/* ---- Main Component ---- */

export default function EmailSequencesPage() {
  const { user, token } = useAuth();

  const [sequences, setSequences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal state
  const [showCreate, setShowCreate] = useState(false);
  const [editSequence, setEditSequence] = useState(null);
  const [detailSequenceId, setDetailSequenceId] = useState(null);

  /* ---- Load list ---- */

  const loadSequences = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchEmailSequences(user.tenantId, token);
      setSequences(res?.sequences || res || []);
    } catch (e) {
      setError(e.message || "Failed to load sequences.");
      setSequences([]);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => { loadSequences(); }, [loadSequences]);

  /* ---- Toggle active ---- */

  const handleToggleActive = async (seq) => {
    try {
      await updateEmailSequence(seq.id, token, { is_active: !seq.is_active });
      setSequences((prev) => prev.map((s) => s.id === seq.id ? { ...s, is_active: !s.is_active } : s));
    } catch (e) {
      alert("Failed to update: " + (e.message || "Unknown error"));
    }
  };

  /* ---- Delete ---- */

  const handleDelete = async (seq) => {
    if (!confirm(`Delete "${seq.name}"? This will stop all active enrollments.`)) return;
    try {
      await deleteEmailSequence(seq.id, token);
      setSequences((prev) => prev.filter((s) => s.id !== seq.id));
    } catch (e) {
      alert("Failed to delete: " + (e.message || "Unknown error"));
    }
  };

  /* ---- Stat calculations ---- */

  const totalActive = sequences.filter((s) => s.is_active).length;
  const totalEnrollments = sequences.reduce((acc, s) => acc + (s.enrollment_count || 0), 0);

  /* ---- Render ---- */

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1100, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 28 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)" }}>
            Email Sequences
          </h1>
          <p style={{ margin: "4px 0 0", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
            Automated drip email series triggered by lead events
          </p>
        </div>
        <button style={btnPrimary} onClick={() => setShowCreate(true)}>
          + New Sequence
        </button>
      </div>

      {/* Stat cards */}
      <div style={{ display: "flex", gap: 16, marginBottom: 28, flexWrap: "wrap" }}>
        <StatCard label="Total Sequences" value={loading ? "..." : sequences.length} />
        <StatCard label="Active Sequences" value={loading ? "..." : totalActive} color="var(--green)" />
        <StatCard label="Total Enrollments" value={loading ? "..." : totalEnrollments} color="var(--accent)" />
      </div>

      {/* Error state */}
      {error && (
        <div style={{
          background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.2)",
          borderRadius: 10, padding: "14px 18px", marginBottom: 20, color: "#f87171", fontSize: "0.875rem",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <span>{error}</span>
          <button style={{ ...btnSecondary, fontSize: "0.8rem" }} onClick={loadSequences}>Retry</button>
        </div>
      )}

      {/* Sequences table / empty state */}
      {!loading && sequences.length === 0 && !error ? (
        <EmptyState onCreateFirst={() => setShowCreate(true)} />
      ) : (
        <div style={cardStyle}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Name", "Trigger", "Active", "Steps", "Enrollments", "Created", "Actions"].map((h) => (
                    <th key={h} style={{
                      padding: "10px 16px", textAlign: "left",
                      fontSize: "0.78rem", color: "var(--text-secondary)",
                      fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em",
                      whiteSpace: "nowrap",
                    }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <LoadingRows count={4} />
                ) : (
                  sequences.map((seq) => (
                    <tr
                      key={seq.id}
                      style={{ borderBottom: "1px solid var(--border)", transition: "background 0.15s" }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = "var(--hover-overlay)"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                    >
                      <td style={{ padding: "14px 16px" }}>
                        <button
                          onClick={() => setDetailSequenceId(seq.id)}
                          style={{
                            background: "none", border: "none", cursor: "pointer",
                            color: "var(--text-primary)", fontWeight: 600, fontSize: "0.9rem",
                            textAlign: "left", padding: 0,
                          }}
                        >
                          {seq.name}
                        </button>
                      </td>
                      <td style={{ padding: "14px 16px" }}>
                        <TriggerBadge type={seq.trigger_type} />
                      </td>
                      <td style={{ padding: "14px 16px" }}>
                        <Toggle
                          checked={seq.is_active}
                          onChange={() => handleToggleActive(seq)}
                        />
                      </td>
                      <td style={{ padding: "14px 16px", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                        {seq.step_count ?? "\u2014"}
                      </td>
                      <td style={{ padding: "14px 16px", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                        {seq.enrollment_count ?? 0}
                      </td>
                      <td style={{ padding: "14px 16px", color: "var(--text-secondary)", fontSize: "0.8rem", whiteSpace: "nowrap" }}>
                        {seq.created_at
                          ? new Date(seq.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
                          : "\u2014"}
                      </td>
                      <td style={{ padding: "14px 16px" }}>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button
                            style={btnSecondary}
                            onClick={() => setEditSequence(seq)}
                          >
                            Edit
                          </button>
                          <button
                            style={btnDanger}
                            onClick={() => handleDelete(seq)}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <SequenceModal
          sequence={null}
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setShowCreate(false)}
          onSaved={() => {
            setShowCreate(false);
            loadSequences();
          }}
        />
      )}

      {/* Edit modal */}
      {editSequence && (
        <SequenceModal
          sequence={editSequence}
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setEditSequence(null)}
          onSaved={() => {
            setEditSequence(null);
            loadSequences();
          }}
        />
      )}

      {/* Detail view */}
      {detailSequenceId && (
        <SequenceDetail
          sequenceId={detailSequenceId}
          token={token}
          onClose={() => setDetailSequenceId(null)}
          onEdit={() => {
            const seq = sequences.find((s) => s.id === detailSequenceId);
            if (seq) {
              setDetailSequenceId(null);
              setEditSequence(seq);
            }
          }}
        />
      )}
    </div>
  );
}
