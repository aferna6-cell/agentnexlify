import DOMPurify from "dompurify";
import { timeAgo, renderMarkdown } from "./utils";

export default function MessageList({ messages, selectedConv }) {
  return (
    <>
      {messages.map((m) => (
        <div key={m.id} className={`conv-msg ${m.role}`}>
          <div className="conv-msg-role">
            {m.role === "user" ? "Visitor" : "AI"}
          </div>
          {m.role === "assistant" ? (
            <div
              className="conv-msg-content"
              dangerouslySetInnerHTML={{
                __html: DOMPurify.sanitize(renderMarkdown(m.content || "")),
              }}
            />
          ) : (
            <div className="conv-msg-content">{m.content}</div>
          )}
          <div className="conv-msg-time">{timeAgo(m.created_at)}</div>
        </div>
      ))}
      {messages.length === 0 && (
        <div className="conv-empty-state">
          No messages in this conversation.
        </div>
      )}

      {selectedConv?.lead_id && (
        <div
          style={{
            background: "rgba(76, 175, 80, 0.08)",
            border: "1px solid rgba(76, 175, 80, 0.25)",
            borderRadius: 8,
            padding: "8px 12px",
            margin: "10px 0 0",
            textAlign: "center",
            fontSize: "0.8rem",
            color: "#4caf50",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 6,
          }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#4caf50"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span style={{ fontWeight: 600 }}>Lead Captured</span>
          <span
            style={{
              color: "rgba(76, 175, 80, 0.7)",
              fontWeight: 400,
            }}
          >
            {selectedConv.lead_name
              ? `— ${selectedConv.lead_name}`
              : "— Contact info detected"}
          </span>
        </div>
      )}
    </>
  );
}
