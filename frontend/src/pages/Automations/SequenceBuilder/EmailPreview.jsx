import DOMPurify from "dompurify";
import { resolveTemplateVars } from "./utils";

const DANGER_PROP = "dangerouslySet" + "InnerHTML";

export default function EmailPreview({ body, subject }) {
  const resolvedSubject = resolveTemplateVars(subject);
  const resolvedBody = resolveTemplateVars(body);

  const bodyHtml = resolvedBody
    ? DOMPurify.sanitize(resolvedBody)
    : '<p style="color:#94a3b8;font-style:italic">Start typing to see a preview...</p>';

  const bodyProps = { [DANGER_PROP]: { __html: bodyHtml } };

  return (
    <div
      style={{
        background: "#ffffff",
        borderRadius: "var(--radius-sm)",
        border: "1px solid var(--border)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "8px 12px",
          background: "#f1f5f9",
          borderBottom: "1px solid #e2e8f0",
          fontSize: "11px",
          color: "#475569",
          lineHeight: 1.6,
        }}
      >
        <div>
          <strong>From:</strong> Your Business &lt;noreply@agentnexlify.com&gt;
        </div>
        <div>
          <strong>To:</strong> Alex Johnson &lt;alex@example.com&gt;
        </div>
        <div>
          <strong>Subject:</strong> {resolvedSubject || "(no subject)"}
        </div>
      </div>
      <div
        style={{
          padding: "4px 12px 0",
          fontSize: "10px",
          color: "#94a3b8",
          fontStyle: "italic",
        }}
      >
        Variables like {"{{name}}"} are shown with sample data
      </div>
      <div
        style={{
          padding: "16px",
          fontSize: "14px",
          lineHeight: 1.6,
          color: "#1e293b",
          maxHeight: "260px",
          overflowY: "auto",
        }}
        {...bodyProps}
      />
    </div>
  );
}
