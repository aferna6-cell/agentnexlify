import { overlay, modalBase, fieldLabel, cancelBtn } from "./styles";

export default function DocumentModal({
  form,
  setForm,
  templates,
  selectedTemplateId,
  onTemplateSelect,
  leads,
  loadingDropdowns,
  saving,
  savingTemplate,
  onClose,
  onSave,
  onSaveAsTemplate,
}) {
  return (
    <div style={overlay} onClick={onClose}>
      <div
        style={{
          ...modalBase,
          width: "90%",
          maxWidth: 640,
          maxHeight: "88vh",
          overflowY: "auto",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ marginBottom: 16 }}>Create Document</h3>

        {templates.length > 0 && (
          <div
            style={{
              background: "rgba(139,92,246,0.08)",
              border: "1px solid rgba(139,92,246,0.2)",
              borderRadius: 8,
              padding: 12,
              marginBottom: 16,
            }}
          >
            <div
              style={{
                fontSize: "0.8rem",
                fontWeight: 600,
                color: "#8b5cf6",
                marginBottom: 8,
              }}
            >
              Start from Template
            </div>
            <select
              value={selectedTemplateId}
              onChange={(e) => onTemplateSelect(e.target.value)}
              style={{ width: "100%", fontSize: "0.85rem" }}
            >
              <option value="">Blank document</option>
              {templates.map((tmpl) => (
                <option key={tmpl.id} value={tmpl.id}>
                  {tmpl.name}
                </option>
              ))}
            </select>
            <div
              style={{
                fontSize: "0.7rem",
                color: "var(--text-muted)",
                marginTop: 4,
              }}
            >
              Select a saved template to pre-fill the document content
            </div>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <label style={fieldLabel}>Document Title *</label>
            <input
              value={form.title}
              onChange={(e) =>
                setForm((f) => ({ ...f, title: e.target.value }))
              }
              placeholder="e.g. Service Agreement, NDA, Consent Form"
              style={{ width: "100%" }}
            />
          </div>

          <div>
            <label style={fieldLabel}>Document Content (HTML)</label>
            <textarea
              value={form.html_content}
              onChange={(e) =>
                setForm((f) => ({ ...f, html_content: e.target.value }))
              }
              placeholder={
                "<h2>Service Agreement</h2>\n<p>This agreement is entered into by...</p>\n<p>Signature: _______________</p>"
              }
              rows={8}
              style={{
                width: "100%",
                resize: "vertical",
                fontFamily: "monospace",
                fontSize: "0.8rem",
              }}
            />
            <div
              style={{
                fontSize: "0.7rem",
                color: "var(--text-muted)",
                marginTop: 4,
              }}
            >
              Use HTML tags for formatting. The signer will see this as a
              formatted document.
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 12,
            }}
          >
            <div>
              <label style={fieldLabel}>Signer Name</label>
              <input
                value={form.signer_name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, signer_name: e.target.value }))
                }
                placeholder="John Smith"
                style={{ width: "100%" }}
              />
            </div>
            <div>
              <label style={fieldLabel}>Signer Email</label>
              <input
                type="email"
                value={form.signer_email}
                onChange={(e) =>
                  setForm((f) => ({ ...f, signer_email: e.target.value }))
                }
                placeholder="john@example.com"
                style={{ width: "100%" }}
              />
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 12,
            }}
          >
            <div>
              <label style={fieldLabel}>Signer Phone</label>
              <input
                type="tel"
                value={form.signer_phone}
                onChange={(e) =>
                  setForm((f) => ({ ...f, signer_phone: e.target.value }))
                }
                placeholder="+1 555-123-4567"
                style={{ width: "100%" }}
              />
            </div>
            <div>
              <label style={fieldLabel}>Expiry (days)</label>
              <input
                type="number"
                value={form.expiry_days}
                onChange={(e) =>
                  setForm((f) => ({ ...f, expiry_days: e.target.value }))
                }
                min={1}
                max={365}
                style={{ width: "100%" }}
              />
            </div>
          </div>

          <div>
            <label style={fieldLabel}>Link to Lead (optional)</label>
            {loadingDropdowns ? (
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                Loading leads...
              </div>
            ) : (
              <select
                value={form.lead_id}
                onChange={(e) => {
                  const leadId = e.target.value;
                  setForm((f) => ({ ...f, lead_id: leadId }));
                  if (leadId) {
                    const lead = leads.find((l) => l.id === leadId);
                    if (lead)
                      setForm((f) => ({
                        ...f,
                        lead_id: leadId,
                        signer_name: f.signer_name || lead.name || "",
                        signer_email: f.signer_email || lead.email || "",
                        signer_phone: f.signer_phone || lead.phone || "",
                      }));
                  }
                }}
                style={{ width: "100%" }}
              >
                <option value="">No lead linked</option>
                {leads.map((lead) => (
                  <option key={lead.id} value={lead.id}>
                    {lead.name || lead.email || lead.phone || lead.id}
                  </option>
                ))}
              </select>
            )}
            <div
              style={{
                fontSize: "0.7rem",
                color: "var(--text-muted)",
                marginTop: 4,
              }}
            >
              Selecting a lead will auto-fill signer details if they are empty
            </div>
          </div>

          <div>
            <label style={fieldLabel}>Internal Notes</label>
            <textarea
              value={form.notes}
              onChange={(e) =>
                setForm((f) => ({ ...f, notes: e.target.value }))
              }
              placeholder="Internal notes about this document (not visible to signer)..."
              rows={2}
              style={{ width: "100%", resize: "vertical" }}
            />
          </div>
        </div>

        <div
          style={{
            display: "flex",
            gap: 8,
            marginTop: 20,
            justifyContent: "flex-end",
          }}
        >
          {form.title.trim() && form.html_content.trim() && (
            <button
              onClick={onSaveAsTemplate}
              disabled={savingTemplate}
              style={{
                background: "transparent",
                border: "1px solid rgba(139,92,246,0.4)",
                borderRadius: 8,
                padding: "8px 16px",
                color: "#8b5cf6",
                cursor: "pointer",
                fontSize: "0.8rem",
                marginRight: "auto",
              }}
            >
              {savingTemplate ? "Saving..." : "Save as Template"}
            </button>
          )}
          <button onClick={onClose} style={cancelBtn}>
            Cancel
          </button>
          <button
            className="btn-primary"
            onClick={onSave}
            disabled={!form.title.trim() || saving}
          >
            {saving ? "Creating..." : "Create Document"}
          </button>
        </div>
      </div>
    </div>
  );
}
