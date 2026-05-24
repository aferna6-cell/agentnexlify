export default function DuplicatesModal({
  duplicates,
  merging,
  onMerge,
  onClose,
}) {
  if (duplicates === null) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: 600, maxHeight: "80vh", overflow: "auto" }}
      >
        <h3>Duplicate Leads</h3>
        {duplicates.length === 0 ? (
          <p style={{ color: "var(--text-muted)" }}>No duplicates found.</p>
        ) : (
          duplicates.map((dup, i) => (
            <div
              key={i}
              style={{
                marginBottom: 16,
                padding: 12,
                background: "var(--bg-secondary)",
                borderRadius: 8,
                border: "1px solid var(--border)",
              }}
            >
              <div
                style={{
                  fontSize: "0.8rem",
                  color: "var(--text-muted)",
                  marginBottom: 8,
                }}
              >
                Match: {dup.match_field} = {dup.match_value}
              </div>
              {dup.leads.map((lead) => (
                <div
                  key={lead.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "6px 0",
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600 }}>
                      {lead.name || "No name"}
                    </div>
                    <div
                      style={{
                        fontSize: "0.8rem",
                        color: "var(--text-muted)",
                      }}
                    >
                      {lead.email || ""} {lead.phone || ""}
                    </div>
                    <div
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--text-muted)",
                      }}
                    >
                      Score: {lead.lead_score ?? "N/A"} | {lead.status}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 4 }}>
                    {dup.leads
                      .filter((l) => l.id !== lead.id)
                      .map((other) => (
                        <button
                          key={other.id}
                          className="btn-sm"
                          disabled={merging}
                          onClick={() => onMerge(lead.id, other.id)}
                          title={`Keep this, merge ${other.name || other.email || "other"} into it`}
                        >
                          Keep this
                        </button>
                      ))}
                  </div>
                </div>
              ))}
            </div>
          ))
        )}
        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
