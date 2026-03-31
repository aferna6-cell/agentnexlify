import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  fetchForms,
  createForm,
  updateForm,
  deleteForm,
  fetchFormSubmissions,
  fetchFormStats,
} from "../utils/api/forms";

const FIELD_TYPES = [
  { value: "text", label: "Text" },
  { value: "email", label: "Email" },
  { value: "phone", label: "Phone" },
  { value: "textarea", label: "Text Area" },
  { value: "select", label: "Dropdown" },
  { value: "radio", label: "Radio Buttons" },
  { value: "checkbox", label: "Checkbox" },
  { value: "number", label: "Number" },
  { value: "date", label: "Date" },
];

const EMBED_BASE = "https://agentnexlify-production.up.railway.app";

function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function StatusBadge({ active }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: "0.7rem",
        fontWeight: 600,
        color: active ? "#22c55e" : "var(--text-muted)",
        background: active ? "rgba(34,197,94,0.1)" : "var(--hover-overlay)",
      }}
    >
      {active ? "Active" : "Inactive"}
    </span>
  );
}

function makeFieldId(fields) {
  const maxNum = fields.reduce((max, f) => {
    const match = (f.id || "").match(/^field_(\d+)$/);
    return match ? Math.max(max, parseInt(match[1], 10)) : max;
  }, 0);
  return `field_${maxNum + 1}`;
}

function newEmptyField(fields) {
  return {
    id: makeFieldId(fields),
    type: "text",
    label: "",
    placeholder: "",
    required: false,
    options: [],
  };
}

const emptyFormData = {
  name: "",
  description: "",
  fields: [],
  settings: {
    success_message: "Thank you for your submission!",
    redirect_url: "",
    is_active: true,
  },
};

// ------------- Live Preview Component -------------
function FormPreview({ fields, name, description }) {
  return (
    <div
      style={{
        background: "#f8f9fa",
        borderRadius: 10,
        padding: "24px 20px",
        minHeight: 200,
        color: "#1a1a2e",
      }}
    >
      {name && (
        <h3 style={{ margin: "0 0 4px", fontSize: "1.1rem", color: "#1a1a2e" }}>
          {name}
        </h3>
      )}
      {description && (
        <p style={{ margin: "0 0 16px", fontSize: "0.85rem", color: "#555" }}>
          {description}
        </p>
      )}
      {fields.length === 0 && (
        <div style={{ textAlign: "center", padding: "32px 0", color: "#999", fontSize: "0.85rem" }}>
          Add fields to see a live preview of your form
        </div>
      )}
      {fields.map((field) => (
        <div key={field.id} style={{ marginBottom: 14 }}>
          <label
            style={{
              display: "block",
              fontSize: "0.8rem",
              fontWeight: 600,
              marginBottom: 4,
              color: "#333",
            }}
          >
            {field.label || "(Untitled field)"}
            {field.required && <span style={{ color: "#ef4444", marginLeft: 2 }}>*</span>}
          </label>
          {field.type === "textarea" ? (
            <textarea
              readOnly
              placeholder={field.placeholder || ""}
              rows={3}
              style={{
                width: "100%",
                padding: "8px 10px",
                border: "1px solid #ccc",
                borderRadius: 6,
                fontSize: "0.85rem",
                resize: "vertical",
                background: "#fff",
                color: "#333",
                boxSizing: "border-box",
              }}
            />
          ) : field.type === "select" ? (
            <select
              disabled
              style={{
                width: "100%",
                padding: "8px 10px",
                border: "1px solid #ccc",
                borderRadius: 6,
                fontSize: "0.85rem",
                background: "#fff",
                color: "#333",
              }}
            >
              <option value="">{field.placeholder || "Select..."}</option>
              {(field.options || []).map((opt, i) => (
                <option key={i} value={opt}>{opt}</option>
              ))}
            </select>
          ) : field.type === "radio" ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
              {(field.options || []).length === 0 ? (
                <span style={{ fontSize: "0.8rem", color: "#999" }}>Add options for radio buttons</span>
              ) : (
                field.options.map((opt, i) => (
                  <label key={i} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem", color: "#333" }}>
                    <input type="radio" name={`preview-${field.id}`} disabled style={{ width: "auto" }} />
                    {opt}
                  </label>
                ))
              )}
            </div>
          ) : field.type === "checkbox" ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
              {(field.options || []).length === 0 ? (
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem", color: "#333" }}>
                  <input type="checkbox" disabled style={{ width: "auto" }} />
                  {field.label || "Checkbox"}
                </label>
              ) : (
                field.options.map((opt, i) => (
                  <label key={i} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem", color: "#333" }}>
                    <input type="checkbox" disabled style={{ width: "auto" }} />
                    {opt}
                  </label>
                ))
              )}
            </div>
          ) : (
            <input
              readOnly
              type={field.type === "email" ? "email" : field.type === "phone" ? "tel" : field.type === "number" ? "number" : field.type === "date" ? "date" : "text"}
              placeholder={field.placeholder || ""}
              style={{
                width: "100%",
                padding: "8px 10px",
                border: "1px solid #ccc",
                borderRadius: 6,
                fontSize: "0.85rem",
                background: "#fff",
                color: "#333",
                boxSizing: "border-box",
              }}
            />
          )}
        </div>
      ))}
      {fields.length > 0 && (
        <button
          disabled
          style={{
            marginTop: 8,
            padding: "10px 24px",
            background: "var(--accent, #6366f1)",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            fontWeight: 600,
            fontSize: "0.9rem",
            cursor: "default",
            opacity: 0.85,
          }}
        >
          Submit
        </button>
      )}
    </div>
  );
}

