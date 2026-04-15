import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { BASE } from "../utils/api/_client";
import SkeletonLoader from "../components/SkeletonLoader";
import { notify } from "../utils/notify";

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

const labelStyle = {
  display: "block",
  fontSize: "0.85rem",
  color: "var(--text-secondary)",
  marginBottom: 6,
};

const overlayStyle = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
};

const modalStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  borderRadius: 16,
  padding: "28px 32px",
  width: "90%",
  maxWidth: 800,
  maxHeight: "90vh",
  overflowY: "auto",
  border: "1px solid var(--border)",
};

const TRIGGER_TYPES = [
  {
    key: "lead_captured",
    label: "Lead Captured",
    desc: "When a new lead is created",
    icon: "\ud83d\udc64",
  },
  {
    key: "tag_added",
    label: "Tag Added",
    desc: "When a specific tag is added to a lead",
    icon: "\ud83c\udff4",
  },
  {
    key: "tag_removed",
    label: "Tag Removed",
    desc: "When a tag is removed from a lead",
    icon: "\ud83d\udd8d",
  },
  {
    key: "form_submitted",
    label: "Form Submitted",
    desc: "When a lead submits a form",
    icon: "\ud83d\udccd",
  },
  {
    key: "appointment_created",
    label: "Appointment Created",
    desc: "When a new appointment is booked",
    icon: "\ud83d\udcc5",
  },
  {
    key: "appointment_completed",
    label: "Appointment Completed",
    desc: "When an appointment is completed",
    icon: "\u2705",
  },
  {
    key: "pipeline_stage_changed",
    label: "Pipeline Stage Changed",
    desc: "When a lead moves between pipeline stages",
    icon: "\u2699\ufe0f",
  },
  {
    key: "lead_score_threshold",
    label: "Lead Score Threshold",
    desc: "When a lead's score crosses a threshold",
    icon: "\ud83d\udcca",
  },
  {
    key: "email_opened",
    label: "Email Opened",
    desc: "When a lead opens a specific email",
    icon: "\ud83d\udce7",
  },
  {
    key: "email_clicked",
    label: "Email Clicked",
    desc: "When a lead clicks a link in an email",
    icon: "\ud83d\udcbb",
  },
  {
    key: "scheduled_daily",
    label: "Scheduled Daily",
    desc: "Runs on a set schedule each day",
    icon: "\u23f0",
  },
  {
    key: "scheduled_weekly",
    label: "Scheduled Weekly",
    desc: "Runs once per week on a specific day",
    icon: "\ud83d\udcc6",
  },
  {
    key: "smart_list_matched",
    label: "Smart List Matched",
    desc: "When a lead enters a smart list",
    icon: "\ud83d\udcbc",
  },
];

const ACTION_TYPES = [
  { key: "send_email", label: "Send Email" },
  { key: "add_tag", label: "Add Tag" },
  { key: "remove_tag", label: "Remove Tag" },
  { key: "update_lead_status", label: "Update Lead Status" },
  { key: "enroll_in_sequence", label: "Enroll in Sequence" },
  { key: "create_task", label: "Create Task" },
  { key: "notify_team", label: "Notify Team" },
  { key: "send_campaign", label: "Send Campaign" },
  { key: "update_lead_score", label: "Update Lead Score" },
];

const CONDITION_OPERATORS = [
  "equals",
  "not_equals",
  "contains",
  "not_contains",
  "greater_than",
  "less_than",
  "is_empty",
  "is_not_empty",
];

const API_BASE = `${BASE}/api/v1`;

async function apiFetch(path, token, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...opts.headers,
    },
    ...opts,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

function TriggerIcon({ triggerType }) {
  const t = TRIGGER_TYPES.find((t) => t.key === triggerType);
  return <span style={{ fontSize: "1rem" }}>{t?.icon || "\u26a1"}</span>;
}

