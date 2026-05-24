import { formatDate, scoreClass, scoreLabel } from "./utils";

export default function LeadTable({
  leads,
  sortField,
  sortOrder,
  onSort,
  onSelectLead,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
}) {
  const columns = [
    { key: "name", label: "Name" },
    { key: "email", label: "Email" },
    { key: "phone", label: "Phone" },
    { key: "status", label: "Stage" },
    { key: "lead_score", label: "Score" },
    { key: "tags", label: "Tags", sortable: false },
    { key: "created_at", label: "Created" },
  ];

  const allSelected =
    leads.length > 0 && leads.every((l) => selectedIds.has(l.id));
  const someSelected = leads.some((l) => selectedIds.has(l.id));

  return (
    <div className="leads-table-wrapper">
      <table className="leads-table">
        <thead>
          <tr>
            <th style={{ width: 36, cursor: "default", padding: "8px 4px" }}>
              <input
                type="checkbox"
                checked={allSelected}
                ref={(el) => {
                  if (el) el.indeterminate = someSelected && !allSelected;
                }}
                onChange={() => onToggleSelectAll(leads)}
                style={{
                  cursor: "pointer",
                  accentColor: "var(--accent, #00BFFF)",
                }}
              />
            </th>
            {columns.map((col) => (
              <th
                key={col.key}
                onClick={
                  col.sortable !== false ? () => onSort(col.key) : undefined
                }
                className={sortField === col.key ? "sorted" : ""}
                style={
                  col.sortable === false ? { cursor: "default" } : undefined
                }
              >
                {col.label}
                {sortField === col.key && (
                  <span className="sort-arrow">
                    {sortOrder === "asc" ? " ↑" : " ↓"}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => (
            <tr
              key={lead.id}
              onClick={() => onSelectLead(lead)}
              className={selectedIds.has(lead.id) ? "selected-row" : ""}
            >
              <td
                style={{ padding: "8px 4px" }}
                onClick={(e) => e.stopPropagation()}
              >
                <input
                  type="checkbox"
                  checked={selectedIds.has(lead.id)}
                  onChange={() => onToggleSelect(lead.id)}
                  style={{
                    cursor: "pointer",
                    accentColor: "var(--accent, #00BFFF)",
                  }}
                />
              </td>
              <td>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  {lead.name || "Unknown"}
                  {lead.enrichment_source === "ai" && (
                    <span
                      title="Fields filled by AI enrichment"
                      style={{
                        fontSize: "0.65rem",
                        padding: "1px 5px",
                        borderRadius: 8,
                        background: "rgba(0,191,255,0.15)",
                        color: "#00BFFF",
                        fontWeight: 700,
                        letterSpacing: "0.02em",
                        flexShrink: 0,
                      }}
                    >
                      AI
                    </span>
                  )}
                </div>
                {lead.conversation_summary && (
                  <div
                    style={{
                      fontSize: "0.72rem",
                      color: "var(--text-muted)",
                      maxWidth: 220,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      marginTop: 2,
                    }}
                  >
                    {lead.conversation_summary}
                  </div>
                )}
              </td>
              <td>{lead.email || "—"}</td>
              <td>{lead.phone || "—"}</td>
              <td>
                <span className={`stage-badge stage-${lead.status || "new"}`}>
                  {lead.status || "new"}
                </span>
              </td>
              <td>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span className={`lead-tag ${scoreClass(lead.lead_score)}`}>
                    {lead.lead_score ?? "N/A"} &middot;{" "}
                    {scoreLabel(lead.lead_score)}
                  </span>
                  {lead.qualification_recommendation && (
                    <span
                      title={`AI: ${lead.qualification_recommendation.replace(/_/g, " ")}`}
                      style={{
                        fontSize: "0.7rem",
                        lineHeight: 1,
                        padding: "3px 6px",
                        borderRadius: 10,
                        background:
                          lead.qualification_recommendation === "hot_call_now"
                            ? "rgba(255,68,68,0.2)"
                            : lead.qualification_recommendation ===
                                "warm_nurture_sequence"
                              ? "rgba(245,166,35,0.2)"
                              : "rgba(136,136,136,0.2)",
                        color:
                          lead.qualification_recommendation === "hot_call_now"
                            ? "#ff4444"
                            : lead.qualification_recommendation ===
                                "warm_nurture_sequence"
                              ? "#f5a623"
                              : "#888",
                        fontWeight: 700,
                      }}
                    >
                      AI
                    </span>
                  )}
                </div>
              </td>
              <td>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {(lead.tags || []).slice(0, 3).map((tag, ti) => (
                    <span
                      key={ti}
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: 12,
                        fontSize: "0.7rem",
                        background: "var(--accent-dim, rgba(0,191,255,0.15))",
                        color: "var(--accent, #00BFFF)",
                        whiteSpace: "nowrap",
                        maxWidth: 140,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                  {(lead.tags || []).length > 3 && (
                    <span
                      style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}
                    >
                      +{lead.tags.length - 3}
                    </span>
                  )}
                </div>
              </td>
              <td>{formatDate(lead.created_at)}</td>
            </tr>
          ))}
          {leads.length === 0 && (
            <tr>
              <td colSpan={8}>
                <div
                  style={{
                    background: "var(--bg-secondary)",
                    borderRadius: 12,
                    padding: 48,
                    textAlign: "center",
                    margin: "8px 0",
                  }}
                >
                  <svg
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="var(--text-muted)"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ marginBottom: 12 }}
                  >
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                  <div
                    style={{
                      fontWeight: 600,
                      fontSize: "1rem",
                      color: "var(--text-primary)",
                      marginBottom: 8,
                    }}
                  >
                    No leads yet
                  </div>
                  <div
                    style={{
                      fontSize: "0.875rem",
                      color: "var(--text-muted)",
                      maxWidth: 360,
                      margin: "0 auto",
                    }}
                  >
                    Leads captured from your chat widget will appear here. Set
                    up your widget to start capturing visitors.
                  </div>
                </div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
