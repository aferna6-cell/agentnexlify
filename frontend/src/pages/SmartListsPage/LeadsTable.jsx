import StatusBadge from "./StatusBadge";
import TemperatureBadge from "./TemperatureBadge";

export default function LeadsTable({ leads, loading }) {
  if (loading) {
    return (
      <div
        style={{
          padding: 40,
          textAlign: "center",
          color: "var(--text-muted)",
          fontSize: "0.9rem",
        }}
      >
        Loading leads...
      </div>
    );
  }

  if (!leads || leads.length === 0) {
    return (
      <div
        style={{
          padding: "40px 20px",
          textAlign: "center",
          color: "var(--text-muted)",
        }}
      >
        <div style={{ fontSize: "1.2rem", marginBottom: 8 }}>
          No matching leads
        </div>
        <p
          style={{
            fontSize: "0.85rem",
            lineHeight: 1.6,
            maxWidth: 400,
            margin: "0 auto",
          }}
        >
          This smart list's filters did not match any current leads. As new
          leads come in or existing leads update, matching ones will appear here
          automatically.
        </p>
      </div>
    );
  }

  return (
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
          gridTemplateColumns: "1.5fr 1.5fr 1fr 0.8fr 0.7fr 0.6fr",
          padding: "10px 16px",
          borderBottom: "1px solid var(--border)",
          fontSize: "0.75rem",
          color: "var(--text-muted)",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        <span>Name</span>
        <span>Email</span>
        <span>Phone</span>
        <span style={{ textAlign: "center" }}>Status</span>
        <span style={{ textAlign: "center" }}>Temp</span>
        <span style={{ textAlign: "center" }}>Score</span>
      </div>

      {leads.map((lead) => (
        <div
          key={lead.id}
          style={{
            display: "grid",
            gridTemplateColumns: "1.5fr 1.5fr 1fr 0.8fr 0.7fr 0.6fr",
            padding: "10px 16px",
            borderBottom: "1px solid var(--border)",
            alignItems: "center",
            fontSize: "0.85rem",
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
            style={{
              fontWeight: 600,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {lead.name || "Unnamed"}
          </span>
          <span
            style={{
              color: "var(--text-secondary)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={lead.email}
          >
            {lead.email || "--"}
          </span>
          <span style={{ color: "var(--text-secondary)" }}>
            {lead.phone || "--"}
          </span>
          <span style={{ textAlign: "center" }}>
            <StatusBadge status={lead.status} />
          </span>
          <span style={{ textAlign: "center" }}>
            <TemperatureBadge temp={lead.lead_temperature} />
          </span>
          <span
            style={{
              textAlign: "center",
              fontWeight: 600,
              color:
                lead.lead_score >= 70
                  ? "#22c55e"
                  : lead.lead_score >= 40
                    ? "#f59e0b"
                    : "var(--text-muted)",
            }}
          >
            {lead.lead_score != null ? lead.lead_score : "--"}
          </span>
        </div>
      ))}
    </div>
  );
}
