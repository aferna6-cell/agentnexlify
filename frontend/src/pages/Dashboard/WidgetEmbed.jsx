import { useState } from "react";

export default function WidgetEmbed({ config, tenantId }) {
  const [copied, setCopied] = useState(false);

  const apiKey = config?.widget_api_key || "your-api-key";
  const embedCode = `<script src="https://app.agentnexlify.com/widget/agentnexlify-widget.js" data-api-key="${apiKey}"></script>`;

  const domains = config?.allowed_domains || [];
  const isActive = config?.is_active !== false;

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
        <span className={`widget-status-dot ${isActive ? "active" : "inactive"}`} />
        <span className="widget-status-text">
          {isActive ? "Widget Active" : "Widget Inactive"}
        </span>
        {domains.length > 0 && (
          <span className="widget-domains">
            {domains.length} domain{domains.length !== 1 ? "s" : ""} configured
          </span>
        )}
      </div>

      <div className="widget-code-block">
        <pre>
          <code>
            <span className="code-tag">&lt;script</span>{" "}
            <span className="code-attr">src</span>=
            <span className="code-string">"https://app.agentnexlify.com/widget/agentnexlify-widget.js"</span>{" "}
            <span className="code-attr">data-api-key</span>=
            <span className="code-string">"{apiKey}"</span>
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
