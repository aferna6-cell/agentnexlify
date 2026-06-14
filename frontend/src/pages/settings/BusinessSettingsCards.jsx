import { SaveButton } from "./shared";

export function BusinessInformationCard({
  form,
  handleChange,
  handleSave,
  saving,
  saved,
  saveError,
}) {
  return (
    <div className="settings-card">
      <h3>Business Information</h3>
      <div className="settings-field">
        <label>Business Name</label>
        <input
          value={form.business_name}
          onChange={handleChange("business_name")}
          placeholder="Your Business"
        />
      </div>
      <div className="settings-field">
        <label>Business Type</label>
        <select
          value={form.business_type}
          onChange={handleChange("business_type")}
          style={{
            padding: "8px 10px",
            borderRadius: 6,
            border: "1px solid var(--border)",
            background: "var(--bg-secondary)",
            color: "var(--text-primary)",
          }}
        >
          <option value="">Select type...</option>
          <option value="restaurant">Restaurant / Food Service</option>
          <option value="home_services">
            Home Services (Plumbing, HVAC, etc.)
          </option>
          <option value="real_estate">Real Estate</option>
          <option value="health_wellness">Health & Wellness</option>
          <option value="legal">Legal Services</option>
          <option value="retail">Retail / E-commerce</option>
          <option value="automotive">Automotive</option>
          <option value="beauty">Beauty / Salon / Spa</option>
          <option value="fitness">Fitness / Gym</option>
          <option value="construction">Construction / Contractor</option>
          <option value="cleaning">Cleaning Services</option>
          <option value="landscaping">Landscaping / Lawn Care</option>
          <option value="professional">Professional Services</option>
          <option value="other">Other</option>
        </select>
      </div>
      <div className="settings-field">
        <label>City</label>
        <input
          value={form.city}
          onChange={handleChange("city")}
          placeholder="Your city"
        />
      </div>
      <div className="settings-field">
        <label>Owner Name</label>
        <input
          value={form.owner_name}
          onChange={handleChange("owner_name")}
          placeholder="Your name"
        />
      </div>
      <SaveButton
        saving={saving}
        saved={saved}
        onSave={handleSave}
        style={{ marginTop: "0.75rem" }}
      />
      {saveError && (
        <p style={{ color: "#ef4444", fontSize: "0.85rem", marginTop: 8 }}>
          {saveError}
        </p>
      )}
    </div>
  );
}

export function WebsiteScannerCard({
  form,
  handleChange,
  handleSave,
  handleScanWebsite,
  saving,
  saved,
  crawling,
  crawlStatus,
  businessSlug,
  businessPageEnabled,
  onNavigate,
}) {
  const canScan = form.website_url || (businessSlug && businessPageEnabled);

  return (
    <div className="settings-card">
      <h3>Website AI Scanner</h3>
      <p className="settings-card-desc">
        Add your website URL and we'll scan it to automatically train your AI
        assistant about your business.
      </p>
      <div className="settings-field">
        <label>Website URL</label>
        <input
          value={form.website_url}
          onChange={handleChange("website_url")}
          placeholder="https://yourbusiness.com"
        />
      </div>
      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          alignItems: "center",
          marginTop: "0.75rem",
        }}
      >
        <button
          className="btn-primary"
          onClick={handleScanWebsite}
          disabled={crawling || !canScan}
        >
          {crawling
            ? "Scanning..."
            : form.website_url
              ? "Scan Website"
              : "Scan Business Page"}
        </button>
        <SaveButton
          saving={saving}
          saved={saved}
          onSave={handleSave}
          label="Save URL"
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            color: "var(--text-primary)",
          }}
        />
      </div>
      {crawlStatus && crawlStatus.crawl_status !== "none" && (
        <CrawlStatusPanel crawlStatus={crawlStatus} />
      )}
      {!form.website_url &&
        (!crawlStatus ||
          crawlStatus.crawl_status === "none" ||
          crawlStatus.crawl_status === "failed") && (
          <NoWebsiteTrainingPanel onNavigate={onNavigate} />
        )}
    </div>
  );
}