// ------------- Main Page Component -------------
export default function FormBuilderPage() {
  const { user, token } = useAuth();
  const [forms, setForms] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Editor state
  const [showEditor, setShowEditor] = useState(false);
  const [editingForm, setEditingForm] = useState(null); // null = new, object = editing
  const [formData, setFormData] = useState({ ...emptyFormData, fields: [] });
  const [saving, setSaving] = useState(false);

  // Submissions view
  const [viewingSubmissions, setViewingSubmissions] = useState(null); // form object
  const [submissions, setSubmissions] = useState([]);
  const [loadingSubs, setLoadingSubs] = useState(false);
  const [expandedSubId, setExpandedSubId] = useState(null);

  // Embed code copy
  const [copiedEmbed, setCopiedEmbed] = useState(null); // "iframe" | "link" | null

  // Deleting
  const [deletingIds, setDeletingIds] = useState(new Set());

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const [formsData, statsData] = await Promise.all([
        fetchForms(user.tenantId, token),
        fetchFormStats(user.tenantId, token),
      ]);
      setForms(formsData.forms || formsData || []);
      setStats(statsData);
      setError(null);
    } catch (err) {
      console.warn("Failed to load forms:", err.message);
      setError(err.message || "Failed to load forms");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  // ---- Form editor helpers ----
  const openCreate = () => {
    setEditingForm(null);
    setFormData({
      name: "",
      description: "",
      fields: [
        { id: "field_1", type: "text", label: "Your Name", placeholder: "John Doe", required: true, options: [] },
        { id: "field_2", type: "email", label: "Email", placeholder: "you@example.com", required: true, options: [] },
        { id: "field_3", type: "textarea", label: "Message", placeholder: "How can we help?", required: false, options: [] },
      ],
      settings: {
        success_message: "Thank you for your submission!",
        redirect_url: "",
        is_active: true,
      },
    });
    setShowEditor(true);
  };

  const openEdit = (form) => {
    setEditingForm(form);
    const fields = (form.fields_json || []).map((f) => ({
      ...f,
      options: f.options || [],
      placeholder: f.placeholder || "",
      required: f.required || false,
    }));
    setFormData({
      name: form.name || "",
      description: form.description || "",
      fields,
      settings: form.settings_json || {
        success_message: "Thank you for your submission!",
        redirect_url: "",
        is_active: true,
      },
    });
    setShowEditor(true);
  };

  const addField = () => {
    setFormData((prev) => ({
      ...prev,
      fields: [...prev.fields, newEmptyField(prev.fields)],
    }));
  };

  const removeField = (idx) => {
    setFormData((prev) => ({
      ...prev,
      fields: prev.fields.filter((_, i) => i !== idx),
    }));
  };

  const updateField = (idx, key, value) => {
    setFormData((prev) => ({
      ...prev,
      fields: prev.fields.map((f, i) => (i === idx ? { ...f, [key]: value } : f)),
    }));
  };

  const moveField = (idx, direction) => {
    const targetIdx = idx + direction;
    if (targetIdx < 0 || targetIdx >= formData.fields.length) return;
    setFormData((prev) => {
      const next = [...prev.fields];
      [next[idx], next[targetIdx]] = [next[targetIdx], next[idx]];
      return { ...prev, fields: next };
    });
  };

  const updateSettings = (key, value) => {
    setFormData((prev) => ({
      ...prev,
      settings: { ...prev.settings, [key]: value },
    }));
  };

  const handleSave = async () => {
    if (!formData.name.trim()) return;
    if (formData.fields.length === 0) {
      setError("Add at least one field to your form");
      return;
    }
    setSaving(true);
    const body = {
      name: formData.name.trim(),
      description: formData.description.trim(),
      fields_json: formData.fields.map((f) => ({
        id: f.id,
        type: f.type,
        label: f.label,
        placeholder: f.placeholder || undefined,
        required: f.required,
        options: ["select", "radio", "checkbox"].includes(f.type) ? f.options : undefined,
      })),
      settings_json: formData.settings,
    };

    try {
      if (editingForm) {
        await updateForm(user.tenantId, token, editingForm.id, body);
      } else {
        await createForm(user.tenantId, token, body);
      }
      setShowEditor(false);
      setEditingForm(null);
      setFormData({ ...emptyFormData, fields: [] });
      loadData();
    } catch (err) {
      console.warn("Save form failed:", err.message);
      setError(err.message || "Failed to save form");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (formId) => {
    if (!window.confirm("Delete this form? This cannot be undone. All submissions will also be deleted.")) return;
    setDeletingIds((prev) => new Set(prev).add(formId));
    try {
      await deleteForm(user.tenantId, token, formId);
      setForms((prev) => prev.filter((f) => f.id !== formId));
      if (viewingSubmissions?.id === formId) setViewingSubmissions(null);
      setError(null);
    } catch (err) {
      console.warn("Delete form failed:", err.message);
      setError(err.message || "Failed to delete form");
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(formId);
        return next;
      });
    }
  };

  // ---- Submissions helpers ----
  const openSubmissions = async (form) => {
    setViewingSubmissions(form);
    setLoadingSubs(true);
    setExpandedSubId(null);
    try {
      const data = await fetchFormSubmissions(user.tenantId, token, form.id);
      setSubmissions(data.submissions || data || []);
    } catch (err) {
      console.warn("Failed to load submissions:", err.message);
      setSubmissions([]);
    } finally {
      setLoadingSubs(false);
    }
  };

  // ---- Embed helpers ----
  const getEmbedIframe = (form) => {
    const url = `${EMBED_BASE}/api/v1/forms/public/${form.public_token || form.id}/embed`;
    return `<iframe src="${url}" width="100%" height="500" frameborder="0" style="border:none;border-radius:12px;"></iframe>`;
  };

  const getDirectLink = (form) => {
    return `${EMBED_BASE}/api/v1/forms/public/${form.public_token || form.id}/embed`;
  };

  const copyToClipboard = (text, type) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedEmbed(type);
      setTimeout(() => setCopiedEmbed(null), 2000);
    }).catch(() => {
      setError("Failed to copy to clipboard");
    });
  };

  // ---- Derived stats ----
  const totalForms = stats?.total_forms ?? forms.length;
  const totalSubmissions = stats?.total_submissions ?? 0;
  const activeForms = stats?.active_forms ?? forms.filter((f) => f.is_active !== false).length;
  const conversionRate = stats?.conversion_rate ?? 0;

  if (loading) return <SkeletonLoader />;

  // ---- Submissions modal ----
  if (viewingSubmissions) {
    return (
      <div className="fade-in">
        <div className="page-header">
          <div>
            <button
              onClick={() => setViewingSubmissions(null)}
              style={{
                background: "none",
                border: "none",
                color: "var(--accent)",
                cursor: "pointer",
                fontSize: "0.85rem",
                padding: 0,
                marginBottom: 8,
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              &larr; Back to Forms
            </button>
            <h1>Submissions: {viewingSubmissions.name}</h1>
            <p>Viewing all submissions for this form</p>
          </div>
        </div>

        {loadingSubs ? (
          <SkeletonLoader />
        ) : submissions.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
            <div style={{ fontSize: "2rem", marginBottom: 12 }}>No submissions yet</div>
            <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
              This form has not received any submissions. Share the form link or embed it on your website to start collecting responses.
            </p>
            <div style={{ display: "flex", gap: 8, justifyContent: "center", flexWrap: "wrap" }}>
              <button
                onClick={() => copyToClipboard(getDirectLink(viewingSubmissions), "link")}
                className="btn-primary"
              >
                {copiedEmbed === "link" ? "Copied!" : "Copy Form Link"}
              </button>
              <button
                onClick={() => copyToClipboard(getEmbedIframe(viewingSubmissions), "iframe")}
                style={{
                  background: "transparent",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: "8px 16px",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                }}
              >
                {copiedEmbed === "iframe" ? "Copied!" : "Copy Embed Code"}
              </button>
            </div>
          </div>
        ) : (
          <div
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            {/* Submissions table header */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "60px 1fr 140px 100px",
                padding: "10px 16px",
                borderBottom: "1px solid var(--border)",
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              <span>#</span>
              <span>Summary</span>
              <span>Submitted</span>
              <span style={{ textAlign: "center" }}>Lead</span>
            </div>

            {submissions.map((sub, idx) => {
              const isExpanded = expandedSubId === sub.id;
              const submissionData = sub.data_json || sub.data || sub.submission_data || {};
              const summaryParts = Object.values(submissionData).filter(Boolean).slice(0, 3);
              const summaryText = summaryParts.join(" / ") || "-";

              return (
                <div key={sub.id || idx}>
                  <div
                    onClick={() => setExpandedSubId(isExpanded ? null : sub.id)}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "60px 1fr 140px 100px",
                      padding: "12px 16px",
                      borderBottom: "1px solid var(--border)",
                      alignItems: "center",
                      cursor: "pointer",
                      transition: "background 0.1s ease",
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "var(--hover-overlay)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                  >
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{idx + 1}</span>
                    <span style={{ fontSize: "0.85rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {summaryText}
                    </span>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      {formatDate(sub.created_at || sub.submitted_at)}
                    </span>
                    <span style={{ textAlign: "center" }}>
                      {sub.lead_id ? (
                        <span
                          style={{
                            display: "inline-block",
                            padding: "2px 8px",
                            borderRadius: 4,
                            fontSize: "0.7rem",
                            fontWeight: 600,
                            color: "#22c55e",
                            background: "rgba(34,197,94,0.1)",
                          }}
                        >
                          Linked
                        </span>
                      ) : (
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>--</span>
                      )}
                    </span>
                  </div>
                  {/* Expanded row with full data */}
                  {isExpanded && (
                    <div
                      style={{
                        padding: "12px 16px 12px 76px",
                        background: "var(--bg-primary)",
                        borderBottom: "1px solid var(--border)",
                      }}
                    >
                      {Object.entries(submissionData).map(([key, val]) => (
                        <div key={key} style={{ marginBottom: 6, fontSize: "0.85rem" }}>
                          <span style={{ color: "var(--text-muted)", fontWeight: 600, marginRight: 8 }}>
                            {key}:
                          </span>
                          <span style={{ color: "var(--text-secondary)" }}>
                            {typeof val === "boolean" ? (val ? "Yes" : "No") : String(val || "-")}
                          </span>
                        </div>
                      ))}
                      {Object.keys(submissionData).length === 0 && (
                        <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>No data recorded</div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // ---- Form editor modal ----
  if (showEditor) {
    const hasOptionsType = ["select", "radio", "checkbox"];

    return (
      <div className="fade-in">
        <div className="page-header">
          <div>
            <button
              onClick={() => { setShowEditor(false); setEditingForm(null); }}
              style={{
                background: "none",
                border: "none",
                color: "var(--accent)",
                cursor: "pointer",
                fontSize: "0.85rem",
                padding: 0,
                marginBottom: 8,
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              &larr; Back to Forms
            </button>
            <h1>{editingForm ? "Edit Form" : "New Form"}</h1>
            <p>Design your form and preview it in real-time</p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <button
              onClick={() => { setShowEditor(false); setEditingForm(null); }}
              style={{
                background: "transparent",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: "8px 16px",
                color: "var(--text-primary)",
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
            <button
              className="btn-primary"
              onClick={handleSave}
              disabled={!formData.name.trim() || formData.fields.length === 0 || saving}
            >
              {saving ? "Saving..." : editingForm ? "Update Form" : "Create Form"}
            </button>
          </div>
        </div>

        {error && (
          <div
            style={{
              marginBottom: 16,
              padding: "10px 16px",
              background: "rgba(239,68,68,0.1)",
              border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: 8,
              color: "#ef4444",
              fontSize: "0.85rem",
            }}
          >
            {error}
            <button
              onClick={() => setError(null)}
              style={{ marginLeft: 12, background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: "0.8rem", textDecoration: "underline" }}
            >
              dismiss
            </button>
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, alignItems: "start" }}>
          {/* Left column: Form builder */}
          <div>
            {/* Name & Description */}
            <div
              style={{
                background: "var(--bg-secondary)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: 20,
                marginBottom: 16,
              }}
            >
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)", fontWeight: 600 }}>
                  Form Name *
                </label>
                <input
                  value={formData.name}
                  onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., Contact Form, Quote Request"
                  style={{ width: "100%", boxSizing: "border-box" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)", fontWeight: 600 }}>
                  Description
                </label>
                <input
                  value={formData.description}
                  onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder="A short description for your visitors"
                  style={{ width: "100%", boxSizing: "border-box" }}
                />
              </div>
            </div>

            {/* Field builder */}
            <div
              style={{
                background: "var(--bg-secondary)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: 20,
                marginBottom: 16,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }}>
                  Fields ({formData.fields.length})
                </div>
                <button
                  onClick={addField}
                  style={{
                    background: "none",
                    border: "1px solid var(--border)",
                    borderRadius: 6,
                    padding: "4px 12px",
                    color: "var(--accent)",
                    cursor: "pointer",
                    fontSize: "0.8rem",
                    fontWeight: 600,
                  }}
                >
                  + Add Field
                </button>
              </div>

              {formData.fields.length === 0 && (
                <div style={{ textAlign: "center", padding: "24px 12px", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                  No fields yet. Click "Add Field" to start building your form.
                </div>
              )}

              {formData.fields.map((field, idx) => (
                <div
                  key={field.id}
                  style={{
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    padding: "12px 14px",
                    marginBottom: 10,
                    background: "var(--bg-primary)",
                  }}
                >
                  {/* Field header: type + actions */}
                  <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}>
                    <select
                      value={field.type}
                      onChange={(e) => updateField(idx, "type", e.target.value)}
                      style={{ flex: "0 0 130px", fontSize: "0.8rem" }}
                    >
                      {FIELD_TYPES.map((ft) => (
                        <option key={ft.value} value={ft.value}>{ft.label}</option>
                      ))}
                    </select>
                    <input
                      value={field.label}
                      onChange={(e) => updateField(idx, "label", e.target.value)}
                      placeholder="Field label"
                      style={{ flex: 1, fontSize: "0.85rem" }}
                    />
                    <div style={{ display: "flex", gap: 2, flexShrink: 0 }}>
                      <button
                        onClick={() => moveField(idx, -1)}
                        disabled={idx === 0}
                        style={{
                          background: "none",
                          border: "1px solid var(--border)",
                          borderRadius: 4,
                          padding: "2px 6px",
                          color: idx === 0 ? "var(--border)" : "var(--text-secondary)",
                          cursor: idx === 0 ? "default" : "pointer",
                          fontSize: "0.75rem",
                        }}
                        title="Move up"
                      >
                        Up
                      </button>
                      <button
                        onClick={() => moveField(idx, 1)}
                        disabled={idx === formData.fields.length - 1}
                        style={{
                          background: "none",
                          border: "1px solid var(--border)",
                          borderRadius: 4,
                          padding: "2px 6px",
                          color: idx === formData.fields.length - 1 ? "var(--border)" : "var(--text-secondary)",
                          cursor: idx === formData.fields.length - 1 ? "default" : "pointer",
                          fontSize: "0.75rem",
                        }}
                        title="Move down"
                      >
                        Dn
                      </button>
                      <button
                        onClick={() => removeField(idx)}
                        style={{
                          background: "none",
                          border: "1px solid rgba(239,68,68,0.3)",
                          borderRadius: 4,
                          padding: "2px 6px",
                          color: "#ef4444",
                          cursor: "pointer",
                          fontSize: "0.75rem",
                        }}
                        title="Remove field"
                      >
                        Del
                      </button>
                    </div>
                  </div>

                  {/* Placeholder + Required */}
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      value={field.placeholder}
                      onChange={(e) => updateField(idx, "placeholder", e.target.value)}
                      placeholder="Placeholder text (optional)"
                      style={{ flex: 1, fontSize: "0.8rem" }}
                    />
                    <label
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                        fontSize: "0.8rem",
                        color: "var(--text-secondary)",
                        cursor: "pointer",
                        whiteSpace: "nowrap",
                        flexShrink: 0,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={field.required}
                        onChange={(e) => updateField(idx, "required", e.target.checked)}
                        style={{ width: "auto" }}
                      />
                      Required
                    </label>
                  </div>

                  {/* Options (for select/radio/checkbox) */}
                  {hasOptionsType.includes(field.type) && (
                    <div style={{ marginTop: 8 }}>
                      <label style={{ display: "block", fontSize: "0.75rem", marginBottom: 4, color: "var(--text-muted)", fontWeight: 600 }}>
                        Options (one per line or comma-separated)
                      </label>
                      <textarea
                        value={(field.options || []).join("\n")}
                        onChange={(e) => {
                          const raw = e.target.value;
                          const opts = raw.includes(",")
                            ? raw.split(",").map((s) => s.trim()).filter(Boolean)
                            : raw.split("\n").filter((s) => s.trim());
                          updateField(idx, "options", opts);
                        }}
                        placeholder={"Option 1\nOption 2\nOption 3"}
                        rows={3}
                        style={{ width: "100%", resize: "vertical", fontSize: "0.8rem", boxSizing: "border-box" }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Settings */}
            <div
              style={{
                background: "var(--bg-secondary)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: 20,
                marginBottom: 16,
              }}
            >
              <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: 14 }}>
                Settings
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)", fontWeight: 600 }}>
                  Success Message
                </label>
                <textarea
                  value={formData.settings.success_message}
                  onChange={(e) => updateSettings("success_message", e.target.value)}
                  placeholder="Message shown after submission"
                  rows={2}
                  style={{ width: "100%", resize: "vertical", boxSizing: "border-box" }}
                />
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)", fontWeight: 600 }}>
                  Redirect URL (optional)
                </label>
                <input
                  value={formData.settings.redirect_url}
                  onChange={(e) => updateSettings("redirect_url", e.target.value)}
                  placeholder="https://yoursite.com/thank-you"
                  style={{ width: "100%", boxSizing: "border-box" }}
                />
              </div>
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  fontSize: "0.85rem",
                  color: "var(--text-secondary)",
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={formData.settings.is_active}
                  onChange={(e) => updateSettings("is_active", e.target.checked)}
                  style={{ width: "auto" }}
                />
                Form is active and accepting submissions
              </label>
            </div>

            {/* Embed code (only for existing forms) */}
            {editingForm && (
              <div
                style={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  padding: 20,
                }}
              >
                <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: 14 }}>
                  Embed Code
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: "block", fontSize: "0.75rem", marginBottom: 4, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
                    Direct Link
                  </label>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      readOnly
                      value={getDirectLink(editingForm)}
                      style={{ flex: 1, fontSize: "0.8rem", background: "var(--bg-primary)" }}
                    />
                    <button
                      onClick={() => copyToClipboard(getDirectLink(editingForm), "link")}
                      style={{
                        background: copiedEmbed === "link" ? "rgba(34,197,94,0.1)" : "var(--bg-primary)",
                        border: "1px solid var(--border)",
                        borderRadius: 6,
                        padding: "6px 12px",
                        color: copiedEmbed === "link" ? "#22c55e" : "var(--text-secondary)",
                        cursor: "pointer",
                        fontSize: "0.8rem",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {copiedEmbed === "link" ? "Copied!" : "Copy"}
                    </button>
                  </div>
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", marginBottom: 4, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
                    Embed (iframe)
                  </label>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      readOnly
                      value={getEmbedIframe(editingForm)}
                      style={{ flex: 1, fontSize: "0.75rem", background: "var(--bg-primary)", fontFamily: "monospace" }}
                    />
                    <button
                      onClick={() => copyToClipboard(getEmbedIframe(editingForm), "iframe")}
                      style={{
                        background: copiedEmbed === "iframe" ? "rgba(34,197,94,0.1)" : "var(--bg-primary)",
                        border: "1px solid var(--border)",
                        borderRadius: 6,
                        padding: "6px 12px",
                        color: copiedEmbed === "iframe" ? "#22c55e" : "var(--text-secondary)",
                        cursor: "pointer",
                        fontSize: "0.8rem",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {copiedEmbed === "iframe" ? "Copied!" : "Copy"}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right column: Live preview */}
          <div
            style={{
              position: "sticky",
              top: 20,
            }}
          >
            <div
              style={{
                background: "var(--bg-secondary)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: 16,
              }}
            >
              <div style={{ fontSize: "0.75rem", fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 10, letterSpacing: "0.05em" }}>
                Live Preview
              </div>
              <FormPreview
                fields={formData.fields}
                name={formData.name}
                description={formData.description}
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ---- Main list view ----
  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Forms & Surveys</h1>
          <p>Create embeddable forms that auto-capture leads</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            className="btn-primary"
            onClick={() => { setLoading(true); loadData(); }}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
            }}
          >
            Refresh
          </button>
          <button className="btn-primary" onClick={openCreate}>
            + New Form
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 12,
          marginBottom: 24,
        }}
      >
        {[
          { label: "Total Forms", value: totalForms, color: "#3b82f6" },
          { label: "Total Submissions", value: totalSubmissions, color: "#8b5cf6" },
          { label: "Active Forms", value: activeForms, color: "#22c55e" },
          { label: "Conversion Rate", value: conversionRate ? `${conversionRate}%` : "---", color: "#f59e0b" },
        ].map((card) => (
          <div
            key={card.label}
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: "16px 20px",
            }}
          >
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4 }}>
              {card.label}
            </div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: card.color }}>
              {card.value}
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div
          style={{
            marginBottom: 16,
            padding: "10px 16px",
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 8,
            color: "#ef4444",
            fontSize: "0.85rem",
          }}
        >
          {error}
          <button
            onClick={() => setError(null)}
            style={{ marginLeft: 12, background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: "0.8rem", textDecoration: "underline" }}
          >
            dismiss
          </button>
        </div>
      )}

      {/* Forms list */}
      {forms.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>No forms yet</div>
          <p style={{ maxWidth: 520, margin: "0 auto 20px", lineHeight: 1.6 }}>
            Create your first form to start capturing leads. Forms can be embedded on any website or shared via a direct link. Submissions automatically create leads in your CRM.
          </p>
          <button className="btn-primary" onClick={openCreate}>
            Create Your First Form
          </button>
        </div>
      ) : (
        <div
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            overflow: "hidden",
          }}
        >
          {/* Table header */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "2fr 120px 100px 130px 200px",
              padding: "10px 16px",
              borderBottom: "1px solid var(--border)",
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            <span>Form</span>
            <span style={{ textAlign: "center" }}>Submissions</span>
            <span style={{ textAlign: "center" }}>Status</span>
            <span>Created</span>
            <span style={{ textAlign: "right" }}>Actions</span>
          </div>

          {forms.map((form) => {
            const isDeleting = deletingIds.has(form.id);
            const isActive = form.is_active !== false;
            const subCount = form.submission_count ?? form.submissions_count ?? 0;

            return (
              <div
                key={form.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "2fr 120px 100px 130px 200px",
                  padding: "12px 16px",
                  borderBottom: "1px solid var(--border)",
                  alignItems: "center",
                  opacity: isDeleting ? 0.5 : 1,
                  transition: "background 0.1s ease",
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = "var(--hover-overlay)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
              >
                {/* Name + description */}
                <div>
                  <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-primary)", marginBottom: 2 }}>
                    {form.name}
                  </div>
                  {form.description && (
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 300 }}>
                      {form.description}
                    </div>
                  )}
                </div>

                {/* Submission count */}
                <div style={{ textAlign: "center", fontSize: "0.9rem", fontWeight: 600, color: "#8b5cf6" }}>
                  {subCount}
                </div>

                {/* Status */}
                <div style={{ textAlign: "center" }}>
                  <StatusBadge active={isActive} />
                </div>

                {/* Created */}
                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  {formatDate(form.created_at)}
                </div>

                {/* Actions */}
                <div style={{ display: "flex", gap: 4, justifyContent: "flex-end" }}>
                  <button
                    onClick={() => openEdit(form)}
                    style={{
                      background: "rgba(59,130,246,0.1)",
                      border: "1px solid rgba(59,130,246,0.3)",
                      borderRadius: 6,
                      padding: "4px 10px",
                      color: "#3b82f6",
                      cursor: "pointer",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                    }}
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => openSubmissions(form)}
                    style={{
                      background: "rgba(139,92,246,0.1)",
                      border: "1px solid rgba(139,92,246,0.3)",
                      borderRadius: 6,
                      padding: "4px 10px",
                      color: "#8b5cf6",
                      cursor: "pointer",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                    }}
                  >
                    Subs
                  </button>
                  <button
                    onClick={() => copyToClipboard(getDirectLink(form), "link")}
                    style={{
                      background: "none",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      padding: "4px 8px",
                      color: copiedEmbed === "link" ? "#22c55e" : "var(--text-secondary)",
                      cursor: "pointer",
                      fontSize: "0.75rem",
                    }}
                    title="Copy form link"
                  >
                    {copiedEmbed === "link" ? "Copied!" : "Link"}
                  </button>
                  <button
                    onClick={() => handleDelete(form.id)}
                    disabled={isDeleting}
                    style={{
                      background: "none",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      padding: "4px 8px",
                      color: "#ef4444",
                      cursor: "pointer",
                      fontSize: "0.75rem",
                    }}
                  >
                    {isDeleting ? "..." : "Del"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