function formatDate(d) {
  if (!d) return "\u2014";
  return new Date(d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function RuleModal({ rule, tenantId, token, onClose, onSaved }) {
  const [name, setName] = useState(rule?.name || "");
  const [description, setDescription] = useState(rule?.description || "");
  const [triggerType, setTriggerType] = useState(
    rule?.trigger_type || "lead_captured",
  );
  const [triggerConfig, setTriggerConfig] = useState(
    rule?.trigger_config || {},
  );
  const [conditions, setConditions] = useState(rule?.conditions || []);
  const [actions, setActions] = useState(rule?.actions || []);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const isEditing = !!rule?.id;

  const addCondition = () =>
    setConditions((prev) => [
      ...prev,
      { field: "", operator: "equals", value: "" },
    ]);
  const removeCondition = (idx) =>
    setConditions((prev) => prev.filter((_, i) => i !== idx));
  const updateCondition = (idx, field, value) =>
    setConditions((prev) =>
      prev.map((c, i) => (i === idx ? { ...c, [field]: value } : c)),
    );

  const addAction = () =>
    setActions((prev) => [...prev, { type: "send_email", config: {} }]);
  const removeAction = (idx) =>
    setActions((prev) => prev.filter((_, i) => i !== idx));
  const updateAction = (idx, field, value) =>
    setActions((prev) =>
      prev.map((a, i) =>
        i === idx
          ? {
              ...a,
              [field]: field === "type" ? value : a.type,
              config: field === "type" ? {} : a.config,
              [field]: value,
            }
          : a,
      ),
    );
  const updateActionConfig = (idx, key, value) =>
    setActions((prev) =>
      prev.map((a, i) =>
        i === idx ? { ...a, config: { ...a.config, [key]: value } } : a,
      ),
    );

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError("Rule name is required");
      return;
    }
    if (!triggerType) {
      setError("Trigger type is required");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        name: name.trim(),
        description: description.trim(),
        trigger_type: triggerType,
        trigger_config: triggerConfig,
        conditions,
        actions,
      };
      if (isEditing) {
        await apiFetch(`/automation-rules/${tenantId}/${rule.id}`, token, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch(`/automation-rules/${tenantId}`, token, {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      onSaved();
    } catch (e) {
      setError(e.message || "Failed to save rule");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={modalStyle}>
        <h2
          style={{
            margin: "0 0 20px",
            color: "var(--text-primary)",
            fontSize: "1.2rem",
          }}
        >
          {isEditing ? "Edit Automation Rule" : "Create Automation Rule"}
        </h2>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Rule Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Follow up hot leads"
            style={inputStyle}
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Description (optional)</label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this rule do?"
            style={inputStyle}
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Trigger Type</label>
          <select
            value={triggerType}
            onChange={(e) => setTriggerType(e.target.value)}
            style={inputStyle}
          >
            {TRIGGER_TYPES.map((t) => (
              <option key={t.key} value={t.key}>
                {t.icon} {t.label}
              </option>
            ))}
          </select>
          {TRIGGER_TYPES.find((t) => t.key === triggerType) && (
            <div
              style={{
                fontSize: "0.8rem",
                color: "var(--text-muted)",
                marginTop: 4,
              }}
            >
              {TRIGGER_TYPES.find((t) => t.key === triggerType).desc}
            </div>
          )}
        </div>

        {triggerType === "tag_added" || triggerType === "tag_removed" ? (
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>Tag Name</label>
            <input
              type="text"
              value={triggerConfig.tag || ""}
              onChange={(e) => setTriggerConfig({ tag: e.target.value })}
              placeholder="e.g., VIP"
              style={inputStyle}
            />
          </div>
        ) : null}

        {/* Conditions */}
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <label style={{ ...labelStyle, margin: 0 }}>
              Conditions (AND logic)
            </label>
            <button
              onClick={addCondition}
              style={{
                ...btnSecondary,
                padding: "4px 12px",
                fontSize: "0.8rem",
              }}
            >
              + Add Condition
            </button>
          </div>
          {conditions.map((c, idx) => (
            <div
              key={idx}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1fr auto",
                gap: 8,
                marginBottom: 8,
                alignItems: "center",
              }}
            >
              <input
                type="text"
                value={c.field}
                onChange={(e) => updateCondition(idx, "field", e.target.value)}
                placeholder="Field (e.g., lead.status)"
                style={inputStyle}
              />
              <select
                value={c.operator}
                onChange={(e) =>
                  updateCondition(idx, "operator", e.target.value)
                }
                style={inputStyle}
              >
                {CONDITION_OPERATORS.map((op) => (
                  <option key={op} value={op}>
                    {op.replace("_", " ")}
                  </option>
                ))}
              </select>
              <input
                type="text"
                value={c.value}
                onChange={(e) => updateCondition(idx, "value", e.target.value)}
                placeholder="Value"
                style={inputStyle}
              />
              <button
                onClick={() => removeCondition(idx)}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                }}
              >
                \u2715
              </button>
            </div>
          ))}
          {conditions.length === 0 && (
            <div
              style={{
                fontSize: "0.85rem",
                color: "var(--text-muted)",
                padding: "8px 0",
              }}
            >
              No conditions — rule will trigger for all matching events
            </div>
          )}
        </div>

        {/* Actions */}
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <label style={{ ...labelStyle, margin: 0 }}>Actions</label>
            <button
              onClick={addAction}
              style={{
                ...btnSecondary,
                padding: "4px 12px",
                fontSize: "0.8rem",
              }}
            >
              + Add Action
            </button>
          </div>
          {actions.map((a, idx) => (
            <div
              key={idx}
              style={{
                background: "var(--bg-primary)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: 12,
                marginBottom: 8,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 8,
                }}
              >
                <select
                  value={a.type}
                  onChange={(e) => updateAction(idx, "type", e.target.value)}
                  style={{ ...inputStyle, width: "auto" }}
                >
                  {ACTION_TYPES.map((at) => (
                    <option key={at.key} value={at.key}>
                      {at.label}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => removeAction(idx)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                  }}
                >
                  \u2715
                </button>
              </div>
              {a.type === "send_email" && (
                <>
                  <input
                    type="text"
                    value={a.config?.subject || ""}
                    onChange={(e) =>
                      updateActionConfig(idx, "subject", e.target.value)
                    }
                    placeholder="Subject"
                    style={{ ...inputStyle, marginBottom: 6 }}
                  />
                  <textarea
                    value={a.config?.body || ""}
                    onChange={(e) =>
                      updateActionConfig(idx, "body", e.target.value)
                    }
                    placeholder="Email body"
                    rows={2}
                    style={{ ...inputStyle, resize: "vertical" }}
                  />
                </>
              )}
              {(a.type === "add_tag" || a.type === "remove_tag") && (
                <input
                  type="text"
                  value={a.config?.tag || ""}
                  onChange={(e) =>
                    updateActionConfig(idx, "tag", e.target.value)
                  }
                  placeholder="Tag name"
                  style={inputStyle}
                />
              )}
              {a.type === "update_lead_status" && (
                <input
                  type="text"
                  value={a.config?.status || ""}
                  onChange={(e) =>
                    updateActionConfig(idx, "status", e.target.value)
                  }
                  placeholder="New status (e.g., contacted)"
                  style={inputStyle}
                />
              )}
              {a.type === "create_task" && (
                <>
                  <input
                    type="text"
                    value={a.config?.description || ""}
                    onChange={(e) =>
                      updateActionConfig(idx, "description", e.target.value)
                    }
                    placeholder="Task description"
                    style={{ ...inputStyle, marginBottom: 6 }}
                  />
                  <input
                    type="text"
                    value={a.config?.priority || ""}
                    onChange={(e) =>
                      updateActionConfig(idx, "priority", e.target.value)
                    }
                    placeholder="Priority (low/normal/high)"
                    style={inputStyle}
                  />
                </>
              )}
              {a.type === "notify_team" && (
                <input
                  type="text"
                  value={a.config?.message || ""}
                  onChange={(e) =>
                    updateActionConfig(idx, "message", e.target.value)
                  }
                  placeholder="Notification message"
                  style={inputStyle}
                />
              )}
              {a.type === "update_lead_score" && (
                <input
                  type="number"
                  value={a.config?.delta || ""}
                  onChange={(e) =>
                    updateActionConfig(
                      idx,
                      "delta",
                      parseInt(e.target.value) || 0,
                    )
                  }
                  placeholder="Score change (e.g., +10 or -5)"
                  style={inputStyle}
                />
              )}
            </div>
          ))}
          {actions.length === 0 && (
            <div
              style={{
                fontSize: "0.85rem",
                color: "var(--text-muted)",
                padding: "8px 0",
              }}
            >
              At least one action is required
            </div>
          )}
        </div>

        {error && (
          <div
            style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 12 }}
          >
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={btnSecondary}>
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            style={{ ...btnPrimary, opacity: submitting ? 0.6 : 1 }}
          >
            {submitting
              ? "Saving..."
              : isEditing
                ? "Save Changes"
                : "Create Rule"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AutomationRulesPage() {
  const { user, token } = useAuth();
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editingRule, setEditingRule] = useState(null);

  const loadRules = useCallback(async () => {
    if (!user?.tenantId || !token) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/automation-rules/${user.tenantId}`, token);
      setRules(Array.isArray(res) ? res : (res.automation_rules || res.rules || []));
    } catch {
      setRules([]);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  const handleToggle = async (rule) => {
    try {
      await apiFetch(
        `/automation-rules/${user.tenantId}/${rule.id}/toggle`,
        token,
        { method: "POST" },
      );
      setRules((prev) =>
        prev.map((r) =>
          r.id === rule.id ? { ...r, is_active: !r.is_active } : r,
        ),
      );
    } catch (e) {
      notify.error("Failed to toggle rule: " + (e.message || "Unknown error"));
    }
  };

  const handleDelete = async (ruleId) => {
    if (!confirm("Delete this automation rule?")) return;
    try {
      await apiFetch(`/automation-rules/${user.tenantId}/${ruleId}`, token, {
        method: "DELETE",
      });
      setRules((prev) => prev.filter((r) => r.id !== ruleId));
    } catch (e) {
      notify.error("Failed to delete: " + (e.message || "Unknown error"));
    }
  };

  if (loading && rules.length === 0) return <SkeletonLoader />;

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1200 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 24,
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              margin: 0,
              color: "var(--text-primary)",
            }}
          >
            Automation Rules
          </h1>
          <p
            style={{
              color: "var(--text-secondary)",
              margin: "4px 0 0",
              fontSize: "0.9rem",
            }}
          >
            Event-driven automations with triggers, conditions, and actions
          </p>
        </div>
        <button onClick={() => setShowCreate(true)} style={btnPrimary}>
          + Create Rule
        </button>
      </div>

      {/* Stats Row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 16,
          marginBottom: 24,
        }}
      >
        {[
          { label: "Total Rules", value: rules.length },
          { label: "Active", value: rules.filter((r) => r.is_active).length },
          {
            label: "Total Executions",
            value: rules.reduce((s, r) => s + (r.triggered_count || 0), 0),
          },
        ].map((s) => (
          <div key={s.label} style={cardStyle}>
            <div
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                marginBottom: 4,
              }}
            >
              {s.label}
            </div>
            <div
              style={{
                fontSize: "1.5rem",
                fontWeight: 700,
                color: "var(--accent)",
              }}
            >
              {s.value}
            </div>
          </div>
        ))}
      </div>

      {/* Rules List */}
      {rules.length === 0 ? (
        <div
          style={{ ...cardStyle, textAlign: "center", padding: "60px 20px" }}
        >
          <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>\u26a1</div>
          <h3 style={{ margin: "0 0 8px", color: "var(--text-primary)" }}>
            No automation rules yet
          </h3>
          <p style={{ color: "var(--text-secondary)", margin: "0 0 16px" }}>
            Create rules to automate actions based on lead events
          </p>
          <button onClick={() => setShowCreate(true)} style={btnPrimary}>
            + Create Rule
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {rules.map((rule) => {
            const trigger = TRIGGER_TYPES.find(
              (t) => t.key === rule.trigger_type,
            );
            return (
              <div
                key={rule.id}
                style={{
                  ...cardStyle,
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  opacity: rule.is_active ? 1 : 0.65,
                }}
              >
                <div style={{ fontSize: "1.4rem", flexShrink: 0 }}>
                  {trigger?.icon || "\u26a1"}
                </div>
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontWeight: 600,
                      color: "var(--text-primary)",
                      marginBottom: 2,
                    }}
                  >
                    {rule.name}
                    {rule.description && (
                      <span
                        style={{
                          fontWeight: 400,
                          color: "var(--text-secondary)",
                          marginLeft: 8,
                          fontSize: "0.85rem",
                        }}
                      >
                        — {rule.description}
                      </span>
                    )}
                  </div>
                  <div
                    style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}
                  >
                    <span style={{ color: "var(--accent)" }}>
                      {trigger?.label || rule.trigger_type}
                    </span>
                    {rule.conditions?.length > 0 && (
                      <span>
                        {" "}
                        with {rule.conditions.length} condition
                        {rule.conditions.length > 1 ? "s" : ""}
                      </span>
                    )}
                    {" · "}
                    {rule.actions?.length || 0} action
                    {(rule.actions?.length || 0) !== 1 ? "s" : ""}
                  </div>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 16,
                    flexShrink: 0,
                  }}
                >
                  <div
                    style={{
                      textAlign: "right",
                      fontSize: "0.8rem",
                      color: "var(--text-muted)",
                    }}
                  >
                    <div>
                      Last triggered: {formatDate(rule.last_triggered_at)}
                    </div>
                    <div>Executions: {rule.triggered_count || 0}</div>
                  </div>
                  <button
                    onClick={() => handleToggle(rule)}
                    style={{
                      width: 44,
                      height: 24,
                      borderRadius: 12,
                      cursor: "pointer",
                      border: "none",
                      position: "relative",
                      transition: "background 0.2s",
                      background: rule.is_active
                        ? "var(--green)"
                        : "var(--hover-overlay)",
                    }}
                  >
                    <div
                      style={{
                        width: 18,
                        height: 18,
                        borderRadius: "50%",
                        background: "#fff",
                        position: "absolute",
                        top: 3,
                        left: rule.is_active ? 23 : 3,
                        transition: "left 0.2s",
                      }}
                    />
                  </button>
                  <button
                    onClick={() => setEditingRule(rule)}
                    style={{
                      ...btnSecondary,
                      padding: "4px 12px",
                      fontSize: "0.8rem",
                    }}
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(rule.id)}
                    style={{
                      background: "none",
                      border: "1px solid var(--border)",
                      color: "var(--text-muted)",
                      padding: "4px 10px",
                      borderRadius: 6,
                      cursor: "pointer",
                      fontSize: "0.8rem",
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modals */}
      {showCreate && (
        <RuleModal
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setShowCreate(false)}
          onSaved={() => {
            setShowCreate(false);
            loadRules();
          }}
        />
      )}
      {editingRule && (
        <RuleModal
          rule={editingRule}
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setEditingRule(null)}
          onSaved={() => {
            setEditingRule(null);
            loadRules();
          }}
        />
      )}
    </div>
  );
}
