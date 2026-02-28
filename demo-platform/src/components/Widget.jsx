import { useState } from 'react';
import MiniChat from './MiniChat';

const DEFAULT_CONFIG = {
  color: '#00BFFF',
  botName: 'AgentNexLiFy AI',
  greeting: 'Hi there! \uD83D\uDC4B How can I help you today?',
  position: 'bottom-right',
};

function EmbedCode({ config }) {
  const [copied, setCopied] = useState(false);

  const code = `<script src="https://cdn.agentnexlify.com/widget.js"
        data-key="YOUR_API_KEY"
        data-color="${config.color}"
        data-name="${config.botName}"
        data-greeting="${config.greeting}"
        data-position="${config.position}">
</script>`;

  const handleCopy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  // Basic syntax highlighting
  const highlighted = code
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/(src|data-key|data-color|data-name|data-greeting|data-position)=/g, '<span class="code-attr">$1</span>=')
    .replace(/"([^"]*)"/g, '<span class="code-string">"$1"</span>')
    .replace(/(&lt;script|&lt;\/script&gt;)/g, '<span class="code-tag">$1</span>');

  return (
    <div className="widget-embed-section">
      <div className="widget-section-label">Embed Code</div>
      <div className="widget-code-block">
        <pre dangerouslySetInnerHTML={{ __html: highlighted }} />
        <button className="widget-copy-btn" onClick={handleCopy}>
          {copied ? '\u2713 Copied!' : 'Copy Code'}
        </button>
      </div>
    </div>
  );
}

export default function Widget() {
  const [config, setConfig] = useState({ ...DEFAULT_CONFIG });

  const updateConfig = (key, value) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <>
      <div className="page-header">
        <h1>Widget Demo</h1>
        <p>Embeddable chatbot widget — customize and deploy on any website</p>
      </div>

      <div className="widget-layout">
        {/* Left: Live Preview */}
        <div className="widget-preview-panel">
          <div className="widget-section-label">Live Preview</div>
          <div className="widget-mockup">
            {/* Fake webpage backdrop */}
            <div className="widget-mockup-browser">
              <div className="widget-mockup-toolbar">
                <div className="widget-mockup-dots">
                  <span /><span /><span />
                </div>
                <div className="widget-mockup-url">yourwebsite.com</div>
              </div>
              <div className="widget-mockup-page">
                <div className="widget-mockup-content">
                  <div className="widget-mockup-line" style={{ width: '70%' }} />
                  <div className="widget-mockup-line" style={{ width: '90%' }} />
                  <div className="widget-mockup-line" style={{ width: '55%' }} />
                  <div className="widget-mockup-line" style={{ width: '80%', marginTop: 20 }} />
                  <div className="widget-mockup-line" style={{ width: '65%' }} />
                  <div className="widget-mockup-line" style={{ width: '45%' }} />
                </div>
                <MiniChat config={config} />
              </div>
            </div>
          </div>
        </div>

        {/* Right: Configurator + Embed Code */}
        <div className="widget-config-panel">
          <div className="widget-configurator">
            <div className="widget-section-label">Widget Configurator</div>

            <div className="widget-config-field">
              <label>Primary Color</label>
              <div className="widget-color-row">
                <input
                  type="color"
                  value={config.color}
                  onChange={(e) => updateConfig('color', e.target.value)}
                  className="widget-color-input"
                />
                <span className="widget-color-value">{config.color}</span>
              </div>
            </div>

            <div className="widget-config-field">
              <label>Bot Name</label>
              <input
                type="text"
                value={config.botName}
                onChange={(e) => updateConfig('botName', e.target.value)}
                className="widget-text-input"
                maxLength={40}
              />
            </div>

            <div className="widget-config-field">
              <label>Greeting Message</label>
              <textarea
                value={config.greeting}
                onChange={(e) => updateConfig('greeting', e.target.value)}
                className="widget-textarea"
                rows={3}
                maxLength={200}
              />
            </div>

            <div className="widget-config-field">
              <label>Position</label>
              <div className="widget-position-selector">
                {['bottom-right', 'bottom-left'].map((pos) => (
                  <button
                    key={pos}
                    className={`widget-position-btn ${config.position === pos ? 'active' : ''}`}
                    onClick={() => updateConfig('position', pos)}
                    style={config.position === pos ? { borderColor: config.color, color: config.color, background: `${config.color}15` } : undefined}
                  >
                    {pos === 'bottom-right' ? 'Bottom Right' : 'Bottom Left'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <EmbedCode config={config} />
        </div>
      </div>

      {/* Stats row */}
      <div className="widget-stats-row">
        {[
          { icon: '\u26A1', text: '< 2 min setup' },
          { icon: '\uD83D\uDEE0\uFE0F', text: 'No coding required' },
          { icon: '\uD83C\uDF10', text: 'Works on any website' },
          { icon: '\uD83D\uDEE1\uFE0F', text: 'GDPR compliant' },
        ].map((stat, i) => (
          <div key={i} className="widget-stat-item">
            <span className="widget-stat-icon">{stat.icon}</span>
            <span>{stat.text}</span>
          </div>
        ))}
      </div>
    </>
  );
}
