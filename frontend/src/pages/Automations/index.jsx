import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  fetchSequences,
  createSequence,
  updateSequence,
  deleteSequence,
  toggleSequence,
  fetchSequenceDetail,
  createFromTemplate,
} from "../../utils/api";
import SequenceBuilder from "./SequenceBuilder";
import SequenceDetail from "./SequenceDetail";
import TemplateGallery from "./TemplateGallery";

const triggerLabels = {
  new_lead: "New Lead",
  lead_stage_change: "Stage Change",
  no_response_24h: "No Response",
};

const triggerColors = {
  new_lead: "var(--green)",
  lead_stage_change: "var(--accent)",
  no_response_24h: "var(--yellow)",
};

export default function AutomationsPage({ onNavigate }) {
  const { user, token } = useAuth();
  const [sequences, setSequences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showBuilder, setShowBuilder] = useState(false);
  const [editingSeq, setEditingSeq] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);

  const loadSequences = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const data = await fetchSequences(user.tenantId, token);
      setSequences(data.sequences || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadSequences();
  }, [loadSequences]);

  const handleCreate = () => {
    setEditingSeq(null);
    setShowBuilder(true);
  };

  const handleEdit = async (seq) => {
    try {
      const detail = await fetchSequenceDetail(user.tenantId, token, seq.id);
      setEditingSeq({ ...detail.sequence, steps: detail.steps });
      setShowBuilder(true);
    } catch {
      setError("Failed to load sequence details");
    }
  };

  const handleSave = async (data) => {
    setSaving(true);
    try {
      if (editingSeq) {
        await updateSequence(user.tenantId, token, editingSeq.id, data);
      } else {
        await createSequence(user.tenantId, token, data);
      }
      setShowBuilder(false);
      setEditingSeq(null);
      await loadSequences();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (seqId) => {
    if (!confirm("Delete this sequence? This cannot be undone.")) return;
    try {
      await deleteSequence(user.tenantId, token, seqId);
      await loadSequences();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleToggle = async (seqId) => {
    try {
      await toggleSequence(user.tenantId, token, seqId);
      await loadSequences();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleViewDetail = async (seq) => {
    try {
      const detail = await fetchSequenceDetail(user.tenantId, token, seq.id);
      setDetailData(detail);
    } catch {
      setError("Failed to load sequence details");
    }
  };

  const handleUseTemplate = async (templateId) => {
    setSaving(true);
    try {
      await createFromTemplate(user.tenantId, token, templateId);
      setShowTemplates(false);
      await loadSequences();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="fade-in">
        <div className="page-header"><h1>Automations</h1></div>
        <div style={{ color: "var(--text-muted)", padding: "40px 0", textAlign: "center" }}>Loading...</div>
      </div>
    );
  }

  const isEmpty = sequences.length === 0 && !showTemplates;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Automations</h1>
        <p>Create automated email sequences to follow up with leads</p>
      </div>

      {error && (
        <div style={{
          background: "var(--red-dim)",
          color: "var(--red)",
          padding: "10px 16px",
          borderRadius: "var(--radius-sm)",
          marginBottom: "16px",
          fontSize: "13px",
        }}>
          {error}
          <button
            onClick={() => setError(null)}
            style={{ float: "right", background: "none", border: "none", color: "var(--red)", cursor: "pointer" }}
          >
            &times;
          </button>
        </div>
      )}

      {/* Action buttons */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "24px" }}>
        <button onClick={handleCreate} style={{
          padding: "10px 20px",
          background: "var(--accent)",
          color: "#000",
          border: "none",
          borderRadius: "var(--radius-sm)",
          cursor: "pointer",
          fontWeight: 600,
          fontSize: "14px",
        }}>
          + Create Sequence
        </button>
        <button onClick={() => setShowTemplates(!showTemplates)} style={{
          padding: "10px 20px",
          background: "transparent",
          color: "var(--text-secondary)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-sm)",
          cursor: "pointer",
          fontSize: "14px",
        }}>
          {showTemplates ? "Hide Templates" : "Use Template"}
        </button>
      </div>

      {/* Template Gallery */}
      {showTemplates && (
        <div style={{ marginBottom: "24px" }}>
          <TemplateGallery onUseTemplate={handleUseTemplate} loading={saving} />
        </div>
      )}

      {/* Empty state */}
      {isEmpty && !showTemplates && (
        <div style={{
          textAlign: "center",
          padding: "60px 20px",
          color: "var(--text-secondary)",
        }}>
          <div style={{ marginBottom: "16px" }}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" /></svg>
          </div>
          <h3 style={{ color: "var(--text-primary)", margin: "0 0 8px" }}>No sequences yet</h3>
          <p style={{ margin: "0 0 20px", fontSize: "14px" }}>
            Create your first automated email sequence or start with a template.
          </p>
          <button onClick={() => setShowTemplates(true)} style={{
            padding: "10px 20px",
            background: "var(--accent-dim)",
            color: "var(--accent)",
            border: "1px solid var(--accent)",
            borderRadius: "var(--radius-sm)",
            cursor: "pointer",
            fontWeight: 600,
          }}>
            Browse Templates
          </button>
        </div>
      )}

      {/* Sequences list */}
      {sequences.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {sequences.map((seq) => (
            <div
              key={seq.id}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
                padding: "20px",
                display: "flex",
                alignItems: "center",
                gap: "16px",
                transition: "border-color 0.2s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border-hover)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
            >
              {/* Active indicator */}
              <div style={{
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                background: seq.is_active ? "var(--green)" : "var(--text-muted)",
                flexShrink: 0,
              }} />

              {/* Info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  marginBottom: "4px",
                }}>
                  <span
                    style={{ color: "var(--text-primary)", fontWeight: 600, fontSize: "15px", cursor: "pointer" }}
                    onClick={() => handleViewDetail(seq)}
                  >
                    {seq.name}
                  </span>
                  <span style={{
                    padding: "2px 8px",
                    background: `color-mix(in srgb, ${triggerColors[seq.trigger_event] || "var(--accent)"} 15%, transparent)`,
                    color: triggerColors[seq.trigger_event] || "var(--accent)",
                    borderRadius: "var(--radius-sm)",
                    fontSize: "11px",
                    fontWeight: 600,
                  }}>
                    {triggerLabels[seq.trigger_event] || seq.trigger_event}
                  </span>
                </div>
                <div style={{ color: "var(--text-muted)", fontSize: "12px" }}>
                  {seq.step_count} step{seq.step_count !== 1 ? "s" : ""} · {seq.total_enrolled} enrolled · {seq.completed_count} completed
                </div>
              </div>

              {/* Actions */}
              <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
                <button
                  onClick={() => handleToggle(seq.id)}
                  title={seq.is_active ? "Deactivate" : "Activate"}
                  style={{
                    padding: "6px 12px",
                    background: seq.is_active ? "var(--green-dim)" : "var(--bg-primary)",
                    color: seq.is_active ? "var(--green)" : "var(--text-muted)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-sm)",
                    cursor: "pointer",
                    fontSize: "12px",
                  }}
                >
                  {seq.is_active ? "Active" : "Paused"}
                </button>
                <button
                  onClick={() => handleEdit(seq)}
                  style={{
                    padding: "6px 12px",
                    background: "var(--bg-primary)",
                    color: "var(--text-secondary)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-sm)",
                    cursor: "pointer",
                    fontSize: "12px",
                  }}
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(seq.id)}
                  style={{
                    padding: "6px 12px",
                    background: "var(--bg-primary)",
                    color: "var(--red)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-sm)",
                    cursor: "pointer",
                    fontSize: "12px",
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Builder modal */}
      {showBuilder && (
        <SequenceBuilder
          sequence={editingSeq}
          onSave={handleSave}
          onClose={() => { setShowBuilder(false); setEditingSeq(null); }}
          saving={saving}
        />
      )}

      {/* Detail modal */}
      {detailData && (
        <SequenceDetail
          detail={detailData}
          onClose={() => setDetailData(null)}
        />
      )}
    </div>
  );
}
