import { useMemo, useState } from "react";

const STAGES = [
  { key: "new", label: "New" },
  { key: "contacted", label: "Contacted" },
  { key: "appointment_booked", label: "Appointment" },
  { key: "closed", label: "Closed" },
  { key: "lost", label: "Lost" },
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

function scoreClass(score) {
  if (score >= 80) return "score-hot";
  if (score >= 60) return "score-warm";
  if (score >= 40) return "score-cool";
  return "score-cold";
}

function scoreLabel(score) {
  if (score >= 80) return "Hot";
  if (score >= 60) return "Warm";
  if (score >= 40) return "Cool";
  return "Cold";
}

function LeadCard({ lead, onClick, onDragStart, onDragEnd }) {
  return (
    <div
      className="lead-card"
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", lead.id);
        e.currentTarget.classList.add("dragging");
        onDragStart?.(lead.id);
      }}
      onDragEnd={(e) => {
        e.currentTarget.classList.remove("dragging");
        onDragEnd?.();
      }}
      onClick={() => onClick(lead)}
    >
      <div className="lead-name">{lead.name || "Unknown"}</div>
      <div className="lead-desc">
        {lead.areas_of_interest || lead.email || "No details"}
      </div>
      <div className="lead-meta">
        <span className={`lead-tag ${scoreClass(lead.lead_score)}`}>
          {scoreLabel(lead.lead_score)}
        </span>
        <span className="lead-time">{formatTimeAgo(lead.created_at)}</span>
      </div>
    </div>
  );
}

function PipelineColumn({ stage, leads, onSelectLead, onStageDrop, onDragStart, onDragEnd }) {
  const [dragOver, setDragOver] = useState(false);

  return (
    <div
      className={`pipeline-column${dragOver ? " drag-over" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        const leadId = e.dataTransfer.getData("text/plain");
        if (leadId) onStageDrop?.(leadId, stage.key);
      }}
    >
      <div className="pipeline-col-header">
        <span className="pipeline-col-title">{stage.label}</span>
        <span className="pipeline-col-count">{leads.length}</span>
      </div>
      <div className="pipeline-cards">
        {leads.map((lead) => (
          <LeadCard
            key={lead.id}
            lead={lead}
            onClick={onSelectLead}
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
          />
        ))}
        {leads.length === 0 && (
          <div className="pipeline-empty">No leads</div>
        )}
      </div>
    </div>
  );
}

export { STAGES };

export default function LeadPipeline({ leads, onSelectLead, onNavigate, onStageDrop }) {
  const [sortByScore, setSortByScore] = useState(false);

  const grouped = useMemo(() => {
    const map = {};
    for (const s of STAGES) map[s.key] = [];
    for (const lead of leads) {
      const stage = lead.status || "new";
      if (map[stage]) map[stage].push(lead);
      else map["new"].push(lead);
    }
    if (sortByScore) {
      for (const key of Object.keys(map)) {
        map[key].sort((a, b) => (b.lead_score || 0) - (a.lead_score || 0));
      }
    }
    return map;
  }, [leads, sortByScore]);

  if (!leads || leads.length === 0) {
    return (
      <div className="pipeline">
        <div className="pipeline-header">Lead Pipeline</div>
        <div className="empty-state">
          <div className="empty-state-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <p className="empty-state-text">
            Leads captured from widget conversations will appear here
          </p>
          <button
            className="empty-state-cta"
            onClick={() => onNavigate?.("widget")}
          >
            Set up your widget &rarr;
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="pipeline">
      <div className="pipeline-header">
        Lead Pipeline
        <button
          className={`pipeline-sort-btn${sortByScore ? " active" : ""}`}
          onClick={() => setSortByScore((s) => !s)}
        >
          Sort by Score
        </button>
      </div>
      <div className="pipeline-columns">
        {STAGES.map((stage) => (
          <PipelineColumn
            key={stage.key}
            stage={stage}
            leads={grouped[stage.key]}
            onSelectLead={onSelectLead}
            onStageDrop={onStageDrop}
          />
        ))}
      </div>
    </div>
  );
}
