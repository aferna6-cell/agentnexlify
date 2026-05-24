import StatusBadge from "./StatusBadge";
import { formatDate, getDirectLink } from "./utils";

export default function FormsGrid({
  forms,
  totalForms,
  totalSubmissions,
  activeForms,
  conversionRate,
  error,
  setError,
  setLoading,
  loadData,
  openCreate,
  openEdit,
  openSubmissions,
  copyToClipboard,
  copiedEmbed,
  handleDelete,
  deletingIds,
}) {
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
            onClick={() => {
              setLoading(true);
              loadData();
            }}
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
          {
            label: "Total Submissions",
            value: totalSubmissions,
            color: "#8b5cf6",
          },
          { label: "Active Forms", value: activeForms, color: "#22c55e" },
          {
            label: "Conversion Rate",
            value: conversionRate ? `${conversionRate}%` : "---",
            color: "#f59e0b",
          },
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
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                marginBottom: 4,
              }}
            >
              {card.label}
            </div>
            <div
              style={{ fontSize: "1.5rem", fontWeight: 700, color: card.color }}
            >
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

      {forms.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            color: "var(--text-muted)",
          }}
        >
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>No forms yet</div>
          <p style={{ maxWidth: 520, margin: "0 auto 20px", lineHeight: 1.6 }}>
            Create your first form to start capturing leads. Forms can be
            embedded on any website or shared via a direct link. Submissions
            automatically create leads in your CRM.
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
            const subCount =
              form.submission_count ?? form.submissions_count ?? 0;

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
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "var(--hover-overlay)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                }}
              >
                <div>
                  <div
                    style={{
                      fontWeight: 600,
                      fontSize: "0.9rem",
                      color: "var(--text-primary)",
                      marginBottom: 2,
                    }}
                  >
                    {form.name}
                  </div>
                  {form.description && (
                    <div
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--text-muted)",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        maxWidth: 300,
                      }}
                    >
                      {form.description}
                    </div>
                  )}
                </div>

                <div
                  style={{
                    textAlign: "center",
                    fontSize: "0.9rem",
                    fontWeight: 600,
                    color: "#8b5cf6",
                  }}
                >
                  {subCount}
                </div>

                <div style={{ textAlign: "center" }}>
                  <StatusBadge active={isActive} />
                </div>

                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  {formatDate(form.created_at)}
                </div>

                <div
                  style={{
                    display: "flex",
                    gap: 4,
                    justifyContent: "flex-end",
                  }}
                >
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
                      color:
                        copiedEmbed === "link"
                          ? "#22c55e"
                          : "var(--text-secondary)",
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
