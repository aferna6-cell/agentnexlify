import { calcTotal, formatCurrency } from "./invoiceUtils";

export default function InvoiceSendModal({
  sendTarget,
  sendMethod,
  setSendMethod,
  sending,
  onClose,
  onSend,
}) {
  if (!sendTarget) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1100,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "var(--bg-primary)",
          borderRadius: 12,
          padding: 24,
          width: "90%",
          maxWidth: 480,
          border: "1px solid var(--border)",
        }}
        onClick={(event) => event.stopPropagation()}
      >
        <h3 style={{ marginBottom: 4 }}>Send Invoice</h3>
        <p
          style={{
            fontSize: "0.85rem",
            color: "var(--text-muted)",
            marginBottom: 20,
          }}
        >
          Invoice #{sendTarget.invoice_number || sendTarget.id?.slice(0, 8)} -{" "}
          {formatCurrency(
            sendTarget.total ??
              calcTotal(
                sendTarget.items_json || sendTarget.items || [],
                sendTarget.tax_rate || 0,
              ),
          )}
        </p>

        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--text-secondary)",
              marginBottom: 10,
              fontWeight: 600,
            }}
          >
            Send Method
          </div>
          {["email", "sms", "both"].map((method) => (
            <label
              key={method}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                marginBottom: 10,
                cursor: "pointer",
              }}
            >
              <input
                type="radio"
                name="send-method"
                value={method}
                checked={sendMethod === method}
                onChange={() => setSendMethod(method)}
                style={{ width: "auto" }}
              />
              <span style={{ fontSize: "0.9rem", textTransform: "capitalize" }}>
                {method === "both" ? "Email + SMS" : method.toUpperCase()}
              </span>
            </label>
          ))}
        </div>

        <div
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            padding: 12,
            marginBottom: 20,
            fontSize: "0.8rem",
            color: "var(--text-secondary)",
            lineHeight: 1.6,
          }}
        >
          <strong>Preview:</strong>
          <br />
          {sendMethod === "sms" || sendMethod === "both"
            ? `SMS: "Invoice #${sendTarget.invoice_number || sendTarget.id?.slice(0, 8)} for ${formatCurrency(sendTarget.total ?? 0)} is ready. Pay at: [payment link]"`
            : null}
          {(sendMethod === "email" || sendMethod === "both") && (
            <span>
              {sendMethod === "both" && <br />}
              Email: Professional invoice with itemized breakdown, payment link,
              and your business details.
            </span>
          )}
        </div>

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "8px 16px",
              color: "var(--text-primary)",
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
          <button className="btn-primary" onClick={onSend} disabled={sending}>
            {sending ? "Sending..." : "Send Invoice"}
          </button>
        </div>
      </div>
    </div>
  );
}
