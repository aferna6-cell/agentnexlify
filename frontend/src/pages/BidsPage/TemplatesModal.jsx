export default function TemplatesModal({
  showTemplates,
  setShowTemplates,
  templates,
  templatesLoading,
  handleUseTemplate,
  handleDeleteTemplate,
}) {
  if (!showTemplates) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={() => setShowTemplates(false)}
    >
      <div
        style={{
          background: "var(--bg-primary)",
          borderRadius: 12,
          padding: 24,
          width: "90%",
          maxWidth: 520,
          maxHeight: "80vh",
          overflowY: "auto",
          border: "1px solid var(--border)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ marginBottom: 16 }}>Bid Templates</h3>

        {templatesLoading ? (
          <div
            style={{
              textAlign: "center",
              padding: "30px 0",
              color: "var(--text-muted)",
            }}
          >
            Loading templates...
          </div>
        ) : templates.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "30px 20px",
              color: "var(--text-muted)",
            }}
          >
            <div style={{ fontSize: "1.1rem", marginBottom: 8 }}>
              No templates saved yet
            </div>
            <p style={{ fontSize: "0.85rem", maxWidth: 360, margin: "0 auto" }}>
              When viewing a bid, click "Save as Template" to reuse it for
              future bids.
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {templates.map((tmpl) => (
              <div
                key={tmpl.id}
                style={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: 12,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>
                    {tmpl.name}
                  </div>
                  <div
                    style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}
                  >
                    {(tmpl.line_items || []).length} items
                  </div>
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                  <button
                    onClick={() => handleUseTemplate(tmpl)}
                    style={{
                      background: "var(--accent-dim)",
                      border: "1px solid var(--accent)",
                      borderRadius: 6,
                      padding: "6px 12px",
                      color: "var(--accent)",
                      cursor: "pointer",
                      fontSize: "0.8rem",
                      fontWeight: 600,
                    }}
                  >
                    Use
                  </button>
                  <button
                    onClick={() => handleDeleteTemplate(tmpl.id)}
                    style={{
                      background: "none",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      padding: "6px 10px",
                      color: "#ef4444",
                      cursor: "pointer",
                      fontSize: "0.8rem",
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            marginTop: 16,
          }}
        >
          <button
            onClick={() => setShowTemplates(false)}
            className="btn-primary"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
