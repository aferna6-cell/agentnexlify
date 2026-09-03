import { useEffect, useState } from "react";
import { getWebsiteConnection } from "../../utils/api/websiteConnect";

export default function WidgetEmbed({
  apiKey,
  tenantId,
  token,
  widgetConfig,
  onNavigate,
}) {
  const [copied, setCopied] = useState(false);
  const [connectStatus, setConnectStatus] = useState(null);

  const displayKey = apiKey || "your-api-key";
  const apiBase =
    import.meta.env.VITE_API_BASE_URL ||
    "https://agentnexlify-production.up.railway.app";
  const embedCode = `<script async src="https://app.agentnexlify.com/widget/agentnexlify-widget.js" data-api-key="${displayKey}" data-api-base="${apiBase}"></script>`;

  const isConfigured =
    widgetConfig &&
    (widgetConfig.greeting_message !== "Hi! How can I help you today?" ||
      widgetConfig.primary_color !== "#00BFFF");
  const live = connectStatus === "connected";

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    getWebsiteConnection(token)
      .then((payload) => {
        if (!cancelled)
          setConnectStatus(
            payload?.connection?.status || payload?.status || "not_started",
          );
      })
      .catch(() => {
        if (!cancelled) setConnectStatus("not_started");
      });
    return () => {
      cancelled = true;
    };
  }, [token, tenantId]);

  function handleCopy() {
    navigator.clipboard.writeText(embedCode).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="widget-embed-section">
      <div className="widget-section-label">Website connection</div>

      <div className="widget-status-row">
        <span className={`widget-status-dot ${live ? "active" : "inactive"}`} />
        <span className="widget-status-text">
          {live
            ? "AI receptionist is live"
            : "Not verified on your website yet"}
        </span>
      </div>

      {!isConfigured && apiKey && (
        <div className="widget-configure-hint">
          Configure your AI agent first to get the most out of your widget.
        </div>
      )}

      <div className="widget-code-block">
        <pre>
          <code>
            <span className="code-tag">&lt;script</span>{" "}
            <span className="code-attr">async</span>{" "}
            <span className="code-attr">src</span>=
            <span className="code-string">
              "https://app.agentnexlify.com/widget/agentnexlify-widget.js"
            </span>{" "}
            <span className="code-attr">data-api-key</span>=
            <span className="code-string">"{displayKey}"</span>{" "}
            <span className="code-attr">data-api-base</span>=
            <span className="code-string">"{apiBase}"</span>
            <span className="code-tag">&gt;&lt;/script&gt;</span>
          </code>
        </pre>
        <button className="widget-copy-btn" onClick={handleCopy}>
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>

      <button
        className="widget-customize-link"
        onClick={() => onNavigate?.("website_connect")}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          font: "inherit",
          color: "inherit",
          padding: 0,
        }}
      >
        Connect and verify your website &rarr;
      </button>
    </div>
  );
}
