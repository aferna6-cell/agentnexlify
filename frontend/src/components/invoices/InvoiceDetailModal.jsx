import StatusBadge from "./StatusBadge";
import {
  calcSubtotal,
  calcTotal,
  formatCurrency,
  formatDate,
} from "./invoiceUtils";

export default function InvoiceDetailModal({
  detailInvoice,
  copiedId,
  paymentAmount,
  recordingPayment,
  markingPaid,
  onClose,
  onCopyPaymentLink,
  onPaymentAmountChange,
  onRecordPayment,
  onOpenSend,
  onMarkPaid,
}) {
  if (!detailInvoice) return null;

  const items = detailInvoice.items_json || detailInvoice.items || [];
  const subtotal = calcSubtotal(items);
  const taxRate = detailInvoice.tax_rate || 0;
  const taxAmount = subtotal * (taxRate / 100);
  const total = detailInvoice.total ?? calcTotal(items, taxRate);
  const paymentLink =
    detailInvoice.stripe_payment_link ||
    `${window.location.origin}/pay/${detailInvoice.id}`;

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
      onClick={onClose}
    >
      <div
        style={{
          background: "var(--bg-primary)",
          borderRadius: 12,
          padding: 24,
          width: "90%",
          maxWidth: 620,
          maxHeight: "85vh",
          overflowY: "auto",
          border: "1px solid var(--border)",
        }}
        onClick={(event) => event.stopPropagation()}
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
            <h3 style={{ marginBottom: 6 }}>
              Invoice #{detailInvoice.invoice_number || detailInvoice.id?.slice(0, 8)}
            </h3>
            <StatusBadge status={detailInvoice.status} />
          </div>
          <button
            onClick={onClose}
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

        {(detailInvoice.customer_name || detailInvoice.lead_name) && (
          <div
            style={{
              marginBottom: 12,
              fontSize: "0.9rem",
              color: "var(--text-secondary)",
            }}
          >
            <strong>Customer:</strong>{" "}
            {detailInvoice.customer_name || detailInvoice.lead_name}
          </div>
        )}

        <div
          style={{
            display: "flex",
            gap: 20,
            marginBottom: 16,
            fontSize: "0.85rem",
            color: "var(--text-secondary)",
          }}
        >
          {detailInvoice.due_date && (
            <div>
              <strong>Due:</strong> {formatDate(detailInvoice.due_date)}
            </div>
          )}
          {detailInvoice.sent_at && (
            <div>
              <strong>Sent:</strong> {formatDate(detailInvoice.sent_at)}
            </div>
          )}
          {detailInvoice.paid_at && (
            <div>
              <strong>Paid:</strong> {formatDate(detailInvoice.paid_at)}
            </div>
          )}
        </div>

        {items.length > 0 && (
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
              Items
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
                <span>Description</span>
                <span style={{ textAlign: "right" }}>Qty</span>
                <span style={{ textAlign: "right" }}>Unit Price</span>
                <span style={{ textAlign: "right" }}>Total</span>
              </div>
              {items.map((item, idx) => (
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
                  <span>{item.description}</span>
                  <span style={{ textAlign: "right" }}>{item.quantity}</span>
                  <span style={{ textAlign: "right" }}>
                    {formatCurrency(item.unit_price)}
                  </span>
                  <span style={{ textAlign: "right", fontWeight: 600 }}>
                    {formatCurrency((item.quantity || 0) * (item.unit_price || 0))}
                  </span>
                </div>
              ))}
            </div>

            <div style={{ padding: "8px 12px", fontSize: "0.85rem" }}>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "flex-end",
                  gap: 4,
                }}
              >
                <div style={{ color: "var(--text-secondary)" }}>
                  Subtotal: {formatCurrency(subtotal)}
                </div>
                {taxRate > 0 && (
                  <div style={{ color: "var(--text-secondary)" }}>
                    Tax ({taxRate}%): {formatCurrency(taxAmount)}
                  </div>
                )}
                <div
                  style={{
                    fontWeight: 700,
                    fontSize: "1rem",
                    color: "#3b82f6",
                  }}
                >
                  Total: {formatCurrency(total)}
                </div>
              </div>
            </div>
          </div>
        )}

        {detailInvoice.notes && (
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
              Notes
            </div>
            <div
              style={{
                fontSize: "0.85rem",
                color: "var(--text-secondary)",
                lineHeight: 1.5,
              }}
            >
              {detailInvoice.notes}
            </div>
          </div>
        )}

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
            Payment Link
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              readOnly
              value={paymentLink}
              style={{
                flex: 1,
                fontSize: "0.8rem",
                background: "var(--bg-secondary)",
                color: "var(--text-secondary)",
              }}
            />
            <button
              onClick={() => onCopyPaymentLink(detailInvoice)}
              style={{
                background:
                  copiedId === detailInvoice.id
                    ? "rgba(34,197,94,0.1)"
                    : "var(--bg-secondary)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                padding: "6px 12px",
                color:
                  copiedId === detailInvoice.id
                    ? "#22c55e"
                    : "var(--text-secondary)",
                cursor: "pointer",
                fontSize: "0.8rem",
                whiteSpace: "nowrap",
              }}
            >
              {copiedId === detailInvoice.id ? "Copied!" : "Copy Link"}
            </button>
          </div>
        </div>

        {(Number(detailInvoice.deposit_amount) > 0 ||
          Number(detailInvoice.amount_paid) > 0) && (
          <div style={{ marginBottom: 16 }}>
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                textTransform: "uppercase",
                marginBottom: 6,
              }}
            >
              Payment Progress
            </div>
            {Number(detailInvoice.deposit_amount) > 0 && (
              <div
                style={{
                  fontSize: "0.82rem",
                  color: "var(--text-secondary)",
                  marginBottom: 4,
                }}
              >
                Deposit required: {formatCurrency(detailInvoice.deposit_amount)}
              </div>
            )}
            <div
              style={{
                fontSize: "0.82rem",
                color: "var(--text-secondary)",
                marginBottom: 6,
              }}
            >
              Paid: {formatCurrency(detailInvoice.amount_paid || 0)} /{" "}
              {formatCurrency(total)}
            </div>
            <div
              style={{
                height: 6,
                background: "var(--bg-secondary)",
                borderRadius: 3,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${Math.min(
                    100,
                    ((Number(detailInvoice.amount_paid) || 0) /
                      (Number(total) || 1)) *
                      100,
                  )}%`,
                  background: "var(--green, #22c55e)",
                  borderRadius: 3,
                  transition: "width 0.3s",
                }}
              />
            </div>
          </div>
        )}

        {detailInvoice.status !== "paid" &&
          detailInvoice.status !== "cancelled" &&
          detailInvoice.status !== "draft" && (
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
                Record Payment
              </div>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <span
                  style={{
                    color: "var(--text-muted)",
                    fontSize: "0.85rem",
                  }}
                >
                  $
                </span>
                <input
                  type="number"
                  value={paymentAmount}
                  onChange={(event) => onPaymentAmountChange(event.target.value)}
                  min={0}
                  step="0.01"
                  placeholder="Amount"
                  style={{ width: 120 }}
                />
                <button
                  onClick={() => onRecordPayment(detailInvoice.id)}
                  disabled={
                    recordingPayment || !paymentAmount || Number(paymentAmount) <= 0
                  }
                  style={{
                    background: "rgba(34,197,94,0.1)",
                    border: "1px solid rgba(34,197,94,0.3)",
                    borderRadius: 6,
                    padding: "6px 12px",
                    color: "#22c55e",
                    cursor: "pointer",
                    fontSize: "0.8rem",
                    fontWeight: 600,
                  }}
                >
                  {recordingPayment ? "Recording..." : "Record"}
                </button>
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
          {(detailInvoice.status === "draft" || detailInvoice.status === "sent") && (
            <button
              onClick={() => {
                onClose();
                onOpenSend(detailInvoice);
              }}
              style={{
                background: "rgba(59,130,246,0.1)",
                border: "1px solid rgba(59,130,246,0.3)",
                borderRadius: 8,
                padding: "8px 16px",
                color: "#3b82f6",
                cursor: "pointer",
                fontSize: "0.85rem",
                fontWeight: 600,
              }}
            >
              Send Invoice
            </button>
          )}
          {(detailInvoice.status === "sent" ||
            detailInvoice.status === "viewed" ||
            detailInvoice.status === "overdue") && (
            <button
              onClick={() => onMarkPaid(detailInvoice.id)}
              disabled={markingPaid}
              style={{
                background: "rgba(34,197,94,0.1)",
                border: "1px solid rgba(34,197,94,0.3)",
                borderRadius: 8,
                padding: "8px 16px",
                color: "#22c55e",
                cursor: "pointer",
                fontSize: "0.85rem",
                fontWeight: 600,
              }}
            >
              {markingPaid ? "Marking..." : "Mark as Paid"}
            </button>
          )}
          <button onClick={onClose} className="btn-primary">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