function CrawlStatusPanel({ crawlStatus }) {
  return (
    <div
      style={{
        marginTop: "0.75rem",
        padding: "10px 14px",
        borderRadius: 8,
        fontSize: "0.85rem",
        background:
          crawlStatus.crawl_status === "completed"
            ? "rgba(34,197,94,0.08)"
            : crawlStatus.crawl_status === "failed"
              ? "rgba(239,68,68,0.08)"
              : "rgba(59,130,246,0.08)",
        border: `1px solid ${
          crawlStatus.crawl_status === "completed"
            ? "rgba(34,197,94,0.2)"
            : crawlStatus.crawl_status === "failed"
              ? "rgba(239,68,68,0.2)"
              : "rgba(59,130,246,0.2)"
        }`,
      }}
    >
      {crawlStatus.crawl_status === "completed" && (
        <span>
          AI knowledge base updated with content from {crawlStatus.pages_found}{" "}
          page{crawlStatus.pages_found !== 1 ? "s" : ""}. Your AI assistant now
          knows your business!
        </span>
      )}
      {crawlStatus.crawl_status === "crawling" && (
        <span>Scanning your website... This may take a minute.</span>
      )}
      {crawlStatus.crawl_status === "pending" && (
        <span>Scan queued. Starting shortly...</span>
      )}
      {crawlStatus.crawl_status === "failed" && (
        <span style={{ color: "var(--red, #ef4444)" }}>
          {crawlStatus.error_message ||
            "Scan failed. Please check the URL and try again."}
        </span>
      )}
      {crawlStatus.crawled_at && (
        <div
          style={{
            fontSize: "0.75rem",
            color: "var(--text-muted)",
            marginTop: 4,
          }}
        >
          Last scanned:{" "}
          {new Date(crawlStatus.crawled_at).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          })}
        </div>
      )}
    </div>
  );
}

function NoWebsiteTrainingPanel({ onNavigate }) {
  return (
    <div
      style={{
        marginTop: "0.75rem",
        padding: "10px 14px",
        borderRadius: 8,
        fontSize: "0.85rem",
        background: "rgba(250,204,21,0.08)",
        border: "1px solid rgba(250,204,21,0.2)",
      }}
    >
      <strong>No website?</strong> You can still train your AI assistant:
      <ul style={{ margin: "6px 0 0", paddingLeft: 18, lineHeight: 1.6 }}>
        <li>
          <button
            className="settings-link-btn"
            onClick={() => onNavigate?.("faq")}
            style={{ fontSize: "0.85rem", padding: 0, textDecoration: "underline" }}
          >
            Add FAQs manually
          </button>{" "}
          - teach your AI about your services, pricing, and policies.
        </li>
        <li>
          <button
            className="settings-link-btn"
            onClick={() => onNavigate?.("business-page")}
            style={{ fontSize: "0.85rem", padding: 0, textDecoration: "underline" }}
          >
            Set up your Business Page
          </button>{" "}
          - we'll auto-scan it to train your AI.
        </li>
      </ul>
    </div>
  );
}

export function AccountCard({ email, livePlan, onNavigate }) {
  return (
    <div className="settings-card">
      <h3>Account</h3>
      <div className="settings-field">
        <label>Email</label>
        <input value={email} disabled style={{ opacity: 0.6 }} />
        <span className="settings-field-hint">
          Contact support to change your email
        </span>
      </div>
      <div className="settings-field">
        <label>Plan</label>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <span className="settings-plan-badge">
            {livePlan.charAt(0).toUpperCase() + livePlan.slice(1)}
          </span>
          <button
            className="btn-secondary btn-sm"
            onClick={() => onNavigate?.("billing")}
          >
            Manage Plan
          </button>
        </div>
      </div>
    </div>
  );
}

