export default function InfoSection({ lead }) {
  return (
    <div className="intel-section">
      <div className="intel-title">Info</div>
      <div className="intel-row">
        <span className="intel-label">Created</span>
        <span className="intel-value">
          {lead.created_at
            ? new Date(lead.created_at).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
              })
            : "Unknown"}
        </span>
      </div>
      {lead.conversation_id && (
        <div className="intel-row">
          <span className="intel-label">Conversation</span>
          <span className="intel-value" style={{ color: "var(--accent)" }}>
            Linked
          </span>
        </div>
      )}
    </div>
  );
}
