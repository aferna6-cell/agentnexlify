import StatusBadge from "./StatusBadge";
import { timeAgo } from "./helpers";

export default function JobHistory({ jobs, selectedJob, onSelect, onDelete }) {
  return (
    <div
      style={{
        background: "var(--card-bg)",
        borderRadius: 12,
        border: "1px solid var(--border)",
        padding: 16,
        flex: 1,
        overflow: "auto",
      }}
    >
      <div
        style={{
          fontSize: "0.9rem",
          fontWeight: 600,
          marginBottom: 12,
          color: "var(--text-secondary)",
        }}
      >
        History
      </div>
      {jobs.length === 0 ? (
        <div
          style={{
            color: "var(--text-muted)",
            fontSize: "0.85rem",
            textAlign: "center",
            padding: 20,
          }}
        >
          No repurpose jobs yet. Create your first one above!
        </div>
      ) : (
        jobs.map((job) => (
          <div
            key={job.id}
            onClick={() => onSelect(job.id)}
            style={{
              padding: "10px 12px",
              borderRadius: 8,
              cursor: "pointer",
              marginBottom: 4,
              background:
                selectedJob?.id === job.id
                  ? "var(--hover-overlay)"
                  : "transparent",
              border:
                selectedJob?.id === job.id
                  ? "1px solid var(--accent)"
                  : "1px solid transparent",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span
                style={{
                  fontSize: "0.85rem",
                  fontWeight: 500,
                  color: "var(--text-primary)",
                }}
              >
                {job.source_title || `${job.source_type} content`}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(job.id);
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  fontSize: "0.8rem",
                }}
              >
                ×
              </button>
            </div>
            <div
              style={{
                display: "flex",
                gap: 8,
                marginTop: 4,
                alignItems: "center",
              }}
            >
              <StatusBadge status={job.status} />
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                {timeAgo(job.created_at)}
              </span>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
