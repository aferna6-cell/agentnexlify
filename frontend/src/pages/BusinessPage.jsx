import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { fetchBusinessPagePublic } from "../utils/api";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://agentnexlify-production.up.railway.app";

const COLOR_THEMES = {
  default: { primary: "#3b82f6", bg: "#ffffff", text: "#1a1a1a", muted: "#6b7280", surface: "#f9fafb", border: "#f0f0f0" },
  ocean:   { primary: "#0ea5e9", bg: "#f0f9ff", text: "#0c4a6e", muted: "#64748b", surface: "#e0f2fe", border: "#bae6fd" },
  forest:  { primary: "#16a34a", bg: "#f0fdf4", text: "#14532d", muted: "#4b5563", surface: "#dcfce7", border: "#bbf7d0" },
  sunset:  { primary: "#f97316", bg: "#fff7ed", text: "#431407", muted: "#78716c", surface: "#fed7aa", border: "#fdba74" },
  slate:   { primary: "#64748b", bg: "#f8fafc", text: "#1e293b", muted: "#94a3b8", surface: "#f1f5f9", border: "#e2e8f0" },
  rose:    { primary: "#f43f5e", bg: "#fff1f2", text: "#4c0519", muted: "#6b7280", surface: "#ffe4e6", border: "#fecdd3" },
  amber:   { primary: "#f59e0b", bg: "#fffbeb", text: "#451a03", muted: "#78716c", surface: "#fef3c7", border: "#fde68a" },
  indigo:  { primary: "#6366f1", bg: "#eef2ff", text: "#1e1b4b", muted: "#6b7280", surface: "#e0e7ff", border: "#c7d2fe" },
  emerald: { primary: "#10b981", bg: "#ecfdf5", text: "#064e3b", muted: "#4b5563", surface: "#d1fae5", border: "#a7f3d0" },
  charcoal:{ primary: "#6b7280", bg: "#1f2937", text: "#f9fafb", muted: "#9ca3af", surface: "#374151", border: "#4b5563" },
};

