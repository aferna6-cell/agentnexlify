import {
  STATUS_COLORS,
  STATUS_PROGRESSION,
  formatCurrency,
  calcTotal,
} from "./utils";

export default function BidDetailModal({
  detailBid,
  setDetailBid,
  openEdit,
  handleStatusChange,
  handleSaveAsTemplate,
  savingTemplate,
}) {
  if (!detailBid) return null;
  const statusColor = STATUS_COLORS[detailBid.status] || STATUS_COLORS.draft;
  const nextStatuses = STATUS_PROGRESSION[detailBid.status] || [];

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={() => setDetailBid(null)}
    >
      <div
        style={{
          background: "var(--bg-primary)",
          borderRadius: 12,
          padding: 24,
          width: "90%",
          maxWidth: 600,
          maxHeight: "80vh",
          overflowY: "auto",
          border: "1px solid var(--border)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: 16,
          }}
        >
          <div>
            <h3 style={{ marginBottom: 6 }}>{detailBid.title}</h3>
            <span
              style={{
                display: "inline-block",
                padding: "3px 10px",
                borderRadius: 4,
                fontSize: "0.75rem",
                fontWeight: 600,
                color: statusColor.color,
                background: statusColor.bg,
                textTransform: "capitalize",
              }}
            >
              {detailBid.status}
            </span>
          </div>
          <button
            onClick={() => setDetailBid(null)}
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: "1.2rem",
            }}
          >
            x
          </button>
        </div>

        {detailBid.description && (
          <div
            style={{
              fontSize: "0.9rem",
              color: "var(--text-secondary)",
              marginBottom: 16,
              lineHeight: 1.5,
            }}
          >
            {detailBid.description}
          </div>
        )}

        {detailBid.line_items && detailBid.line_items.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: 8,
              }}
            >
              Line Items
            </div>
            <div
              style={{
                border: "1px solid var(--border)",
                borderRadius: 8,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "2fr 1fr 1fr 1fr",
                  padding: "8px 12px",
                  background: "var(--bg-secondary)",
                  fontSize: "0.75rem",
                  color: "var(--text-muted)",
                  fontWeight: 600,
                }}
              >
                <span>Item</span>
                <span style={{ textAlign: "right" }}>Qty</span>
                <span style={{ textAlign: "right" }}>Unit Price</span>
                <span style={{ textAlign: "right" }}>Total</span>
              </div>
              {detailBid.line_items.map((li, idx) => (
                <div
                  key={idx}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "2fr 1fr 1fr 1fr",
                    padding: "8px 12px",
                    borderTop: "1px solid var(--border)",
                    fontSize: "0.85rem",
                  }}
                >
                  <span>{li.name}</span>
                  <span style={{ textAlign: "right" }}>{li.qty}</span>
                  <span style={{ textAlign: "right" }}>
                    {formatCurrency(li.unit_price)}
                  </span>
                  <span style={{ textAlign: "right", fontWeight: 600 }}>
                    {formatCurrency((li.qty || 0) * (li.unit_price || 0))}
                  </span>
                </div>
              ))}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "2fr 1fr 1fr 1fr",
                  padding: "10px 12px",
                  borderTop: "2px solid var(--border)",
                  fontSize: "0.9rem",
                  fontWeight: 700,
                }}
              >
                <span>Total</span>
                <span />
                <span />
                <span style={{ textAlign: "right", color: "#3b82f6" }}>
                  {formatCurrency(calcTotal(detailBid.line_items))}
                </span>
              </div>
            </div>
          </div>
        )}

        {detailBid.terms && (
          <div style={{ marginBottom: 12 }}>
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                textTransform: "uppercase",
                marginBottom: 4,
              }}
            >
              Terms
            </div>
            <div
              style={{
                fontSize: "0.85rem",
                color: "var(--text-secondary)",
                lineHeight: 1.5,
              }}
            >
              {detailBid.terms}
            </div>
          </div>
        )}

        {detailBid.timeline && (
          <div style={{ marginBottom: 16 }}>
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                textTransform: "uppercase",
                marginBottom: 4,
              }}
            >
              Timeline
            </div>
            <div
              style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}
            >
              {detailBid.timeline}
            </div>
          </div>
        )}

        {nextStatuses.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                textTransform: "uppercase",
                marginBottom: 8,
              }}
            >
              Update Status
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {nextStatuses.map((nextStatus) => {
                const sc = STATUS_COLORS[nextStatus] || STATUS_COLORS.draft;
                return (
                  <button
                    key={nextStatus}
                    onClick={() => handleStatusChange(detailBid.id, nextStatus)}
                    style={{
                      padding: "6px 14px",
                      borderRadius: 6,
                      border: `1px solid ${sc.color}`,
                      background: sc.bg,
                      color: sc.color,
                      cursor: "pointer",
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      textTransform: "capitalize",
                    }}
                  >
                    Mark as {nextStatus}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div
          style={{
            display: "flex",
            gap: 8,
            justifyContent: "flex-end",
            borderTop: "1px solid var(--border)",
            paddingTop: 16,
          }}
        >
          <button
            onClick={() => handleSaveAsTemplate(detailBid)}
            disabled={savingTemplate}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "8px 16px",
              color: "var(--text-primary)",
              cursor: "pointer",
              fontSize: "0.8rem",
            }}
          >
            {savingTemplate ? "Saving..." : "Save as Template"}
          </button>
          <button
            onClick={() => openEdit(detailBid)}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "8px 16px",
              color: "var(--text-primary)",
              cursor: "pointer",
              fontSize: "0.8rem",
            }}
          >
            Edit
          </button>
          <button onClick={() => setDetailBid(null)} className="btn-primary">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
