import { PLATFORM_INSTRUCTIONS } from "./constants";

export default function InstallStep({
  platform,
  setPlatform,
  apiKey,
  apiBase,
  copied,
  onCopyEmbed,
  onMarkInstalled,
}) {
  return (
    <div className="onboarding-step-body">
      <div className="platform-tabs">
        {Object.keys(PLATFORM_INSTRUCTIONS).map((p) => (
          <button
            key={p}
            className={`platform-tab${platform === p ? " active" : ""}`}
            onClick={() => setPlatform(p)}
          >
            {p}
          </button>
        ))}
      </div>
      <p className="onboarding-hint">{PLATFORM_INSTRUCTIONS[platform]}</p>
      <div className="widget-code-block">
        <pre>
          <code>
            <span className="code-tag">&lt;script</span>{" "}
            <span className="code-attr">src</span>=
            <span className="code-string">
              "https://app.agentnexlify.com/widget/agentnexlify-widget.js"
            </span>{" "}
            <span className="code-attr">data-api-key</span>=
            <span className="code-string">"{apiKey || "your-api-key"}"</span>{" "}
            <span className="code-attr">data-api-base</span>=
            <span className="code-string">"{apiBase}"</span>
            <span className="code-tag">&gt;&lt;/script&gt;</span>
          </code>
        </pre>
        <button className="widget-copy-btn" onClick={onCopyEmbed}>
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <button className="onboarding-save-btn" onClick={onMarkInstalled}>
        Mark as Installed
      </button>
    </div>
  );
}
