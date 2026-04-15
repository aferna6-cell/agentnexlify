import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { notify } from "../utils/notify";
import {
  fetchPipelineAutomations,
  createPipelineAutomation,
  updatePipelineAutomation,
  deletePipelineAutomation,
  fetchPipelineStages,
} from "../utils/api";
import SkeletonLoader from "../components/SkeletonLoader";

const ACTION_TYPES = [
  { value: "email", label: "Send Email", icon: "\u2709" },
  { value: "create_task", label: "Create Task", icon: "\u2611" },
  { value: "notify_team", label: "Notify Team", icon: "\uD83D\uDD14" },
];

function emptyAction(type = "email") {
  if (type === "email") return { type: "email", subject: "", body: "" };
  if (type === "create_task") return { type: "create_task", description: "" };
  return { type: "notify_team", message: "" };
}

export default function PipelineAutomationsPage({ onNavigate }) {
  const { user, token } = useAuth();
  const tenantId = user?.tenantId;

  const [automations, setAutomations] = useState([]);
  const [stages, setStages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null); // null = create, object = edit
  const [form, setForm] = useState({ name: "", trigger_stage: "", actions: [emptyAction()], is_active: true });
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  const loadData = useCallback(async () => {
    if (!tenantId || !token) return;
    setLoading(true);
    setError(null);
    try {
      const [autoRes, stageRes] = await Promise.all([
        fetchPipelineAutomations(tenantId, token),
        fetchPipelineStages(tenantId, token),
      ]);
      setAutomations(autoRes.automations || []);
      setStages(stageRes.stages || stageRes || []);
    } catch (err) {
      setError(err.message || "Failed to load pipeline automations");
    } finally {
      setLoading(false);
    }
  }, [tenantId, token]);

  useEffect(() => { loadData(); }, [loadData]);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: "", trigger_stage: "", actions: [emptyAction()], is_active: true });
    setShowModal(true);
  };

  const openEdit = (auto) => {
    setEditing(auto);
    setForm({
      name: auto.name || "",
      trigger_stage: auto.trigger_stage || "",
      actions: (auto.actions || []).map((a) => ({ ...a })),
      is_active: auto.is_active !== false,
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.name.trim() || !form.trigger_stage) return;
    if (form.actions.length === 0) return;
    setSaving(true);
    try {
      if (editing) {
        await updatePipelineAutomation(tenantId, token, editing.id, form);
      } else {
        await createPipelineAutomation(tenantId, token, form);
      }
      setShowModal(false);
      await loadData();
    } catch (err) {
      notify.error(err.message || "Failed to save automation");
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (auto) => {
    try {
      await updatePipelineAutomation(tenantId, token, auto.id, { is_active: !auto.is_active });
      await loadData();
    } catch (err) {
      notify.error(err.message || "Failed to toggle automation");
    }
  };

  const handleDelete = async (id) => {
    try {
      await deletePipelineAutomation(tenantId, token, id);
      setDeleteConfirm(null);
      await loadData();
    } catch (err) {
      notify.error(err.message || "Failed to delete automation");
    }
  };

  const updateAction = (idx, field, value) => {
    const updated = [...form.actions];
    updated[idx] = { ...updated[idx], [field]: value };
    setForm({ ...form, actions: updated });
  };

  const changeActionType = (idx, newType) => {
    const updated = [...form.actions];
    updated[idx] = emptyAction(newType);
    setForm({ ...form, actions: updated });
  };

  const addAction = () => {
    if (form.actions.length >= 10) return;
    setForm({ ...form, actions: [...form.actions, emptyAction()] });
  };

  const removeAction = (idx) => {
    if (form.actions.length <= 1) return;
    const updated = form.actions.filter((_, i) => i !== idx);
    setForm({ ...form, actions: updated });
  };

  const stageNames = stages.map((s) => (typeof s === "string" ? s : s.name || s.stage || ""));

  if (loading) return <SkeletonLoader />;

  return (
    <div style={{ padding: "32px 24px", maxWidth: 900 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.5rem", color: "var(--text-primary)" }}>Pipeline Automations</h1>
          <p style={{ margin: "4px 0 0", color: "var(--text-muted)", fontSize: "0.9rem" }}>
            Auto-trigger actions when leads move between pipeline stages
          </p>
        </div>
        <button className="btn-primary" onClick={openCreate}>
          + New Automation
        </button>
      </div>

      {error && (
        <div style={{ background: "var(--red-dim)", color: "var(--red)", padding: "12px 16px", borderRadius: 8, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {automations.length === 0 && !error ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>\u2699\uFE0F</div>
          <h3 style={{ margin: "0 0 8px", color: "var(--text-secondary)" }}>No pipeline automations yet</h3>
          <p style={{ margin: "0 0 20px" }}>Create your first automation to trigger actions when leads change stages.</p>
          <button className="btn-primary" onClick={openCreate}>Create Automation</button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {automations.map((auto) => (
            <div
              key={auto.id}
              style={{
                background: "var(--card-bg)",
                border: "1px solid var(--border)",
                borderRadius: 10,
                padding: "16px 20px",
                display: "flex",
                alignItems: "center",
                gap: 16,
                opacity: auto.is_active ? 1 : 0.6,
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>{auto.name}</div>
                <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  Trigger: <span style={{ color: "var(--accent)", fontWeight: 500 }}>{auto.trigger_stage}</span>
                  {" "}&middot;{" "}
                  {(auto.actions || []).length} action{(auto.actions || []).length !== 1 ? "s" : ""}
                  {" "}&middot;{" "}
                  {(auto.actions || []).map((a) => a.type).join(", ")}
                </div>
              </div>
              <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                <input
                  type="checkbox"
                  checked={auto.is_active}
                  onChange={() => handleToggleActive(auto)}
                  style={{ accentColor: "var(--accent)" }}
                />
                Active
              </label>
              <button
                onClick={() => openEdit(auto)}
                style={{
                  background: "var(--hover-overlay)",
                  border: "1px solid var(--border)",
                  color: "var(--text-secondary)",
                  padding: "6px 14px",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontSize: "0.8rem",
                }}
              >
                Edit
              </button>
              {deleteConfirm === auto.id ? (
                <div style={{ display: "flex", gap: 4 }}>
                  <button
                    onClick={() => handleDelete(auto.id)}
                    style={{ background: "var(--red)", color: "#fff", border: "none", padding: "6px 12px", borderRadius: 6, cursor: "pointer", fontSize: "0.8rem" }}
                  >
                    Confirm
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(null)}
                    style={{ background: "var(--hover-overlay)", border: "1px solid var(--border)", color: "var(--text-muted)", padding: "6px 10px", borderRadius: 6, cursor: "pointer", fontSize: "0.8rem" }}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setDeleteConfirm(auto.id)}
                  style={{
                    background: "none",
                    border: "1px solid var(--border)",
                    color: "var(--red)",
                    padding: "6px 12px",
                    borderRadius: 6,
                    cursor: "pointer",
                    fontSize: "0.8rem",
                  }}
                >
                  Delete
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setShowModal(false)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "var(--card-bg)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: "28px 24px",
              width: "100%",
              maxWidth: 560,
              maxHeight: "85vh",
              overflowY: "auto",
            }}
          >
            <h2 style={{ margin: "0 0 20px", fontSize: "1.2rem", color: "var(--text-primary)" }}>
              {editing ? "Edit Automation" : "New Pipeline Automation"}
            </h2>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 6 }}>Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Won deal follow-up"
                style={{
                  width: "100%",
                  background: "var(--input-bg)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: "10px 14px",
                  color: "var(--text-primary)",
                  fontSize: "0.95rem",
                }}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 6 }}>Trigger Stage</label>
              <select
                value={form.trigger_stage}
                onChange={(e) => setForm({ ...form, trigger_stage: e.target.value })}
                style={{
                  width: "100%",
                  background: "var(--input-bg)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: "10px 14px",
                  color: "var(--text-primary)",
                  fontSize: "0.95rem",
                }}
              >
                <option value="">Select a stage...</option>
                {stageNames.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 6 }}>Active</label>
              <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  style={{ accentColor: "var(--accent)" }}
                />
                <span style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>Enable this automation</span>
              </label>
            </div>

            <div style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <label style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Actions ({form.actions.length}/10)</label>
                {form.actions.length < 10 && (
                  <button
                    onClick={addAction}
                    style={{ background: "none", border: "none", color: "var(--accent)", cursor: "pointer", fontSize: "0.85rem", fontWeight: 600 }}
                  >
                    + Add Action
                  </button>
                )}
              </div>

              {form.actions.map((action, idx) => (
                <div
                  key={idx}
                  style={{
                    background: "var(--hover-overlay)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    padding: 14,
                    marginBottom: 10,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                    <select
                      value={action.type}
                      onChange={(e) => changeActionType(idx, e.target.value)}
                      style={{
                        background: "var(--input-bg)",
                        border: "1px solid var(--border)",
                        borderRadius: 6,
                        padding: "6px 10px",
                        color: "var(--text-primary)",
                        fontSize: "0.85rem",
                      }}
                    >
                      {ACTION_TYPES.map((at) => (
                        <option key={at.value} value={at.value}>{at.icon} {at.label}</option>
                      ))}
                    </select>
                    {form.actions.length > 1 && (
                      <button
                        onClick={() => removeAction(idx)}
                        style={{ background: "none", border: "none", color: "var(--red)", cursor: "pointer", fontSize: "0.8rem" }}
                      >
                        Remove
                      </button>
                    )}
                  </div>

                  {action.type === "email" && (
                    <>
                      <input
                        type="text"
                        value={action.subject || ""}
                        onChange={(e) => updateAction(idx, "subject", e.target.value)}
                        placeholder="Email subject (supports {{name}}, {{business_name}})"
                        style={{
                          width: "100%",
                          background: "var(--input-bg)",
                          border: "1px solid var(--border)",
                          borderRadius: 6,
                          padding: "8px 12px",
                          color: "var(--text-primary)",
                          fontSize: "0.85rem",
                          marginBottom: 8,
                        }}
                      />
                      <textarea
                        value={action.body || ""}
                        onChange={(e) => updateAction(idx, "body", e.target.value)}
                        placeholder="Email body HTML (supports {{name}}, {{business_name}})"
                        rows={3}
                        style={{
                          width: "100%",
                          background: "var(--input-bg)",
                          border: "1px solid var(--border)",
                          borderRadius: 6,
                          padding: "8px 12px",
                          color: "var(--text-primary)",
                          fontSize: "0.85rem",
                          resize: "vertical",
                        }}
                      />
                    </>
                  )}

                  {action.type === "create_task" && (
                    <input
                      type="text"
                      value={action.description || ""}
                      onChange={(e) => updateAction(idx, "description", e.target.value)}
                      placeholder="Task description (supports {{name}}, {{stage}})"
                      style={{
                        width: "100%",
                        background: "var(--input-bg)",
                        border: "1px solid var(--border)",
                        borderRadius: 6,
                        padding: "8px 12px",
                        color: "var(--text-primary)",
                        fontSize: "0.85rem",
                      }}
                    />
                  )}

                  {action.type === "notify_team" && (
                    <input
                      type="text"
                      value={action.message || ""}
                      onChange={(e) => updateAction(idx, "message", e.target.value)}
                      placeholder="Notification message (optional)"
                      style={{
                        width: "100%",
                        background: "var(--input-bg)",
                        border: "1px solid var(--border)",
                        borderRadius: 6,
                        padding: "8px 12px",
                        color: "var(--text-primary)",
                        fontSize: "0.85rem",
                      }}
                    />
                  )}
                </div>
              ))}
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                onClick={() => setShowModal(false)}
                style={{
                  background: "var(--hover-overlay)",
                  border: "1px solid var(--border)",
                  color: "var(--text-secondary)",
                  padding: "10px 20px",
                  borderRadius: 8,
                  cursor: "pointer",
                  fontSize: "0.9rem",
                }}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleSave}
                disabled={saving || !form.name.trim() || !form.trigger_stage}
                style={{ opacity: saving ? 0.6 : 1 }}
              >
                {saving ? "Saving..." : editing ? "Update" : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
