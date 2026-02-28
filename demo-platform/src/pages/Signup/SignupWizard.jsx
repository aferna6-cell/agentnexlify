import { useState, useCallback } from 'react';
import MiniChat from '../../components/MiniChat';

const API_BASE = import.meta.env.VITE_API_URL || '';

const INDUSTRIES = [
  { value: 'plumbing', label: 'Plumbing' },
  { value: 'dental', label: 'Dental' },
  { value: 'restaurant', label: 'Restaurant' },
  { value: 'realestate', label: 'Real Estate' },
  { value: 'legal', label: 'Legal' },
  { value: 'fitness', label: 'Fitness' },
  { value: 'other', label: 'Other' },
];

const STEPS = ['Business Info', 'Customize Widget', 'Install & Share'];

function ProgressBar({ step }) {
  return (
    <div className="signup-progress">
      {STEPS.map((label, i) => (
        <div key={label} className={`signup-progress-step ${i < step ? 'completed' : ''} ${i === step ? 'active' : ''}`}>
          <div className="signup-progress-dot">
            {i < step ? '\u2713' : i + 1}
          </div>
          <span className="signup-progress-label">{label}</span>
          {i < STEPS.length - 1 && <div className="signup-progress-line" />}
        </div>
      ))}
    </div>
  );
}

function EmbedCodeBlock({ code }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const highlighted = code
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/(src|data-key|data-color|data-name|data-greeting|data-position)=/g, '<span class="code-attr">$1</span>=')
    .replace(/"([^"]*)"/g, '<span class="code-string">"$1"</span>')
    .replace(/(&lt;script|&lt;\/script&gt;)/g, '<span class="code-tag">$1</span>');

  return (
    <div className="widget-code-block">
      <pre dangerouslySetInnerHTML={{ __html: highlighted }} />
      <button className="widget-copy-btn" onClick={handleCopy}>
        {copied ? '\u2713 Copied!' : 'Copy Code'}
      </button>
    </div>
  );
}