export function BookingPageCard({ apiBase, businessSlug }) {
  if (!businessSlug) return null;

  const bookingUrl = `${apiBase}/api/v1/book/${businessSlug}`;
  const embedCode = `<iframe\n  src="${bookingUrl}"\n  width="100%"\n  height="600"\n  frameborder="0"\n  style="border:none;border-radius:12px;"\n></iframe>`;
  const copy = (value) => {
    navigator.clipboard.writeText(value).catch(() => {
      /* clipboard unavailable in insecure context */
    });
  };

  return (
    <div className="settings-card">
      <h3>Booking Page</h3>
      <p className="settings-card-desc">
        Share this link with customers so they can book appointments directly.
        Embed the widget on any website to let visitors book without leaving
        your page.
      </p>
      <div className="settings-field">
        <label>Booking URL</label>
        <div style={{ display: "flex", gap: 8, alignItems: "stretch" }}>
          <input
            readOnly
            value={bookingUrl}
            style={{
              flex: 1,
              fontFamily: "monospace",
              fontSize: "0.82rem",
              color: "var(--text-secondary)",
            }}
            onClick={(e) => e.target.select()}
          />
          <button
            className="btn-secondary"
            onClick={() => copy(bookingUrl)}
            style={{ whiteSpace: "nowrap", flexShrink: 0 }}
          >
            Copy Link
          </button>
        </div>
      </div>
      <div className="settings-field" style={{ marginTop: 12 }}>
        <label>Embed Code (iframe)</label>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
          <textarea
            readOnly
            rows={4}
            value={embedCode}
            style={{
              flex: 1,
              fontFamily: "monospace",
              fontSize: "0.78rem",
              color: "var(--text-secondary)",
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: "8px 10px",
              resize: "none",
              lineHeight: 1.5,
            }}
            onClick={(e) => e.target.select()}
          />
          <button
            className="btn-secondary"
            onClick={() => copy(embedCode)}
            style={{ whiteSpace: "nowrap", flexShrink: 0 }}
          >
            Copy Code
          </button>
        </div>
        <span className="settings-field-hint">
          Paste this into your website's HTML to embed the booking form.
        </span>
      </div>
    </div>
  );
}

export function QuickLinksCard({ onNavigate }) {
  return (
    <div className="settings-card">
      <h3>Quick Links</h3>
      <div className="settings-links">
        <button className="settings-link-btn" onClick={() => onNavigate?.("widget")}>
          Widget Settings
        </button>
        <button className="settings-link-btn" onClick={() => onNavigate?.("faq")}>
          FAQ Manager
        </button>
        <button
          className="settings-link-btn"
          onClick={() => onNavigate?.("availability")}
        >
          Calendar Availability
        </button>
      </div>
    </div>
  );
}

export function ClientPortalLoginCard({
  clientLoginEnabled,
  togglingClientLogin,
  businessSlug,
  handleToggleClientLogin,
}) {
  return (
    <div className="settings-card">
      <h3>Client Portal Login</h3>
      <p className="settings-card-desc">
        Allow your clients to create an account and log in to see their
        appointments, invoices, documents, and service history. Clients register
        through their portal link and can then access their account anytime.
      </p>
      <div
        className="settings-field"
        style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
      >
        <input
          type="checkbox"
          checked={clientLoginEnabled}
          onChange={handleToggleClientLogin}
          disabled={togglingClientLogin}
          style={{ width: 18, height: 18, cursor: "pointer" }}
        />
        <label style={{ cursor: "pointer" }} onClick={handleToggleClientLogin}>
          {togglingClientLogin
            ? "Updating..."
            : clientLoginEnabled
              ? "Client login enabled"
              : "Client login disabled"}
        </label>
      </div>
      {clientLoginEnabled && businessSlug && (
        <div
          style={{
            marginTop: 10,
            padding: "10px 14px",
            borderRadius: 8,
            fontSize: "0.83rem",
            background: "rgba(99,102,241,0.07)",
            border: "1px solid rgba(99,102,241,0.2)",
            color: "var(--text-secondary)",
          }}
        >
          Your clients can log in at:{" "}
          <strong style={{ color: "var(--text-primary)" }}>
            {window.location.origin}/client/login/{businessSlug}
          </strong>
        </div>
      )}
    </div>
  );
}

export function DangerZoneCard({ logout }) {
  return (
    <div className="settings-card danger-zone">
      <h3>Danger Zone</h3>
      <p className="settings-card-desc">
        Logging out will end your current session.
      </p>
      <button className="btn-danger" onClick={logout}>
        Log Out
      </button>
    </div>
  );
}
