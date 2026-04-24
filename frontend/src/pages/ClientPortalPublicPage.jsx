import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://agentnexlify-production.up.railway.app";

export default function ClientPortalPublicPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [widgetLoading, setWidgetLoading] = useState(false);
  const widgetInjected = useRef(false);

  useEffect(() => {
    if (!token) return;
    fetch(`${API_BASE}/api/v1/portal/portal/${token}`, {
      headers: { "Content-Type": "application/json" },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Portal link is invalid or expired.");
        return res.json();
      })
      .then(setData)
      .catch((err) => setError(err.message || "Failed to load portal."))
      .finally(() => setLoading(false));
  }, [token]);

  // Cleanup widget on unmount
  useEffect(() => {
    return () => {
      const el = document.getElementById("anx-portal-widget");
      if (el) el.remove();
      const container = document.getElementById("anx-container");
      if (container) container.remove();
      const host = document.getElementById("anx-chat-widget");
      if (host) host.remove();
      const nexHost = document.getElementById("nexlify-chat-widget");
      if (nexHost) nexHost.remove();
      window.__agentNexlifyWidget = false;
      window.__nexlifyWidgetLoaded = false;
      window.__anxWidgetLoaded = false;
    };
  }, []);

  const handleBookAgain = () => {
    if (widgetInjected.current) {
      // Widget already loaded - just open it
      const bubble =
        document.querySelector("#anx-chat-widget")?.shadowRoot?.querySelector(".anx-bubble") ||
        document.querySelector("#nexlify-chat-widget")?.shadowRoot?.querySelector(".nex-bubble");
      if (bubble) bubble.click();
      return;
    }

    if (!data?.api_key) return;

    setWidgetLoading(true);
    const script = document.createElement("script");
    script.id = "anx-portal-widget";
    script.async = true;
    script.src = `${data.api_base || API_BASE}/widget/agentnexlify-widget.js`;
    script.setAttribute("data-api-key", data.api_key);
    script.setAttribute("data-api-base", data.api_base || API_BASE);
    script.onload = () => {
      widgetInjected.current = true;
      setWidgetLoading(false);
      // Auto-open the widget after a brief delay
      setTimeout(() => {
        const bubble =
          document.querySelector("#anx-chat-widget")?.shadowRoot?.querySelector(".anx-bubble") ||
          document.querySelector("#nexlify-chat-widget")?.shadowRoot?.querySelector(".nex-bubble");
        if (bubble) bubble.click();
      }, 800);
    };
    script.onerror = () => {
      setWidgetLoading(false);
    };
    document.body.appendChild(script);
  };

  if (loading) {
    return (
      <>
        <style>{portalStyles}</style>
        <div className="cp-page">
          <div className="cp-loading">
            <div className="cp-spinner" />
            <p>Loading your portal...</p>
          </div>
        </div>
      </>
    );
  }

  if (error || !data) {
    return (
      <>
        <style>{portalStyles}</style>
        <div className="cp-page">
          <div className="cp-error">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#ff4444" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="M15 9l-6 6M9 9l6 6" />
            </svg>
            <h1>Portal Not Available</h1>
            <p>{error || "This portal link is invalid or has expired."}</p>
            <a href="https://agentnexlify.com" className="cp-back-link">
              Visit AgentNexLiFy
            </a>
          </div>
        </div>
      </>
    );
  }

  const serviceRecords = data.service_records || [];
  const customerName = data.customer_name || "Customer";
  const businessName = data.business_name || "Business";

  return (
    <>
      <style>{portalStyles}</style>
      <div className="cp-page">
        {/* Header */}
        <header className="cp-header">
          <div className="cp-header-inner">
            <div className="cp-header-logo">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#00bfff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <path d="M9 12l2 2 4-4" />
              </svg>
              <span className="cp-header-biz">{businessName}</span>
            </div>
            <div className="cp-header-greeting">
              Welcome, {customerName}
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="cp-main">
          <div className="cp-welcome-card">
            <h2>Your Service History</h2>
            <p>
              Hi {customerName}, here is your service history with {businessName}.
              Need to schedule another visit? Click the button below.
            </p>
            <button
              className="cp-book-btn"
              onClick={handleBookAgain}
              disabled={widgetLoading || !data.api_key}
            >
              {widgetLoading ? (
                <>
                  <div className="cp-btn-spinner" />
                  Loading...
                </>
              ) : (
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M19 4H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z" />
                    <path d="M16 2v4M8 2v4M3 10h18" />
                  </svg>
                  Book Again
                </>
              )}
            </button>
            {data.client_login_enabled && (
              <CreateAccountSection portalToken={token} businessSlug={data.business?.business_slug} />
            )}
          </div>

          {/* Service Records */}
          {serviceRecords.length > 0 ? (
            <div className="cp-records">
              {serviceRecords.map((record) => (
                <div key={record.id} className="cp-record-card">
                  <div className="cp-record-header">
                    <span className="cp-record-title">{record.title || record.service_type || "Service"}</span>
                    <span className={`cp-record-status cp-status-${(record.status || "completed").toLowerCase()}`}>
                      {record.status || "completed"}
                    </span>
                  </div>
                  {record.description && (
                    <p className="cp-record-desc">{record.description}</p>
                  )}
                  <div className="cp-record-meta">
                    {record.service_date && (
                      <span className="cp-record-date">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M19 4H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z" />
                          <path d="M16 2v4M8 2v4M3 10h18" />
                        </svg>
                        {new Date(record.service_date).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </span>
                    )}
                    {record.amount != null && (
                      <span className="cp-record-amount">${Number(record.amount).toFixed(2)}</span>
                    )}
                  </div>
                  {record.notes && (
                    <p className="cp-record-notes">{record.notes}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="cp-empty">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#5c5c72" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
              </svg>
              <h3>No Service Records Yet</h3>
              <p>
                Your service history will appear here after your first appointment with {businessName}.
                Book your first visit to get started!
              </p>
              <button className="cp-book-btn cp-book-btn-sm" onClick={handleBookAgain} disabled={widgetLoading || !data.api_key}>
                {widgetLoading ? "Loading..." : "Book Now"}
              </button>
            </div>
          )}
        </main>

        {/* Footer */}
        <footer className="cp-footer">
          <a href="https://agentnexlify.com" target="_blank" rel="noopener noreferrer" className="cp-powered">
            Powered by <strong>AgentNexLiFy</strong>
          </a>
        </footer>
      </div>
    </>
  );
}

function CreateAccountSection({ portalToken, businessSlug }) {
  const [show, setShow] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const API = import.meta.env.VITE_API_BASE_URL || "https://agentnexlify-production.up.railway.app";

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${API}/api/v1/portal/client/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ portal_token: portalToken, email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Registration failed");
      setResult({ success: true, message: "Account created! You can now log in anytime." });
    } catch (err) {
      setResult({ success: false, message: err.message });
    } finally {
      setLoading(false);
    }
  };

  if (!show) {
    return (
      <div style={{ textAlign: "center", marginTop: 16 }}>
        <button
          onClick={() => setShow(true)}
          style={{
            background: "none", border: "none", color: "#00bfff",
            fontSize: 13, cursor: "pointer", textDecoration: "underline",
          }}
        >
          Create an account to log in anytime
        </button>
      </div>
    );
  }

  return (
    <div style={{
      marginTop: 20, padding: 20, background: "rgba(0,191,255,0.05)",
      border: "1px solid rgba(0,191,255,0.15)", borderRadius: 12,
    }}>
      <h4 style={{ margin: "0 0 12px", fontSize: 15, color: "#f0f0f5" }}>Create Your Account</h4>
      <p style={{ margin: "0 0 16px", fontSize: 13, color: "#9494a8" }}>
        Set up a login so you can access your portal anytime without a link.
      </p>
      {result && (
        <div style={{
          padding: "8px 12px", borderRadius: 8, marginBottom: 12, fontSize: 13,
          background: result.success ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
          color: result.success ? "#6ee7b7" : "#fca5a5",
          border: `1px solid ${result.success ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)"}`,
        }}>
          {result.message}
          {result.success && businessSlug && (
            <div style={{ marginTop: 8 }}>
              <a href={`/client/login/${businessSlug}`} style={{ color: "#00bfff" }}>
                Go to login page
              </a>
            </div>
          )}
        </div>
      )}
      {!result?.success && (
        <form onSubmit={handleRegister}>
          <input
            type="email" value={email} onChange={(e) => setEmail(e.target.value)}
            placeholder="Your email" required
            style={{
              width: "100%", padding: "10px 12px", background: "rgba(10,10,15,0.8)",
              border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8,
              color: "#f0f0f5", fontSize: 14, marginBottom: 10, boxSizing: "border-box",
            }}
          />
          <input
            type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            placeholder="Choose a password (min 6 chars)" required minLength={6}
            style={{
              width: "100%", padding: "10px 12px", background: "rgba(10,10,15,0.8)",
              border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8,
              color: "#f0f0f5", fontSize: 14, marginBottom: 12, boxSizing: "border-box",
            }}
          />
          <button
            type="submit" disabled={loading}
            style={{
              width: "100%", padding: "10px", background: "#00bfff", border: "none",
              borderRadius: 8, color: "#0a0a0f", fontWeight: 600, fontSize: 14, cursor: "pointer",
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? "Creating..." : "Create Account"}
          </button>
        </form>
      )}
    </div>
  );
}

const portalStyles = `
  /* Reset for portal page */
  .cp-page {
    all: initial;
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0a0a0f;
    color: #f0f0f5;
    -webkit-font-smoothing: antialiased;
  }
  .cp-page *, .cp-page *::before, .cp-page *::after {
    box-sizing: border-box;
  }

  /* Loading */
  .cp-loading {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
  }
  .cp-loading p {
    color: #9494a8;
    font-size: 0.9rem;
  }
  .cp-spinner {
    width: 36px;
    height: 36px;
    border: 3px solid rgba(255,255,255,0.1);
    border-top-color: #00bfff;
    border-radius: 50%;
    animation: cp-spin 0.7s linear infinite;
  }
  @keyframes cp-spin { to { transform: rotate(360deg); } }

  /* Error */
  .cp-error {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2rem;
    gap: 12px;
  }
  .cp-error h1 {
    font-size: 1.4rem;
    font-weight: 700;
    color: #f0f0f5;
    margin: 0;
  }
  .cp-error p {
    color: #9494a8;
    font-size: 0.95rem;
    margin: 0;
    max-width: 400px;
    line-height: 1.5;
  }
  .cp-back-link {
    color: #00bfff;
    text-decoration: none;
    font-weight: 500;
    font-size: 0.9rem;
    margin-top: 8px;
  }
  .cp-back-link:hover { text-decoration: underline; }

  /* Header */
  .cp-header {
    background: #111118;
    border-bottom: 1px solid #222233;
    padding: 16px 24px;
    position: sticky;
    top: 0;
    z-index: 10;
  }
  .cp-header-inner {
    max-width: 800px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }
  .cp-header-logo {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .cp-header-biz {
    font-size: 1.1rem;
    font-weight: 700;
    color: #f0f0f5;
  }
  .cp-header-greeting {
    font-size: 0.85rem;
    color: #9494a8;
  }

  /* Main */
  .cp-main {
    flex: 1;
    max-width: 800px;
    margin: 0 auto;
    width: 100%;
    padding: 24px;
  }

  /* Welcome Card */
  .cp-welcome-card {
    background: #16161f;
    border: 1px solid #222233;
    border-radius: 12px;
    padding: 28px;
    margin-bottom: 24px;
  }
  .cp-welcome-card h2 {
    font-size: 1.25rem;
    font-weight: 700;
    margin: 0 0 8px;
    color: #f0f0f5;
  }
  .cp-welcome-card p {
    color: #9494a8;
    font-size: 0.9rem;
    line-height: 1.6;
    margin: 0 0 20px;
  }

  /* Book Again Button */
  .cp-book-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 12px 24px;
    background: #00bfff;
    color: #000;
    border: none;
    border-radius: 10px;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, transform 0.1s;
    font-family: inherit;
  }
  .cp-book-btn:hover:not(:disabled) { background: #00a8e6; }
  .cp-book-btn:active:not(:disabled) { transform: scale(0.97); }
  .cp-book-btn:disabled { opacity: 0.6; cursor: not-allowed; }
  .cp-book-btn-sm { padding: 10px 20px; font-size: 0.9rem; }

  .cp-btn-spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(0,0,0,0.2);
    border-top-color: #000;
    border-radius: 50%;
    animation: cp-spin 0.6s linear infinite;
  }

  /* Service Records */
  .cp-records {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .cp-record-card {
    background: #16161f;
    border: 1px solid #222233;
    border-radius: 10px;
    padding: 20px;
    transition: border-color 0.15s;
  }
  .cp-record-card:hover {
    border-color: #333344;
  }
  .cp-record-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    gap: 12px;
  }
  .cp-record-title {
    font-size: 1rem;
    font-weight: 600;
    color: #f0f0f5;
  }
  .cp-record-status {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    text-transform: capitalize;
    white-space: nowrap;
  }
  .cp-status-completed {
    background: rgba(52, 211, 153, 0.15);
    color: #34d399;
  }
  .cp-status-pending, .cp-status-scheduled {
    background: rgba(245, 166, 35, 0.15);
    color: #f5a623;
  }
  .cp-status-cancelled {
    background: rgba(255, 68, 68, 0.15);
    color: #ff4444;
  }
  .cp-record-desc {
    font-size: 0.85rem;
    color: #9494a8;
    line-height: 1.5;
    margin: 0 0 10px;
  }
  .cp-record-meta {
    display: flex;
    align-items: center;
    gap: 16px;
    font-size: 0.8rem;
    color: #5c5c72;
  }
  .cp-record-date {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .cp-record-amount {
    font-weight: 600;
    color: #34d399;
  }
  .cp-record-notes {
    margin: 10px 0 0;
    font-size: 0.82rem;
    color: #5c5c72;
    font-style: italic;
    line-height: 1.5;
  }

  /* Empty State */
  .cp-empty {
    text-align: center;
    padding: 48px 24px;
    background: #16161f;
    border: 1px solid #222233;
    border-radius: 12px;
  }
  .cp-empty h3 {
    font-size: 1.1rem;
    font-weight: 600;
    color: #f0f0f5;
    margin: 16px 0 8px;
  }
  .cp-empty p {
    color: #9494a8;
    font-size: 0.85rem;
    line-height: 1.6;
    max-width: 400px;
    margin: 0 auto 20px;
  }

  /* Footer */
  .cp-footer {
    text-align: center;
    padding: 24px;
    border-top: 1px solid #222233;
    margin-top: auto;
  }
  .cp-powered {
    font-size: 0.8rem;
    color: #5c5c72;
    text-decoration: none;
  }
  .cp-powered:hover { color: #9494a8; }
  .cp-powered strong { font-weight: 600; }

  /* Mobile */
  @media (max-width: 640px) {
    .cp-main { padding: 16px; }
    .cp-welcome-card { padding: 20px; }
    .cp-header-inner { flex-direction: column; align-items: flex-start; gap: 4px; }
    .cp-header-greeting { font-size: 0.8rem; }
  }
`;