export default function SignupWizard() {
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Step 1 fields
  const [businessName, setBusinessName] = useState('');
  const [ownerName, setOwnerName] = useState('');
  const [email, setEmail] = useState('');
  const [industry, setIndustry] = useState('other');
  const [city, setCity] = useState('');

  // Signup result
  const [clientId, setClientId] = useState('');
  const [widgetApiKey, setWidgetApiKey] = useState('');
  const [embedCode, setEmbedCode] = useState('');

  // Step 2 fields
  const [botName, setBotName] = useState('NexLiFy AI');
  const [brandColor, setBrandColor] = useState('#00BFFF');
  const [greeting, setGreeting] = useState('Hi there! How can I help you today?');
  const [position, setPosition] = useState('bottom-right');

  const widgetConfig = {
    color: brandColor,
    botName,
    greeting,
    position,
  };

  const validateEmail = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);

  const handleStep1Submit = useCallback(async () => {
    setError('');
    if (!businessName.trim() || !ownerName.trim() || !email.trim() || !city.trim()) {
      setError('Please fill in all required fields.');
      return;
    }
    if (!validateEmail(email)) {
      setError('Please enter a valid email address.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business_name: businessName.trim(),
          owner_name: ownerName.trim(),
          email: email.trim(),
          industry,
          city: city.trim(),
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Signup failed. Please try again.');
      }

      const data = await res.json();
      setClientId(data.client_id);
      setWidgetApiKey(data.widget_api_key);
      setEmbedCode(data.embed_code);
      setStep(1);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [businessName, ownerName, email, industry, city]);

  const handleStep2Submit = useCallback(async () => {
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/signup/${clientId}/widget`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-Widget-Key': widgetApiKey,
        },
        body: JSON.stringify({
          bot_name: botName,
          brand_color: brandColor,
          greeting_message: greeting,
          position,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to save widget config.');
      }

      // Update embed code with customized values
      const updatedEmbed =
        `<script src="https://cdn.agentnexlify.com/widget.js"\n` +
        `        data-key="${widgetApiKey}"\n` +
        `        data-color="${brandColor}"\n` +
        `        data-name="${botName}"\n` +
        `        data-greeting="${greeting}"\n` +
        `        data-position="${position}">\n` +
        `</script>`;
      setEmbedCode(updatedEmbed);
      setStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [clientId, widgetApiKey, botName, brandColor, greeting, position]);

  const referralLink = `https://agentnexlify.com/?ref=${clientId}`;
  const [refCopied, setRefCopied] = useState(false);
  const copyReferral = () => {
    navigator.clipboard.writeText(referralLink).then(() => {
      setRefCopied(true);
      setTimeout(() => setRefCopied(false), 2000);
    });
  };

  return (
    <div className="signup-container">
      {/* Logo */}
      <div className="signup-logo">
        <span className="signup-logo-icon">N</span>
        <span className="signup-logo-text">AgentNexLiFy</span>
      </div>

      <ProgressBar step={step} />

      {error && <div className="signup-error">{error}</div>}

      {/* Step 1: Business Info */}
      {step === 0 && (
        <div className="signup-card fade-in">
          <h2>Tell us about your business</h2>
          <p className="signup-card-subtitle">Set up your free AI chatbot in under 2 minutes</p>

          <div className="signup-form">
            <div className="widget-config-field">
              <label>Business Name *</label>
              <input
                type="text"
                className="widget-text-input"
                placeholder="Acme Plumbing Co."
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                maxLength={100}
              />
            </div>

            <div className="widget-config-field">
              <label>Your Name *</label>
              <input
                type="text"
                className="widget-text-input"
                placeholder="John Smith"
                value={ownerName}
                onChange={(e) => setOwnerName(e.target.value)}
                maxLength={100}
              />
            </div>

            <div className="widget-config-field">
              <label>Email *</label>
              <input
                type="email"
                className="widget-text-input"
                placeholder="john@acmeplumbing.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div className="widget-config-field">
              <label>Industry</label>
              <select
                className="widget-text-input"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
              >
                {INDUSTRIES.map((ind) => (
                  <option key={ind.value} value={ind.value}>{ind.label}</option>
                ))}
              </select>
            </div>

            <div className="widget-config-field">
              <label>City *</label>
              <input
                type="text"
                className="widget-text-input"
                placeholder="San Francisco"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                maxLength={100}
              />
            </div>

            <button
              className="signup-btn"
              onClick={handleStep1Submit}
              disabled={loading}
            >
              {loading ? 'Creating your account...' : 'Continue'}
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Customize Widget */}
      {step === 1 && (
        <div className="signup-card signup-card-wide fade-in">
          <h2>Customize your widget</h2>
          <p className="signup-card-subtitle">Make it match your brand — changes appear live in the preview</p>

          <div className="signup-customize-layout">
            <div className="signup-customize-form">
              <div className="widget-config-field">
                <label>Bot Name</label>
                <input
                  type="text"
                  className="widget-text-input"
                  value={botName}
                  onChange={(e) => setBotName(e.target.value)}
                  maxLength={40}
                />
              </div>

              <div className="widget-config-field">
                <label>Primary Color</label>
                <div className="widget-color-row">
                  <input
                    type="color"
                    value={brandColor}
                    onChange={(e) => setBrandColor(e.target.value)}
                    className="widget-color-input"
                  />
                  <span className="widget-color-value">{brandColor}</span>
                </div>
              </div>

              <div className="widget-config-field">
                <label>Greeting Message</label>
                <textarea
                  className="widget-textarea"
                  value={greeting}
                  onChange={(e) => setGreeting(e.target.value)}
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
                      className={`widget-position-btn ${position === pos ? 'active' : ''}`}
                      onClick={() => setPosition(pos)}
                      style={position === pos ? { borderColor: brandColor, color: brandColor, background: `${brandColor}15` } : undefined}
                    >
                      {pos === 'bottom-right' ? 'Bottom Right' : 'Bottom Left'}
                    </button>
                  ))}
                </div>
              </div>

              <button
                className="signup-btn"
                onClick={handleStep2Submit}
                disabled={loading}
              >
                {loading ? 'Saving...' : 'Save & Continue'}
              </button>
            </div>

            {/* Live preview */}
            <div className="signup-preview-panel">
              <div className="widget-section-label">Live Preview</div>
              <div className="signup-preview-mockup">
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
                    </div>
                    <MiniChat config={widgetConfig} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Install & Share */}
      {step === 2 && (
        <div className="signup-card fade-in">
          <h2>You're all set!</h2>
          <p className="signup-card-subtitle">Add this snippet to your website to activate your AI chatbot</p>

          <div className="signup-form">
            <div className="signup-embed-section">
              <div className="widget-section-label">Embed Code</div>
              <EmbedCodeBlock code={embedCode} />
            </div>

            <div className="signup-install-steps">
              <div className="widget-section-label">How to install</div>
              <ol>
                <li>Copy the embed code above</li>
                <li>Paste it before the closing <code>&lt;/body&gt;</code> tag on your website</li>
                <li>Save and publish — your chatbot will appear immediately</li>
              </ol>
            </div>

            <div className="signup-referral">
              <div className="signup-referral-header">Share & Earn</div>
              <p>Invite other business owners and earn credits when they sign up.</p>
              <div className="signup-referral-link-row">
                <input
                  type="text"
                  className="widget-text-input"
                  value={referralLink}
                  readOnly
                />
                <button className="signup-referral-copy" onClick={copyReferral}>
                  {refCopied ? '\u2713 Copied!' : 'Copy Link'}
                </button>
              </div>
            </div>

            <a className="signup-btn" href="/" style={{ textAlign: 'center', textDecoration: 'none', display: 'block' }}>
              Go to Dashboard
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
