import StatusBadge from "./StatusBadge";
import { overlay, modalBase, sectionLabel } from "./styles";
import { formatDate, sanitizeDocHtml } from "./utils";

export default function DocumentDetail({
  detailDoc,
  copiedId,
  onClose,
  onCopyLink,
  onSend,
  onDelete,
}) {
  if (!detailDoc) return null;
  return (
    <div style={overlay} onClick={onClose}>
      <div
        style={{
          ...modalBase,
          width: "90%",
          maxWidth: 620,
          maxHeight: "85vh",
          overflowY: "auto",
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
            <h3 style={{ marginBottom: 6 }}>
              {detailDoc.title || "Untitled Document"}
            </h3>
            <StatusBadge status={detailDoc.status} />
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

        <div style={{ marginBottom: 16 }}>
          <div style={sectionLabel}>Signer Details</div>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 4,
              fontSize: "0.85rem",
              color: "var(--text-secondary)",
            }}
          >
            {detailDoc.signer_name && (
              <div>
                <strong>Name:</strong> {detailDoc.signer_name}
              </div>
            )}
            {detailDoc.signer_email && (
              <div>
                <strong>Email:</strong> {detailDoc.signer_email}
              </div>
            )}
            {detailDoc.signer_phone && (
              <div>
                <strong>Phone:</strong> {detailDoc.signer_phone}
              </div>
            )}
            {!detailDoc.signer_name &&
              !detailDoc.signer_email &&
              !detailDoc.signer_phone && (
                <div
                  style={{
                    color: "var(--text-muted)",
                    fontStyle: "italic",
                  }}
                >
                  No signer assigned
                </div>
              )}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            gap: 20,
            marginBottom: 16,
            fontSize: "0.85rem",
            color: "var(--text-secondary)",
            flexWrap: "wrap",
          }}
        >
          {detailDoc.created_at && (
            <div>
              <strong>Created:</strong> {formatDate(detailDoc.created_at)}
            </div>
          )}
          {detailDoc.sent_at && (
            <div>
              <strong>Sent:</strong> {formatDate(detailDoc.sent_at)}
            </div>
          )}
          {detailDoc.signed_at && (
            <div>
              <strong>Signed:</strong> {formatDate(detailDoc.signed_at)}
            </div>
          )}
          {detailDoc.expires_at && (
            <div>
              <strong>Expires:</strong> {formatDate(detailDoc.expires_at)}
            </div>
          )}
        </div>

        {(detailDoc.status === "sent" || detailDoc.status === "viewed") && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ ...sectionLabel, marginBottom: 4 }}>Signing Link</div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                readOnly
                value={
                  detailDoc.signing_url ||
                  `${window.location.origin}/sign/${detailDoc.id}`
                }
                style={{
                  flex: 1,
                  fontSize: "0.8rem",
                  background: "var(--bg-secondary)",
                  color: "var(--text-secondary)",
                }}
              />
              <button
                onClick={() => onCopyLink(detailDoc)}
                style={{
                  background:
                    copiedId === detailDoc.id
                      ? "rgba(34,197,94,0.1)"
                      : "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  padding: "6px 12px",
                  color:
                    copiedId === detailDoc.id
                      ? "#22c55e"
                      : "var(--text-secondary)",
                  cursor: "pointer",
                  fontSize: "0.8rem",
                  whiteSpace: "nowrap",
                }}
              >
                {copiedId === detailDoc.id ? "Copied!" : "Copy Link"}
              </button>
            </div>
          </div>
        )}

        {detailDoc.notes && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ ...sectionLabel, marginBottom: 4 }}>Notes</div>
            <div
              style={{
                fontSize: "0.85rem",
                color: "var(--text-secondary)",
                lineHeight: 1.5,
              }}
            >
              {detailDoc.notes}
            </div>
          </div>
        )}

        {detailDoc.html_content && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ ...sectionLabel, marginBottom: 4 }}>
              Document Preview
            </div>
            <div
              style={{
                background: "#fff",
                color: "#1a1a1a",
                borderRadius: 8,
                padding: 16,
                maxHeight: 300,
                overflowY: "auto",
                border: "1px solid var(--border)",
                fontSize: "0.85rem",
                lineHeight: 1.6,
              }}
              dangerouslySetInnerHTML={{
                __html: sanitizeDocHtml(detailDoc.html_content),
              }}
            />
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
          {detailDoc.status === "draft" && (
            <>
              <button
                onClick={() => {
                  onClose();
                  onSend(detailDoc);
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
                Send Document
              </button>
              <button
                onClick={() => {
                  onClose();
                  onDelete(detailDoc.id);
                }}
                style={{
                  background: "rgba(239,68,68,0.1)",
                  border: "1px solid rgba(239,68,68,0.3)",
                  borderRadius: 8,
                  padding: "8px 16px",
                  color: "#ef4444",
                  cursor: "pointer",
                  fontSize: "0.85rem",
                  fontWeight: 600,
                }}
              >
                Delete
              </button>
            </>
          )}
          <button onClick={onClose} className="btn-primary">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
