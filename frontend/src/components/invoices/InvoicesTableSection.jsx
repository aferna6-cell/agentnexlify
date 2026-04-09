import StatusBadge from "./StatusBadge";
import { calcTotal, formatCurrency, formatDate } from "./invoiceUtils";

export default function InvoicesTableSection({
  activeFilter,
  filteredInvoices,
  selectedIds,
  deletingIds,
  markingPaid,
  copiedId,
  bulkSending,
  onSelectedIdsChange,
  onClearFilter,
  onOpenCreate,
  onOpenDetail,
  onOpenSend,
  onMarkPaid,
  onCopyPaymentLink,
  onDelete,
  onBulkSend,
}) {
  if (filteredInvoices.length === 0) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "60px 20px",
          color: "var(--text-muted)",
        }}
      >
        <div style={{ fontSize: "2rem", marginBottom: 12 }}>
          {activeFilter !== "all"
            ? "No invoices match this filter"
            : "No invoices yet"}
        </div>
        <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
          {activeFilter !== "all"
            ? "Try selecting a different status filter, or create a new invoice."
            : "Create your first invoice to start tracking payments. You can create invoices manually or convert a bid into an invoice."}
        </p>
        {activeFilter !== "all" ? (
          <button
            className="btn-primary"
            onClick={onClearFilter}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
            }}
          >
            Clear Filter
          </button>
        ) : (
          <button className="btn-primary" onClick={onOpenCreate}>
            Create Your First Invoice
          </button>
        )}
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
          gridTemplateColumns:
            "28px 100px 1fr 120px 100px 110px 110px 160px",
          padding: "10px 16px",
          borderBottom: "1px solid var(--border)",
          fontSize: "0.75rem",
          color: "var(--text-muted)",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        <span style={{ width: 28 }}>
          <input
            type="checkbox"
            checked={
              selectedIds.size > 0 &&
              filteredInvoices.every((invoice) => selectedIds.has(invoice.id))
            }
            onChange={(event) => {
              if (event.target.checked) {
                onSelectedIdsChange(new Set(filteredInvoices.map((invoice) => invoice.id)));
              } else {
                onSelectedIdsChange(new Set());
              }
            }}
          />
        </span>
        <span>Invoice #</span>
        <span>Customer</span>
        <span style={{ textAlign: "right" }}>Amount</span>
        <span style={{ textAlign: "center" }}>Status</span>
        <span style={{ textAlign: "center" }}>Due Date</span>
        <span style={{ textAlign: "center" }}>Sent</span>
        <span style={{ textAlign: "right" }}>Actions</span>
      </div>

      {selectedIds.size > 0 && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "10px 16px",
            background: "rgba(0,191,255,0.08)",
            borderBottom: "1px solid rgba(0,191,255,0.25)",
          }}
        >
          <span
            style={{
              fontWeight: 600,
              fontSize: 13,
              color: "var(--accent, #00BFFF)",
            }}
          >
            {selectedIds.size} selected
          </span>
          <button
            disabled={bulkSending}
            onClick={onBulkSend}
            style={{
              padding: "4px 12px",
              fontSize: 12,
              fontWeight: 600,
              background: "var(--accent, #00BFFF)",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              cursor: "pointer",
            }}
          >
            {bulkSending ? "Sending..." : "Send All via Email"}
          </button>
          <button
            onClick={() => onSelectedIdsChange(new Set())}
            style={{
              padding: "4px 10px",
              fontSize: 12,
              background: "none",
              color: "var(--text-muted)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              cursor: "pointer",
            }}
          >
            Clear
          </button>
        </div>
      )}

      {filteredInvoices.map((invoice) => {
        const isDeleting = deletingIds.has(invoice.id);
        const total = calcTotal(
          invoice.items_json || invoice.items || [],
          invoice.tax_rate || 0,
        );
        const canSend = invoice.status === "draft" || invoice.status === "sent";
        const canPay =
          invoice.status === "sent" ||
          invoice.status === "viewed" ||
          invoice.status === "overdue";

        return (
          <div
            key={invoice.id}
            onClick={() => onOpenDetail(invoice)}
            style={{
              display: "grid",
              gridTemplateColumns:
                "28px 100px 1fr 120px 100px 110px 110px 160px",
              padding: "12px 16px",
              borderBottom: "1px solid var(--border)",
              alignItems: "center",
              cursor: "pointer",
              opacity: isDeleting ? 0.5 : 1,
              transition: "background 0.1s ease",
            }}
            onMouseEnter={(event) => {
              event.currentTarget.style.background = "var(--hover-overlay)";
            }}
            onMouseLeave={(event) => {
              event.currentTarget.style.background = "transparent";
            }}
          >
            <span onClick={(event) => event.stopPropagation()}>
              <input
                type="checkbox"
                checked={selectedIds.has(invoice.id)}
                onChange={(event) => {
                  const next = new Set(selectedIds);
                  if (event.target.checked) next.add(invoice.id);
                  else next.delete(invoice.id);
                  onSelectedIdsChange(next);
                }}
              />
            </span>
            <span
              style={{
                fontSize: "0.85rem",
                fontWeight: 600,
                color: "var(--accent)",
              }}
            >
              #{invoice.invoice_number || invoice.id?.slice(0, 8)}
            </span>
            <span style={{ fontSize: "0.85rem" }}>
              {invoice.customer_name || invoice.lead_name || "-"}
            </span>
            <span
              style={{
                textAlign: "right",
                fontSize: "0.9rem",
                fontWeight: 700,
                color: "#3b82f6",
              }}
            >
              {formatCurrency(invoice.total ?? total)}
            </span>
            <span style={{ textAlign: "center" }}>
              <StatusBadge status={invoice.status} />
            </span>
            <span
              style={{
                textAlign: "center",
                fontSize: "0.8rem",
                color:
                  invoice.status === "overdue"
                    ? "#ef4444"
                    : "var(--text-secondary)",
              }}
            >
              {formatDate(invoice.due_date) || "-"}
            </span>
            <span
              style={{
                textAlign: "center",
                fontSize: "0.8rem",
                color: "var(--text-muted)",
              }}
            >
              {formatDate(invoice.sent_at) || "-"}
            </span>
            <div
              style={{
                display: "flex",
                gap: 4,
                justifyContent: "flex-end",
              }}
              onClick={(event) => event.stopPropagation()}
            >
              {canSend && (
                <button
                  onClick={(event) => onOpenSend(invoice, event)}
                  style={{
                    background: "rgba(59,130,246,0.1)",
                    border: "1px solid rgba(59,130,246,0.3)",
                    borderRadius: 6,
                    padding: "4px 10px",
                    color: "#3b82f6",
                    cursor: "pointer",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                  }}
                >
                  Send
                </button>
              )}
              {canPay && (
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    onMarkPaid(invoice.id);
                  }}
                  disabled={markingPaid}
                  style={{
                    background: "rgba(34,197,94,0.1)",
                    border: "1px solid rgba(34,197,94,0.3)",
                    borderRadius: 6,
                    padding: "4px 10px",
                    color: "#22c55e",
                    cursor: "pointer",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                  }}
                >
                  {markingPaid ? "..." : "Paid"}
                </button>
              )}
              <button
                onClick={(event) => onCopyPaymentLink(invoice, event)}
                style={{
                  background: "none",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  padding: "4px 8px",
                  color:
                    copiedId === invoice.id
                      ? "#22c55e"
                      : "var(--text-secondary)",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                }}
                title="Copy payment link"
              >
                {copiedId === invoice.id ? "Copied!" : "Link"}
              </button>
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  onDelete(invoice.id);
                }}
                disabled={isDeleting}
                style={{
                  background: "none",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  padding: "4px 8px",
                  color: "#ef4444",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                }}
              >
                {isDeleting ? "..." : "Del"}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