export default function BusinessPage() {
  const { slug } = useParams();
  const [biz, setBiz] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBusinessPagePublic(slug)
      .then(setBiz)
      .catch(() => setError("not_found"))
      .finally(() => setLoading(false));
  }, [slug]);

  // Inject widget script once we have data
  useEffect(() => {
    if (!biz?.widget_api_key) return;
    const existing = document.getElementById("anx-biz-widget");
    if (existing) existing.remove();

    const script = document.createElement("script");
    script.id = "anx-biz-widget";
    script.src = `${API_BASE}/widget/agentnexlify-widget.js`;
    script.setAttribute("data-api-key", biz.widget_api_key);
    script.setAttribute("data-brand-color", biz.widget_primary_color || "#00BFFF");
    script.setAttribute("data-api-base", API_BASE);
    document.body.appendChild(script);

    return () => {
      const el = document.getElementById("anx-biz-widget");
      if (el) el.remove();
      // Clean up widget DOM
      const host = document.getElementById("nexlify-chat-widget");
      if (host) host.remove();
      const anxHost = document.getElementById("anx-chat-widget");
      if (anxHost) anxHost.remove();
      window.__nexlifyWidgetLoaded = false;
      window.__anxWidgetLoaded = false;
    };
  }, [biz]);

  if (loading) {
    return (
      <>
        <style>{baseStyles}</style>
        <div className="bp-loading">
          <div className="bp-spinner" />
        </div>
      </>
    );
  }

  if (error || !biz) {
    return (
      <>
        <style>{baseStyles}</style>
        <div className="bp-error">
          <h1>Page Not Found</h1>
          <p>This business page doesn't exist or hasn't been published yet.</p>
          <a href="https://agentnexlify.com" className="bp-back-link">
            Visit AgentNexLiFy
          </a>
        </div>
      </>
    );
  }

  const theme = COLOR_THEMES[biz.color_theme] || COLOR_THEMES.default;
  const accent = theme.primary;
  const fontFamily = biz.font_family || null;
  const location = [biz.city, biz.state].filter(Boolean).join(", ");
  const logoLetter = (biz.business_name || "B").charAt(0).toUpperCase();
  const mapsQuery = [biz.address, biz.city, biz.state].filter(Boolean).join(", ");
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(mapsQuery)}`;

  const structuredData = {
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    name: biz.business_name,
    ...(biz.description && { description: biz.description }),
    ...(biz.phone && { telephone: biz.phone }),
    ...(biz.logo_url && { image: biz.logo_url }),
    ...(mapsQuery && {
      address: {
        "@type": "PostalAddress",
        ...(biz.address && { streetAddress: biz.address }),
        ...(biz.city && { addressLocality: biz.city }),
        ...(biz.state && { addressRegion: biz.state }),
      },
    }),
    ...(biz.hours_display && { openingHours: biz.hours_display }),
  };

  const openWidget = () => {
    // Try to open the embedded widget
    const bubble =
      document.querySelector("#anx-chat-widget")?.shadowRoot?.querySelector(".anx-bubble") ||
      document.querySelector("#nexlify-chat-widget")?.shadowRoot?.querySelector(".nex-bubble");
    if (bubble) bubble.click();
  };

  return (
    <>
      <Helmet>
        <title>{biz.meta_title || `${biz.business_name}${location ? ` - ${location}` : ""}`}</title>
        <meta
          name="description"
          content={biz.meta_description || biz.description || `${biz.business_name}${location ? ` in ${location}` : ""}. Chat with us online.`}
        />
        <meta property="og:title" content={biz.meta_title || biz.business_name} />
        <meta
          property="og:description"
          content={biz.meta_description || biz.description || `${biz.business_name}${location ? ` in ${location}` : ""}`}
        />
        {biz.logo_url && <meta property="og:image" content={biz.logo_url} />}
        <meta property="og:type" content="website" />
        <script type="application/ld+json">{JSON.stringify(structuredData)}</script>
        {fontFamily && (
          <link
            href={`https://fonts.googleapis.com/css2?family=${encodeURIComponent(fontFamily)}:wght@400;500;600;700&display=swap`}
            rel="stylesheet"
          />
        )}
      </Helmet>

      <style>{baseStyles}</style>
      <style>{`
        .bp-page, .bp-loading, .bp-error {
          background: ${theme.bg};
          color: ${theme.text};
          ${fontFamily ? `font-family: '${fontFamily}', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;` : ""}
        }
        .bp-page *, .bp-loading *, .bp-error * {
          ${fontFamily ? `font-family: inherit;` : ""}
        }
        .bp-header { background: ${theme.bg}; border-bottom-color: ${theme.border}; }
        .bp-biz-name { color: ${theme.text}; }
        .bp-meta-item { color: ${theme.muted}; }
        .bp-description { color: ${theme.muted}; }
        .bp-section-title { color: ${theme.text}; }
        .bp-service-card { background: ${theme.surface}; border-left: 3px solid ${accent}; color: ${theme.text}; }
        .bp-card { border-top-color: ${theme.border}; }
        .bp-hours { color: ${theme.muted}; }
        .bp-contact-item { background: ${theme.surface}; color: ${theme.text}; }
        .bp-contact-item:hover { background: ${theme.border}; }
        .bp-footer { border-top-color: ${theme.border}; }
        .bp-accent { color: ${accent}; }
        .bp-btn-accent { background: ${accent}; }
        .bp-btn-accent:hover { background: ${accent}dd; }
        .bp-avatar-fallback { background: ${accent}22; color: ${accent}; }
        .bp-hero-gradient { background: linear-gradient(135deg, ${accent}18 0%, ${accent}08 100%); }
        .bp-open-badge { background: #22c55e22; color: #16a34a; }
      `}</style>
      {biz.custom_css && <style>{biz.custom_css}</style>}

      <div className="bp-page">
        {/* Header */}
        <header className="bp-header">
          <div className="bp-header-inner">
            {biz.logo_url ? (
              <img src={biz.logo_url} alt={biz.business_name} className="bp-logo" />
            ) : (
              <div className="bp-avatar-fallback">{logoLetter}</div>
            )}
            <div className="bp-header-info">
              <h1 className="bp-biz-name">{biz.business_name}</h1>
              <div className="bp-header-meta">
                {location && (
                  <span className="bp-meta-item">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
                    {location}
                  </span>
                )}
                {biz.phone && (
                  <a href={`tel:${biz.phone}`} className="bp-meta-item bp-phone-link">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>
                    {biz.phone}
                  </a>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Hero */}
        <section className={biz.cover_url ? "bp-hero bp-hero-image" : "bp-hero bp-hero-gradient"}>
          {biz.cover_url && (
            <img src={biz.cover_url} alt="" className="bp-cover-img" />
          )}
          <div className="bp-hero-content">
            {biz.description && <p className="bp-description">{biz.description}</p>}
            <button className="bp-btn bp-btn-accent" onClick={openWidget}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
              Chat with us
            </button>
          </div>
        </section>

        {/* Services */}
        {biz.services && biz.services.length > 0 && (
          <section className="bp-section">
            <h2 className="bp-section-title">Our Services</h2>
            <div className="bp-services-grid">
              {biz.services.map((svc, i) => (
                <div key={i} className="bp-service-card">
                  <span className="bp-service-name">{svc}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Hours & Contact */}
        <div className="bp-two-col">
          {biz.hours_display && (
            <section className="bp-section bp-card">
              <h2 className="bp-section-title">Business Hours</h2>
              <pre className="bp-hours">{biz.hours_display}</pre>
            </section>
          )}

          {(biz.phone || biz.address) && (
            <section className="bp-section bp-card">
              <h2 className="bp-section-title">Contact Us</h2>
              <div className="bp-contact-list">
                {biz.phone && (
                  <a href={`tel:${biz.phone}`} className="bp-contact-item">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>
                    Click to call: {biz.phone}
                  </a>
                )}
                {mapsQuery && (
                  <a href={mapsUrl} target="_blank" rel="noopener noreferrer" className="bp-contact-item">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
                    View on Google Maps
                  </a>
                )}
                <button className="bp-contact-item bp-contact-btn" onClick={openWidget}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
                  Send us a message
                </button>
              </div>
            </section>
          )}
        </div>

        {/* Footer */}
        {!biz.hide_powered_by && (
          <footer className="bp-footer">
            <a href="https://agentnexlify.com" target="_blank" rel="noopener noreferrer" className="bp-powered">
              Powered by <strong>AgentNexLiFy</strong>
            </a>
          </footer>
        )}
      </div>
    </>
  );
}

const baseStyles = `
  /* Reset for business page */
  .bp-page, .bp-loading, .bp-error {
    all: initial;
    display: block;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    color: #1a1a1a;
    background: #fff;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }
  .bp-page *, .bp-loading *, .bp-error * {
    box-sizing: border-box;
  }

  /* Loading */
  .bp-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
  }
  .bp-spinner {
    width: 36px;
    height: 36px;
    border: 3px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: bp-spin 0.7s linear infinite;
  }
  @keyframes bp-spin { to { transform: rotate(360deg); } }

  /* Error */
  .bp-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    text-align: center;
    padding: 2rem;
  }
  .bp-error h1 { font-size: 1.5rem; margin-bottom: 0.5rem; color: #1a1a1a; }
  .bp-error p { color: #6b7280; margin-bottom: 1.5rem; }
  .bp-back-link {
    color: #3b82f6;
    text-decoration: none;
    font-weight: 500;
  }
  .bp-back-link:hover { text-decoration: underline; }

  /* Header */
  .bp-header {
    padding: 1.25rem 1.5rem;
    border-bottom: 1px solid #f0f0f0;
    background: #fff;
    position: sticky;
    top: 0;
    z-index: 10;
  }
  .bp-header-inner {
    max-width: 800px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    gap: 1rem;
  }
  .bp-logo {
    width: 52px;
    height: 52px;
    border-radius: 12px;
    object-fit: cover;
    flex-shrink: 0;
  }
  .bp-avatar-fallback {
    width: 52px;
    height: 52px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    font-weight: 700;
    flex-shrink: 0;
  }
  .bp-header-info { flex: 1; min-width: 0; }
  .bp-biz-name {
    font-size: 1.35rem;
    font-weight: 700;
    margin: 0;
    line-height: 1.2;
    color: #111;
  }
  .bp-header-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-top: 0.25rem;
  }
  .bp-meta-item {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.85rem;
    color: #6b7280;
  }
  .bp-phone-link {
    color: #6b7280;
    text-decoration: none;
  }
  .bp-phone-link:hover { color: #111; }

  /* Hero */
  .bp-hero {
    position: relative;
    padding: 3rem 1.5rem;
    overflow: hidden;
  }
  .bp-hero-image {
    background: #f9fafb;
  }
  .bp-cover-img {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0.15;
  }
  .bp-hero-content {
    position: relative;
    max-width: 800px;
    margin: 0 auto;
  }
  .bp-description {
    font-size: 1.1rem;
    line-height: 1.7;
    color: #374151;
    margin: 0 0 1.5rem;
    max-width: 600px;
  }

  /* Buttons */
  .bp-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 10px;
    font-size: 0.95rem;
    font-weight: 600;
    color: #fff;
    cursor: pointer;
    transition: background 0.15s, transform 0.1s;
  }
  .bp-btn:active { transform: scale(0.97); }

  /* Sections */
  .bp-section {
    padding: 2rem 1.5rem;
    max-width: 800px;
    margin: 0 auto;
  }
  .bp-section-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #111;
    margin: 0 0 1rem;
  }

  /* Services */
  .bp-services-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 0.75rem;
  }
  .bp-service-card {
    background: #f9fafb;
    padding: 0.85rem 1rem;
    border-radius: 8px;
    font-size: 0.95rem;
    font-weight: 500;
    color: #1f2937;
  }

  /* Two-column layout */
  .bp-two-col {
    max-width: 800px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
  }
  @media (max-width: 640px) {
    .bp-two-col { grid-template-columns: 1fr; }
  }

  .bp-card {
    border-top: 1px solid #f0f0f0;
  }

  /* Hours */
  .bp-hours {
    font-family: inherit;
    font-size: 0.9rem;
    line-height: 1.8;
    color: #374151;
    white-space: pre-wrap;
    margin: 0;
  }

  /* Contact */
  .bp-contact-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  .bp-contact-item {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.9rem;
    color: #374151;
    text-decoration: none;
    padding: 0.6rem 0.75rem;
    border-radius: 8px;
    background: #f9fafb;
    border: none;
    cursor: pointer;
    font-family: inherit;
    transition: background 0.15s;
  }
  .bp-contact-item:hover { background: #f0f0f0; }
  .bp-contact-btn { text-align: left; }

  /* Footer */
  .bp-footer {
    text-align: center;
    padding: 2rem 1.5rem;
    border-top: 1px solid #f0f0f0;
    margin-top: 1rem;
  }
  .bp-powered {
    font-size: 0.8rem;
    color: #9ca3af;
    text-decoration: none;
  }
  .bp-powered:hover { color: #6b7280; }
  .bp-powered strong { font-weight: 600; }

  /* Mobile */
  @media (max-width: 640px) {
    .bp-biz-name { font-size: 1.15rem; }
    .bp-hero { padding: 2rem 1.25rem; }
    .bp-description { font-size: 1rem; }
    .bp-section { padding: 1.5rem 1.25rem; }
    .bp-services-grid { grid-template-columns: 1fr; }
  }
`;
