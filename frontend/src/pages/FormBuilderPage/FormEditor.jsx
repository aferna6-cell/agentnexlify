import FormPreview from "./FormPreview";
import { FIELD_TYPES, getDirectLink, getEmbedIframe } from "./utils";

export default function FormEditor({
  formData,
  setFormData,
  editingForm,
  saving,
  error,
  setError,
  setShowEditor,
  setEditingForm,
  handleSave,
  addField,
  removeField,
  updateField,
  moveField,
  updateSettings,
  copyToClipboard,
  copiedEmbed,
}) {
  const hasOptionsType = ["select", "radio", "checkbox"];

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <button
            onClick={() => {
              setShowEditor(false);
              setEditingForm(null);
            }}
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
            onClick={() => {
              setShowEditor(false);
              setEditingForm(null);
            }}
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
            disabled={
              !formData.name.trim() || formData.fields.length === 0 || saving
            }
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
            style={{
              marginLeft: 12,
              background: "none",
              border: "none",
              color: "#ef4444",
              cursor: "pointer",
              fontSize: "0.8rem",
              textDecoration: "underline",
            }}
          >
            dismiss
          </button>
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 20,
          alignItems: "start",
        }}
      >
        <div>
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
              <label
                style={{
                  display: "block",
                  fontSize: "0.8rem",
                  marginBottom: 4,
                  color: "var(--text-secondary)",
                  fontWeight: 600,
                }}
              >
                Form Name *
              </label>
              <input
                value={formData.name}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder="e.g., Contact Form, Quote Request"
                style={{ width: "100%", boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "0.8rem",
                  marginBottom: 4,
                  color: "var(--text-secondary)",
                  fontWeight: 600,
                }}
              >
                Description
              </label>
              <input
                value={formData.description}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    description: e.target.value,
                  }))
                }
                placeholder="A short description for your visitors"
                style={{ width: "100%", boxSizing: "border-box" }}
              />
            </div>
          </div>

          <div
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: 20,
              marginBottom: 16,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 14,
              }}
            >
              <div
                style={{
                  fontSize: "0.85rem",
                  fontWeight: 700,
                  color: "var(--text-primary)",
                }}
              >
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
              <div
                style={{
                  textAlign: "center",
                  padding: "24px 12px",
                  color: "var(--text-muted)",
                  fontSize: "0.85rem",
                }}
              >
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
                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                    marginBottom: 10,
                  }}
                >
                  <select
                    value={field.type}
                    onChange={(e) => updateField(idx, "type", e.target.value)}
                    style={{ flex: "0 0 130px", fontSize: "0.8rem" }}
                  >
                    {FIELD_TYPES.map((ft) => (
                      <option key={ft.value} value={ft.value}>
                        {ft.label}
                      </option>
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
                        color:
                          idx === 0 ? "var(--border)" : "var(--text-secondary)",
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
                        color:
                          idx === formData.fields.length - 1
                            ? "var(--border)"
                            : "var(--text-secondary)",
                        cursor:
                          idx === formData.fields.length - 1
                            ? "default"
                            : "pointer",
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

                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input
                    value={field.placeholder}
                    onChange={(e) =>
                      updateField(idx, "placeholder", e.target.value)
                    }
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
                      onChange={(e) =>
                        updateField(idx, "required", e.target.checked)
                      }
                      style={{ width: "auto" }}
                    />
                    Required
                  </label>
                </div>

                {hasOptionsType.includes(field.type) && (
                  <div style={{ marginTop: 8 }}>
                    <label
                      style={{
                        display: "block",
                        fontSize: "0.75rem",
                        marginBottom: 4,
                        color: "var(--text-muted)",
                        fontWeight: 600,
                      }}
                    >
                      Options (one per line or comma-separated)
                    </label>
                    <textarea
                      value={(field.options || []).join("\n")}
                      onChange={(e) => {
                        const raw = e.target.value;
                        const opts = raw.includes(",")
                          ? raw
                              .split(",")
                              .map((s) => s.trim())
                              .filter(Boolean)
                          : raw.split("\n").filter((s) => s.trim());
                        updateField(idx, "options", opts);
                      }}
                      placeholder={"Option 1\nOption 2\nOption 3"}
                      rows={3}
                      style={{
                        width: "100%",
                        resize: "vertical",
                        fontSize: "0.8rem",
                        boxSizing: "border-box",
                      }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>

          <div
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: 20,
              marginBottom: 16,
            }}
          >
            <div
              style={{
                fontSize: "0.85rem",
                fontWeight: 700,
                color: "var(--text-primary)",
                marginBottom: 14,
              }}
            >
              Settings
            </div>
            <div style={{ marginBottom: 12 }}>
              <label
                style={{
                  display: "block",
                  fontSize: "0.8rem",
                  marginBottom: 4,
                  color: "var(--text-secondary)",
                  fontWeight: 600,
                }}
              >
                Success Message
              </label>
              <textarea
                value={formData.settings.success_message}
                onChange={(e) =>
                  updateSettings("success_message", e.target.value)
                }
                placeholder="Message shown after submission"
                rows={2}
                style={{
                  width: "100%",
                  resize: "vertical",
                  boxSizing: "border-box",
                }}
              />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label
                style={{
                  display: "block",
                  fontSize: "0.8rem",
                  marginBottom: 4,
                  color: "var(--text-secondary)",
                  fontWeight: 600,
                }}
              >
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

          {editingForm && (
            <div
              style={{
                background: "var(--bg-secondary)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: 20,
              }}
            >
              <div
                style={{
                  fontSize: "0.85rem",
                  fontWeight: 700,
                  color: "var(--text-primary)",
                  marginBottom: 14,
                }}
              >
                Embed Code
              </div>
              <div style={{ marginBottom: 12 }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.75rem",
                    marginBottom: 4,
                    color: "var(--text-muted)",
                    fontWeight: 600,
                    textTransform: "uppercase",
                  }}
                >
                  Direct Link
                </label>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input
                    readOnly
                    value={getDirectLink(editingForm)}
                    style={{
                      flex: 1,
                      fontSize: "0.8rem",
                      background: "var(--bg-primary)",
                    }}
                  />
                  <button
                    onClick={() =>
                      copyToClipboard(getDirectLink(editingForm), "link")
                    }
                    style={{
                      background:
                        copiedEmbed === "link"
                          ? "rgba(34,197,94,0.1)"
                          : "var(--bg-primary)",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      padding: "6px 12px",
                      color:
                        copiedEmbed === "link"
                          ? "#22c55e"
                          : "var(--text-secondary)",
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
                <label
                  style={{
                    display: "block",
                    fontSize: "0.75rem",
                    marginBottom: 4,
                    color: "var(--text-muted)",
                    fontWeight: 600,
                    textTransform: "uppercase",
                  }}
                >
                  Embed (iframe)
                </label>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input
                    readOnly
                    value={getEmbedIframe(editingForm)}
                    style={{
                      flex: 1,
                      fontSize: "0.75rem",
                      background: "var(--bg-primary)",
                      fontFamily: "monospace",
                    }}
                  />
                  <button
                    onClick={() =>
                      copyToClipboard(getEmbedIframe(editingForm), "iframe")
                    }
                    style={{
                      background:
                        copiedEmbed === "iframe"
                          ? "rgba(34,197,94,0.1)"
                          : "var(--bg-primary)",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      padding: "6px 12px",
                      color:
                        copiedEmbed === "iframe"
                          ? "#22c55e"
                          : "var(--text-secondary)",
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

        <div style={{ position: "sticky", top: 20 }}>
          <div
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: 16,
            }}
          >
            <div
              style={{
                fontSize: "0.75rem",
                fontWeight: 600,
                textTransform: "uppercase",
                color: "var(--text-muted)",
                marginBottom: 10,
                letterSpacing: "0.05em",
              }}
            >
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
