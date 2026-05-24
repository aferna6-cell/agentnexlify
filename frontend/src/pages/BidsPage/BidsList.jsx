import {
  STATUS_FILTERS,
  STATUS_COLORS,
  formatCurrency,
  formatDate,
  calcTotal,
} from "./utils";

export default function BidsList({
  bids,
  stats,
  activeFilter,
  setActiveFilter,
  error,
  setError,
  setLoading,
  loadData,
  openCreate,
  openEdit,
  setDetailBid,
  handleDelete,
  deletingIds,
  setShowTemplates,
  loadTemplates,
}) {
  const totalBids = stats?.total_bids ?? bids.length;
  const winRate = stats?.win_rate ?? 0;
  const avgValue = stats?.average_bid_value ?? 0;
  const pipelineValue = stats?.pipeline_value ?? 0;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Bids</h1>
          <p>Create, track, and manage contractor bids and proposals</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            className="btn-primary"
            onClick={() => {
              setShowTemplates(true);
              loadTemplates();
            }}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
            }}
          >
            Templates
          </button>
          <button
            className="btn-primary"
            onClick={() => {
              setLoading(true);
              loadData();
            }}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
            }}
          >
            Refresh
          </button>
          <button className="btn-primary" onClick={openCreate}>
            + New Bid
          </button>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 12,
          marginBottom: 24,
        }}
      >
        {[
          {
            label: "Total Bids",
            value: totalBids,
            color: "var(--text-secondary)",
          },
          {
            label: "Win Rate",
            value: `${Math.round(winRate)}%`,
            color: "#22c55e",
          },
          {
            label: "Avg Bid Value",
            value: formatCurrency(avgValue),
            color: "#3b82f6",
          },
          {
            label: "Pipeline Value",
            value: formatCurrency(pipelineValue),
            color: "#8b5cf6",
          },
        ].map((card) => (
          <div
            key={card.label}
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: "16px 20px",
            }}
          >
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                marginBottom: 4,
              }}
            >
              {card.label}
            </div>
            <div
              style={{ fontSize: "1.5rem", fontWeight: 700, color: card.color }}
            >
              {card.value}
            </div>
          </div>
        ))}
      </div>

      <div
        style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}
      >
        {STATUS_FILTERS.map((s) => {
          const isActive = activeFilter === s;
          const count =
            s === "all"
              ? bids.length
              : bids.filter((b) => b.status === s).length;
          return (
            <button
              key={s}
              onClick={() => setActiveFilter(s)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border: isActive
                  ? "1px solid var(--accent)"
                  : "1px solid var(--border)",
                background: isActive
                  ? "var(--accent-dim)"
                  : "var(--bg-secondary)",
                color: isActive ? "var(--accent)" : "var(--text-secondary)",
                cursor: "pointer",
                fontSize: "0.85rem",
                fontWeight: isActive ? 600 : 400,
                textTransform: "capitalize",
                transition: "all 0.15s ease",
              }}
            >
              {s}
              <span
                style={{ marginLeft: 6, fontSize: "0.75rem", opacity: 0.7 }}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {error && (
        <div
          style={{
            marginBottom: 16,
            padding: "10px 16px",
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 8,
            color: "#ef4444",
            fontSize: "0.85rem",
          }}
        >
          {error}
          <button
            onClick={() => setError(null)}
            style={{
              marginLeft: 12,
              background: "none",
              border: "none",
              color: "#ef4444",
              cursor: "pointer",
              fontSize: "0.8rem",
              textDecoration: "underline",
            }}
          >
            dismiss
          </button>
        </div>
      )}

      {bids.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            color: "var(--text-muted)",
          }}
        >
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>
            {activeFilter !== "all"
              ? "No bids match this filter"
              : "No bids yet"}
          </div>
          <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
            {activeFilter !== "all"
              ? "Try selecting a different status filter, or create a new bid."
              : "Create your first bid to start tracking proposals and win rates. You can generate bids with AI or build them from templates."}
          </p>
          {activeFilter !== "all" ? (
            <button
              className="btn-primary"
              onClick={() => setActiveFilter("all")}
              style={{
                background: "transparent",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
              }}
            >
              Clear Filter
            </button>
          ) : (
            <button className="btn-primary" onClick={openCreate}>
              Create Your First Bid
            </button>
          )}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {bids.map((bid) => {
            const statusColor =
              STATUS_COLORS[bid.status] || STATUS_COLORS.draft;
            const isDeleting = deletingIds.has(bid.id);
            const total = calcTotal(bid.line_items);

            return (
              <div
                key={bid.id}
                style={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  padding: 16,
                  borderLeft: `4px solid ${statusColor.color}`,
                  opacity: isDeleting ? 0.5 : 1,
                  cursor: "pointer",
                  transition: "opacity 0.2s ease",
                }}
                onClick={() => setDetailBid(bid)}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                    gap: 8,
                  }}
                >
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        marginBottom: 6,
                      }}
                    >
                      <span style={{ fontWeight: 600, fontSize: "1rem" }}>
                        {bid.title}
                      </span>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "2px 8px",
                          borderRadius: 4,
                          fontSize: "0.7rem",
                          fontWeight: 600,
                          color: statusColor.color,
                          background: statusColor.bg,
                          textTransform: "capitalize",
                        }}
                      >
                        {bid.status}
                      </span>
                    </div>
                    {bid.description && (
                      <div
                        style={{
                          fontSize: "0.85rem",
                          color: "var(--text-secondary)",
                          lineHeight: 1.4,
                          marginBottom: 4,
                        }}
                      >
                        {bid.description.length > 120
                          ? bid.description.slice(0, 120) + "..."
                          : bid.description}
                      </div>
                    )}
                    <div
                      style={{
                        display: "flex",
                        gap: 12,
                        fontSize: "0.8rem",
                        color: "var(--text-muted)",
                      }}
                    >
                      {bid.timeline && <span>Timeline: {bid.timeline}</span>}
                      <span>{formatDate(bid.created_at)}</span>
                    </div>
                  </div>
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 12 }}
                  >
                    <div style={{ textAlign: "right" }}>
                      <div
                        style={{
                          fontSize: "1.1rem",
                          fontWeight: 700,
                          color: "#3b82f6",
                        }}
                      >
                        {formatCurrency(total)}
                      </div>
                      <div
                        style={{
                          fontSize: "0.75rem",
                          color: "var(--text-muted)",
                        }}
                      >
                        {(bid.line_items || []).length} item
                        {(bid.line_items || []).length !== 1 ? "s" : ""}
                      </div>
                    </div>
                    <div
                      style={{ display: "flex", gap: 6 }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        onClick={() => openEdit(bid)}
                        disabled={isDeleting}
                        style={{
                          background: "none",
                          border: "1px solid var(--border)",
                          borderRadius: 6,
                          padding: "6px 10px",
                          color: "var(--text-secondary)",
                          cursor: "pointer",
                          fontSize: "0.8rem",
                        }}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(bid.id)}
                        disabled={isDeleting}
                        style={{
                          background: "none",
                          border: "1px solid var(--border)",
                          borderRadius: 6,
                          padding: "6px 10px",
                          color: "var(--red, #ef4444)",
                          cursor: "pointer",
                          fontSize: "0.8rem",
                        }}
                      >
                        {isDeleting ? "..." : "Delete"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
