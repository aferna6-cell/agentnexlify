import { overlay, modalBase, cancelBtn, warnBox } from "./styles";

export default function SendModal({
  sendTarget,
  sendMethod,
  setSendMethod,
  sending,
  onClose,
  onSend,
}) {
  if (!sendTarget) return null;
  return (
    <div style={{ ...overlay, zIndex: 1100 }} onClick={onClose}>
      <div
        style={{ ...modalBase, width: "90%", maxWidth: 480 }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ marginBottom: 4 }}>Send Document for Signing</h3>
        <p
          style={{
            fontSize: "0.85rem",
            color: "var(--text-muted)",
            marginBottom: 20,
          }}
        >
          {sendTarget.title}
          {sendTarget.signer_name ? ` -- to ${sendTarget.signer_name}` : ""}
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
                name="send-doc-method"
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
          <strong>What happens next:</strong>
          <br />
          The signer will receive a link to view and sign the document.
          {(sendMethod === "email" || sendMethod === "both") &&
            " An email with the signing link and document preview will be sent."}
          {(sendMethod === "sms" || sendMethod === "both") &&
            " An SMS with the signing link will be sent."}{" "}
          You will be notified when the document is viewed or signed.
        </div>

        {sendMethod !== "sms" && !sendTarget.signer_email && (
          <div style={{ ...warnBox("245,158,11"), color: "#f59e0b" }}>
            No signer email set. Email delivery will fail. Edit the document to
            add an email address first.
          </div>
        )}
        {sendMethod !== "email" && !sendTarget.signer_phone && (
          <div style={{ ...warnBox("245,158,11"), color: "#f59e0b" }}>
            No signer phone set. SMS delivery will fail. Edit the document to
            add a phone number first.
          </div>
        )}

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={cancelBtn}>
            Cancel
          </button>
          <button className="btn-primary" onClick={onSend} disabled={sending}>
            {sending ? "Sending..." : "Send Document"}
          </button>
        </div>
      </div>
    </div>
  );
}
