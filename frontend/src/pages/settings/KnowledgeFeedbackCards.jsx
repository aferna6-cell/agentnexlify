export function AiKnowledgeSourcesCard({ knowledgeStats, onNavigate }) {
  if (!knowledgeStats) return null;

  return (
    <div className="settings-card">
      <h3>AI Knowledge Sources</h3>
      <p className="settings-card-desc">
        What your AI chatbot currently knows. The more sources, the better your
        AI can help visitors.
      </p>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 12,
          marginTop: 12,
        }}
      >
        <KnowledgeStatCard
          value={knowledgeStats.faq_count}
          label="FAQ Entries"
          color={knowledgeStats.faq_count > 0 ? "#22c55e" : "var(--text-muted)"}
        >
          {knowledgeStats.faq_count === 0 && (
            <button onClick={() => onNavigate?.("faq")} style={linkButtonStyle}>
              Add FAQs
            </button>
          )}
        </KnowledgeStatCard>
        <KnowledgeStatCard
          value={knowledgeStats.website_pages_crawled}
          label="Website Pages Crawled"
          color={
            knowledgeStats.website_pages_crawled > 0
              ? "#22c55e"
              : "var(--text-muted)"
          }
        >
          {knowledgeStats.website_crawl_status && (
            <div
              style={{
                fontSize: 11,
                color:
                  knowledgeStats.website_crawl_status === "completed"
                    ? "#22c55e"
                    : "#f59e0b",
                marginTop: 2,
              }}
            >
              Status: {knowledgeStats.website_crawl_status}
            </div>
          )}
        </KnowledgeStatCard>
        <KnowledgeStatCard
          value={knowledgeStats.feedback_corrections_count}
          label="AI Corrections"
          color={
            knowledgeStats.feedback_corrections_count > 0
              ? "#f59e0b"
              : "var(--text-muted)"
          }
        >
          <div style={mutedTinyStyle}>From thumbs-down feedback</div>
        </KnowledgeStatCard>
        {knowledgeStats.active_chat_flow && (
          <div style={statCardStyle}>
            <div style={{ fontSize: 16, fontWeight: 600, color: "#8b5cf6" }}>
              Active
            </div>
            <div style={statLabelStyle}>
              Chat Flow: {knowledgeStats.active_chat_flow}
            </div>
          </div>
        )}
        {knowledgeStats.menu_items_count > 0 && (
          <KnowledgeStatCard
            value={knowledgeStats.menu_items_count}
            label="Menu Items"
            color="#22c55e"
          />
        )}
        {knowledgeStats.job_postings_count > 0 && (
          <KnowledgeStatCard
            value={knowledgeStats.job_postings_count}
            label="Active Job Postings"
            color="#22c55e"
          />
        )}
      </div>
    </div>
  );
}

function KnowledgeStatCard({ value, label, color, children }) {
  return (
    <div style={statCardStyle}>
      <div style={{ fontSize: 24, fontWeight: 700, color }}>{value}</div>
      <div style={statLabelStyle}>{label}</div>
      {children}
    </div>
  );
}

export function AiResponseFeedbackCard({ feedback, handleDeleteFeedback }) {
  return (
    <div className="settings-card">
      <h3>AI Response Feedback</h3>
      <p className="settings-card-desc">
        Visitor ratings on your AI assistant's responses. Corrections from
        thumbs-down feedback are automatically used to improve future responses.
      </p>
      {feedback.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          No feedback yet. Visitors can rate AI responses with thumbs up/down in
          the chat widget.
        </p>
      ) : (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 8,
            marginTop: 8,
          }}
        >
          {feedback.slice(0, 20).map((fb) => (
            <FeedbackRow
              key={fb.id}
              feedback={fb}
              handleDeleteFeedback={handleDeleteFeedback}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function FeedbackRow({ feedback, handleDeleteFeedback }) {
  const positive = feedback.rating === "thumbs_up";

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        padding: "8px 12px",
        borderRadius: 8,
        fontSize: "0.85rem",
        background: positive ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)",
        border: `1px solid ${
          positive ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)"
        }`,
      }}
    >
      <div>
        <span style={{ marginRight: 8 }}>{positive ? "\u{1F44D}" : "\u{1F44E}"}</span>
        {feedback.correction ? (
          <span>{feedback.correction}</span>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>
            {positive ? "Positive rating" : "Negative rating (no correction)"}
          </span>
        )}
        <div
          style={{
            fontSize: "0.75rem",
            color: "var(--text-muted)",
            marginTop: 4,
          }}
        >
          {new Date(feedback.created_at).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
          })}
        </div>
      </div>
      <button
        onClick={() => handleDeleteFeedback(feedback.id)}
        style={{
          background: "none",
          border: "none",
          color: "var(--text-muted)",
          cursor: "pointer",
          fontSize: "0.8rem",
        }}
      >
        dismiss
      </button>
    </div>
  );
}

const statCardStyle = {
  padding: "12px 16px",
  borderRadius: 8,
  background: "var(--bg-secondary)",
  border: "1px solid var(--border)",
};

const statLabelStyle = {
  fontSize: 13,
  color: "var(--text-secondary)",
};

const mutedTinyStyle = {
  fontSize: 11,
  color: "var(--text-muted)",
  marginTop: 2,
};

const linkButtonStyle = {
  fontSize: 12,
  color: "var(--accent)",
  background: "none",
  border: "none",
  cursor: "pointer",
  padding: 0,
  marginTop: 4,
};
