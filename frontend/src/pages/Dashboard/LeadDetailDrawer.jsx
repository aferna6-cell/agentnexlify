function scoreClass(score) {
  if (score >= 70) return "score-hot";
  if (score >= 40) return "score-warm";
  return "score-cold";
}

function scoreLabel(score) {
  if (score >= 70) return "Hot";
  if (score >= 40) return "Warm";
  return "Cold";
}

function scoreColor(score) {
  if (score >= 70) return "var(--red)";
  if (score >= 40) return "var(--yellow)";
  return "var(--accent)";
}

export default function LeadDetailDrawer({ lead, onClose }) {
  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <h2 className="drawer-title">{lead.name || "Unknown Lead"}</h2>
          <button className="drawer-close" onClick={onClose}>&times;</button>
        </div>

        <div className="drawer-body">
          {/* Score */}
          <div className="lead-score-display">
            <div>
              <div className="lead-score-label">Lead Score</div>
              <div className="lead-score-value" style={{ color: scoreColor(lead.lead_score) }}>
                {lead.lead_score ?? "N/A"} / 100
              </div>
            </div>
            <span
              className={`lead-tag ${scoreClass(lead.lead_score)}`}
              style={{ marginLeft: "auto", fontSize: 13 }}
            >
              {scoreLabel(lead.lead_score)}
            </span>
          </div>

          {/* Contact Info */}
          <div className="intel-section">
            <div className="intel-title">Contact Info</div>
            <div className="intel-row">
              <span className="intel-label">Email</span>
              <span className={`intel-value${!lead.email ? " empty" : ""}`}>
                {lead.email || "Not provided"}
              </span>
            </div>
            <div className="intel-row">
              <span className="intel-label">Phone</span>
              <span className={`intel-value${!lead.phone ? " empty" : ""}`}>
                {lead.phone || "Not provided"}
              </span>
            </div>
          </div>

          {/* Lead Details */}
          <div className="intel-section">
            <div className="intel-title">Details</div>
            <div className="intel-row">
              <span className="intel-label">Type</span>
              <span className={`intel-value${!lead.lead_type ? " empty" : ""}`}>
                {lead.lead_type || "Unknown"}
              </span>
            </div>
            <div className="intel-row">
              <span className="intel-label">Timeline</span>
              <span className={`intel-value${!lead.timeline ? " empty" : ""}`}>
                {lead.timeline || "Not specified"}
              </span>
            </div>
            <div className="intel-row">
              <span className="intel-label">Budget</span>
              <span className={`intel-value${!lead.budget ? " empty" : ""}`}>
                {lead.budget || "Not specified"}
              </span>
            </div>
            <div className="intel-row">
              <span className="intel-label">Areas of Interest</span>
              <span className={`intel-value${!lead.areas_of_interest ? " empty" : ""}`}>
                {lead.areas_of_interest || "None"}
              </span>
            </div>
            <div className="intel-row">
              <span className="intel-label">Must Haves</span>
              <span className={`intel-value${!lead.must_haves ? " empty" : ""}`}>
                {lead.must_haves || "None"}
              </span>
            </div>
            <div className="intel-row">
              <span className="intel-label">Pre-Approved</span>
              <span className="intel-value">
                {lead.pre_approved === true ? "Yes" : lead.pre_approved === false ? "No" : "Unknown"}
              </span>
            </div>
          </div>

          {/* Conversation Summary */}
          {lead.conversation_summary && (
            <div className="intel-section">
              <div className="intel-title">Conversation Summary</div>
              <p className="drawer-summary">{lead.conversation_summary}</p>
            </div>
          )}

          {/* Next Steps */}
          {lead.next_steps && (
            <div className="intel-section">
              <div className="intel-title">Next Steps</div>
              <p className="drawer-summary">{lead.next_steps}</p>
            </div>
          )}

          {/* Status */}
          <div className="intel-section">
            <div className="intel-title">Status</div>
            <div className="intel-row">
              <span className="intel-label">Stage</span>
              <span className="intel-value">{lead.lead_stage || "new"}</span>
            </div>
            {lead.appointment_date && (
              <div className="intel-row">
                <span className="intel-label">Appointment</span>
                <span className="intel-value">
                  {new Date(lead.appointment_date).toLocaleDateString("en-US", {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                    hour: "numeric",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
