import { useMemo } from "react";

const STAGES = [
  { key: "new", label: "New" },
  { key: "contacted", label: "Contacted" },
  { key: "qualified", label: "Qualified" },
  { key: "appointment", label: "Appointment" },
  { key: "closed", label: "Closed" },
];

function formatTimeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "Yesterday";
  return `${days}d ago`;
}

function scoreClass(temp) {
  if (temp === "hot") return "score-hot";
  if (temp === "warm") return "score-warm";
  return "score-cold";
}

function scoreLabel(temp) {
  if (temp === "hot") return "Hot";
  if (temp === "warm") return "Warm";
  return "Cold";
}

function LeadCard({ lead, onClick }) {
  return (
    <div className="lead-card" onClick={() => onClick(lead)}>
      <div className="lead-name">{lead.name || "Unknown"}</div>
      <div className="lead-desc">
        {lead.lead_type || lead.areas_of_interest || "No details"}
      </div>
      <div className="lead-meta">
        <span className={`lead-tag ${scoreClass(lead.lead_temperature)}`}>
          {scoreLabel(lead.lead_temperature)}
        </span>
        <span className="lead-time">{formatTimeAgo(lead.created_at)}</span>
      </div>
    </div>
  );
}

export default function LeadPipeline({ leads, onSelectLead }) {
  const grouped = useMemo(() => {
    const map = {};
    for (const s of STAGES) map[s.key] = [];
    for (const lead of leads) {
      const stage = lead.lead_stage || lead.status || "new";
      if (map[stage]) map[stage].push(lead);
      else map["new"].push(lead);
    }
    return map;
  }, [leads]);

  return (
    <div className="pipeline">
      <div className="pipeline-header">Lead Pipeline</div>
      <div className="pipeline-columns">
        {STAGES.map((stage) => (
          <div className="pipeline-column" key={stage.key}>
            <div className="pipeline-col-header">
              <span className="pipeline-col-title">{stage.label}</span>
              <span className="pipeline-col-count">{grouped[stage.key].length}</span>
            </div>
            <div className="pipeline-cards">
              {grouped[stage.key].map((lead) => (
                <LeadCard key={lead.id} lead={lead} onClick={onSelectLead} />
              ))}
              {grouped[stage.key].length === 0 && (
                <div className="pipeline-empty">No leads</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
