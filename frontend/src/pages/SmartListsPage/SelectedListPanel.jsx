import LeadsTable from "./LeadsTable";

function parseFilters(filterJson) {
  if (!filterJson) return {};
  if (typeof filterJson === "string") {
    try {
      return JSON.parse(filterJson);
    } catch {
      return {};
    }
  }
  return filterJson;
}

function buildBadges(f) {
  const badges = [];
  if ((f.status || []).length > 0)
    badges.push(`Status: ${f.status.join(", ")}`);
  if (f.lead_temperature) badges.push(`Temp: ${f.lead_temperature}`);
  if (f.min_score) badges.push(`Score >= ${f.min_score}`);
  if (f.max_score) badges.push(`Score <= ${f.max_score}`);
  if ((f.tags_include || []).length > 0)
    badges.push(`Tags: ${f.tags_include.join(", ")}`);
  if (f.assigned_to) badges.push(`Assigned: ${f.assigned_to}`);
  if (f.created_after) badges.push(`After: ${f.created_after}`);
  if (f.created_before) badges.push(`Before: ${f.created_before}`);
  if (f.has_email) badges.push("Has email");
  if (f.has_phone) badges.push("Has phone");
  if (f.search) badges.push(`Search: "${f.search}"`);
  if (badges.length === 0) badges.push("No filters (all leads)");
  return badges;
}

export default function SelectedListPanel({
  selectedList,
  selectedLeads,
  leadsLoading,
  exporting,
  onExport,
  onUseCampaign,
}) {
  const filterBadges = selectedList?.filter_json
    ? buildBadges(parseFilters(selectedList.filter_json))
    : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
      <div
        style={{
          padding: "16px 20px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div style={{ flex: 1, minWidth: 200 }}>
          <h2 style={{ fontSize: "1.2rem", marginBottom: 4 }}>
            {selectedList.name}
          </h2>
          {selectedList.description && (
            <p
              style={{
                fontSize: "0.85rem",
                color: "var(--text-muted)",
                marginBottom: 6,
              }}
            >
              {selectedList.description}
            </p>
          )}
          <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
            <span style={{ fontWeight: 700, color: "var(--accent)" }}>
              {leadsLoading ? "..." : selectedLeads.length}
            </span>{" "}
            matching lead{selectedLeads.length !== 1 ? "s" : ""}
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
          <button
            onClick={onExport}
            disabled={exporting || selectedLeads.length === 0}
            style={{
              background: "rgba(59,130,246,0.1)",
              border: "1px solid rgba(59,130,246,0.3)",
              borderRadius: 8,
              padding: "8px 14px",
              color: "#3b82f6",
              cursor: selectedLeads.length === 0 ? "not-allowed" : "pointer",
              fontSize: "0.8rem",
              fontWeight: 600,
              opacity: selectedLeads.length === 0 ? 0.5 : 1,
            }}
          >
            {exporting ? "Exporting..." : "Export CSV"}
          </button>
          <button
            onClick={onUseCampaign}
            disabled={selectedLeads.length === 0}
            style={{
              background: "rgba(139,92,246,0.1)",
              border: "1px solid rgba(139,92,246,0.3)",
              borderRadius: 8,
              padding: "8px 14px",
              color: "#8b5cf6",
              cursor: selectedLeads.length === 0 ? "not-allowed" : "pointer",
              fontSize: "0.8rem",
              fontWeight: 600,
              opacity: selectedLeads.length === 0 ? 0.5 : 1,
            }}
          >
            Use in Campaign
          </button>
        </div>
      </div>

      {filterBadges && (
        <div
          style={{
            padding: "10px 20px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            gap: 6,
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          <span
            style={{
              fontSize: "0.72rem",
              color: "var(--text-muted)",
              fontWeight: 600,
              textTransform: "uppercase",
              marginRight: 4,
            }}
          >
            Filters:
          </span>
          {filterBadges.map((b, i) => (
            <span
              key={i}
              style={{
                padding: "3px 8px",
                borderRadius: 6,
                fontSize: "0.72rem",
                background: "var(--hover-overlay)",
                color: "var(--text-secondary)",
                border: "1px solid var(--border)",
              }}
            >
              {b}
            </span>
          ))}
        </div>
      )}

      <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
        <LeadsTable leads={selectedLeads} loading={leadsLoading} />
      </div>
    </div>
  );
}
