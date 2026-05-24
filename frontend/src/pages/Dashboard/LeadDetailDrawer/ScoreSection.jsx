import {
  scoreClass,
  scoreLabel,
  scoreColor,
  temperatureBadge,
} from "./helpers";

function GenericScoreFactors({ lead }) {
  const factors = [
    { label: "Has email", met: !!lead.email, points: 20 },
    { label: "Has phone", met: !!lead.phone, points: 15 },
    { label: "Has name", met: !!lead.name, points: 10 },
    {
      label: "Has conversation",
      met: !!lead.conversation_id || !!lead.session_id,
      points: 10,
    },
    {
      label: "Booked appointment",
      met: lead.status === "appointment_booked",
      points: 25,
    },
  ];
  const earned = factors
    .filter((f) => f.met)
    .reduce((sum, f) => sum + f.points, 0);

  return (
    <div className="score-factors-section">
      <div className="score-factors-header">
        <span
          style={{
            fontSize: "0.78rem",
            color: "var(--text-muted)",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.5px",
          }}
        >
          Score Factors
        </span>
        <span style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
          {earned} pts from profile
        </span>
      </div>
      <div className="score-factors-list">
        {factors.map((f) => (
          <div key={f.label} className="score-factor-row">
            <span className="score-factor-left">
              {f.met ? (
                <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
                  <circle cx="10" cy="10" r="10" fill="var(--green)" />
                  <path
                    d="M6 10l3 3 5-6"
                    stroke="white"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              ) : (
                <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
                  <circle cx="10" cy="10" r="10" fill="var(--border)" />
                  <path
                    d="M7 7l6 6M13 7l-6 6"
                    stroke="var(--text-muted)"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>
              )}
              <span
                style={{
                  color: f.met ? "var(--text-primary)" : "var(--text-muted)",
                  fontSize: "0.8rem",
                }}
              >
                {f.label}
              </span>
            </span>
            <span
              style={{
                fontSize: "0.78rem",
                fontWeight: 600,
                color: f.met ? "var(--green)" : "var(--text-muted)",
              }}
            >
              {f.met ? `+${f.points}` : `+${f.points}`}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScoreBreakdown({ breakdown }) {
  if (!breakdown) return null;
  const eng = breakdown.engagement?.total || 0;
  const int = breakdown.intent?.total || 0;
  const rec = breakdown.recency?.total || 0;
  const dec = breakdown.decay?.total || 0;
  const total = eng + int + rec;

  return (
    <div className="score-breakdown">
      <div className="score-stacked-bar">
        {total > 0 && (
          <>
            <div
              className="bar-segment engagement"
              style={{ width: `${(eng / total) * 100}%` }}
            />
            <div
              className="bar-segment intent"
              style={{ width: `${(int / total) * 100}%` }}
            />
            <div
              className="bar-segment recency"
              style={{ width: `${(rec / total) * 100}%` }}
            />
          </>
        )}
      </div>
      <div className="score-category-row">
        <span className="score-category-left">
          <span className="score-dot engagement" />{" "}
          <span className="score-category-label">Engagement</span>
        </span>
        <span className="score-category-value">
          {eng} / {breakdown.engagement?.max || 40}
        </span>
      </div>
      <div className="score-category-row">
        <span className="score-category-left">
          <span className="score-dot intent" />{" "}
          <span className="score-category-label">Intent</span>
        </span>
        <span className="score-category-value">
          {int} / {breakdown.intent?.max || 40}
        </span>
      </div>
      <div className="score-category-row">
        <span className="score-category-left">
          <span className="score-dot recency" />{" "}
          <span className="score-category-label">Recency</span>
        </span>
        <span className="score-category-value">
          {rec} / {breakdown.recency?.max || 20}
        </span>
      </div>
      {dec > 0 && (
        <div className="score-category-row">
          <span className="score-category-left">
            <span className="score-dot decay" />{" "}
            <span className="score-category-label">Decay</span>
          </span>
          <span className="score-category-value decay">-{dec}</span>
        </div>
      )}
    </div>
  );
}

export default function ScoreSection({ lead, breakdown }) {
  return (
    <>
      <div className="lead-score-display">
        <div>
          <div className="lead-score-label">Lead Score</div>
          <div
            className="lead-score-value"
            style={{ color: scoreColor(lead.lead_score) }}
          >
            {lead.lead_score ?? "N/A"} / 100
          </div>
        </div>
        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          {lead.lead_temperature && temperatureBadge(lead.lead_temperature)}
          <span
            className={`lead-tag ${scoreClass(lead.lead_score)}`}
            style={{ fontSize: 13 }}
          >
            {scoreLabel(lead.lead_score)}
          </span>
        </div>
      </div>
      <ScoreBreakdown breakdown={breakdown} />
      {!breakdown && <GenericScoreFactors lead={lead} />}
    </>
  );
}
