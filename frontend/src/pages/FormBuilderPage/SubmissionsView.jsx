import SkeletonLoader from "../../components/SkeletonLoader";
import { formatDate, getDirectLink, getEmbedIframe } from "./utils";

export default function SubmissionsView({
  viewingSubmissions,
  submissions,
  loadingSubs,
  expandedSubId,
  setExpandedSubId,
  setViewingSubmissions,
  copyToClipboard,
  copiedEmbed,
}) {
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
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            color: "var(--text-muted)",
          }}
        >
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>
            No submissions yet
          </div>
          <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
            This form has not received any submissions. Share the form link or
            embed it on your website to start collecting responses.
          </p>
          <div
            style={{
              display: "flex",
              gap: 8,
              justifyContent: "center",
              flexWrap: "wrap",
            }}
          >
            <button
              onClick={() =>
                copyToClipboard(getDirectLink(viewingSubmissions), "link")
              }
              className="btn-primary"
            >
              {copiedEmbed === "link" ? "Copied!" : "Copy Form Link"}
            </button>
            <button
              onClick={() =>
                copyToClipboard(getEmbedIframe(viewingSubmissions), "iframe")
              }
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
            const submissionData =
              sub.data_json || sub.data || sub.submission_data || {};
            const summaryParts = Object.values(submissionData)
              .filter(Boolean)
              .slice(0, 3);
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
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "var(--hover-overlay)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "transparent";
                  }}
                >
                  <span
                    style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}
                  >
                    {idx + 1}
                  </span>
                  <span
                    style={{
                      fontSize: "0.85rem",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {summaryText}
                  </span>
                  <span
                    style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}
                  >
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
                      <span
                        style={{
                          fontSize: "0.75rem",
                          color: "var(--text-muted)",
                        }}
                      >
                        --
                      </span>
                    )}
                  </span>
                </div>
                {isExpanded && (
                  <div
                    style={{
                      padding: "12px 16px 12px 76px",
                      background: "var(--bg-primary)",
                      borderBottom: "1px solid var(--border)",
                    }}
                  >
                    {Object.entries(submissionData).map(([key, val]) => (
                      <div
                        key={key}
                        style={{ marginBottom: 6, fontSize: "0.85rem" }}
                      >
                        <span
                          style={{
                            color: "var(--text-muted)",
                            fontWeight: 600,
                            marginRight: 8,
                          }}
                        >
                          {key}:
                        </span>
                        <span style={{ color: "var(--text-secondary)" }}>
                          {typeof val === "boolean"
                            ? val
                              ? "Yes"
                              : "No"
                            : String(val || "-")}
                        </span>
                      </div>
                    ))}
                    {Object.keys(submissionData).length === 0 && (
                      <div
                        style={{
                          fontSize: "0.85rem",
                          color: "var(--text-muted)",
                        }}
                      >
                        No data recorded
                      </div>
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
