export default function SmsComposeModal({
  smsPhone,
  setSmsPhone,
  smsMessage,
  setSmsMessage,
  sendingSms,
  smsError,
  smsSent,
  onSend,
  onClose,
}) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: 460 }}
      >
        <h3 style={{ margin: "0 0 16px" }}>New SMS Message</h3>

        {smsError && (
          <div
            style={{
              marginBottom: 12,
              padding: "8px 12px",
              borderRadius: 6,
              fontSize: "0.85rem",
              background: "rgba(239,68,68,0.08)",
              border: "1px solid rgba(239,68,68,0.2)",
              color: "var(--red, #ef4444)",
            }}
          >
            {smsError}
          </div>
        )}

        {smsSent && (
          <div
            style={{
              marginBottom: 12,
              padding: "8px 12px",
              borderRadius: 6,
              fontSize: "0.85rem",
              background: "rgba(34,197,94,0.08)",
              border: "1px solid rgba(34,197,94,0.2)",
              color: "var(--green, #4ade80)",
            }}
          >
            SMS sent successfully.
          </div>
        )}

        <div className="modal-field">
          <label>Phone Number</label>
          <input
            className="modal-input"
            placeholder="+1 (555) 123-4567"
            value={smsPhone}
            onChange={(e) => setSmsPhone(e.target.value)}
            disabled={sendingSms}
          />
        </div>
        <div className="modal-field">
          <label>Message</label>
          <textarea
            className="modal-textarea"
            rows={4}
            placeholder="Type your message..."
            value={smsMessage}
            onChange={(e) => setSmsMessage(e.target.value)}
            disabled={sendingSms}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSend();
              }
            }}
          />
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
            Press Enter to send, Shift+Enter for new line.
          </span>
        </div>

        <div className="modal-actions">
          <button
            className="btn-primary"
            onClick={onSend}
            disabled={sendingSms || !smsPhone.trim() || !smsMessage.trim()}
          >
            {sendingSms ? "Sending..." : "Send SMS"}
          </button>
          <button
            className="btn-secondary"
            onClick={onClose}
            disabled={sendingSms}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
