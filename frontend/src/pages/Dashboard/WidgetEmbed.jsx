import { useState } from "react";

export default function WidgetEmbed({ apiKey, tenantId, widgetConfig }) {
  const [copied, setCopied] = useState(false);

  const displayKey = apiKey || "your-api-key";
  const embedCode = `<script src="https://app.agentnexlify.com/widget/agentnexlify-widget.js" data-api-key="${displayKey}"></script>`;

  const isConfigured = widgetConfig &&
    (widgetConfig.greeting_message !== "Hi! How can I help you today?" ||
     widgetConfig.primary_color !== "#00BFFF");

  function handleCopy() {
    navigator.clipboard.writeText(embedCode).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="widget-embed-section">
      <div className="widget-section-label">Widget Embed Code</div>

      <div className="widget-status-row">
        <span className={`widget-status-dot ${apiKey ? "active" : "inactive"}`} />
        <span className="widget-status-text">
          {apiKey ? "Widget Active" : "Widget Not Configured"}
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
            <span className="code-attr">src</span>=
            <span className="code-string">"https://app.agentnexlify.com/widget/agentnexlify-widget.js"</span>{" "}
            <span className="code-attr">data-api-key</span>=
            <span className="code-string">"{displayKey}"</span>
            <span className="code-tag">&gt;&lt;/script&gt;</span>
          </code>
        </pre>
        <button className="widget-copy-btn" onClick={handleCopy}>
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>

      <a href="#widget" className="widget-customize-link">
        Customize Widget Appearance &rarr;
      </a>
    </div>
  );
}
