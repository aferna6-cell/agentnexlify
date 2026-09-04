import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  connectWebsite,
  getWebsiteConnection,
  verifyWebsiteConnection,
  wordpressPluginDownloadUrl,
} from "../utils/api/websiteConnect";
import { fetchDashboard } from "../utils/api/dashboard";
import SkeletonLoader from "../components/SkeletonLoader";

const PLATFORMS = [
  { id: "wordpress", label: "WordPress" },
  { id: "wix", label: "Wix" },
  { id: "squarespace", label: "Squarespace" },
  { id: "godaddy", label: "GoDaddy" },
  { id: "custom", label: "Custom / other" },
];

const STATUS_META = {
  connected: {
    label: "AI receptionist is live",
    color: "var(--green)",
    bg: "var(--green-dim)",
  },
  needs_action: {
    label: "Install the widget, then verify",
    color: "var(--yellow)",
    bg: "var(--yellow-dim)",
  },
  failed: {
    label: "We could not verify this site yet",
    color: "var(--red)",
    bg: "var(--red-dim)",
  },
  not_started: {
    label: "Connect your website",
    color: "var(--text-secondary)",
    bg: "var(--hover-overlay)",
  },
};

function statusMeta(status) {
  return STATUS_META[status] || STATUS_META.not_started;
}

export default function WebsiteConnectPage() {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState("");
  const [connection, setConnection] = useState(null);
  const [status, setStatus] = useState("not_started");
  const [url, setUrl] = useState("");
  const [platform, setPlatform] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [copied, setCopied] = useState(false);

  const applyPayload = useCallback((payload) => {
    const row = payload?.connection || (payload?.id ? payload : null);
    setConnection(row);
    setStatus(row?.status || payload?.status || "not_started");
    if (row?.website_url) setUrl(row.website_url);
    if (row?.platform && row.platform !== "unknown") setPlatform(row.platform);
  }, []);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([
      getWebsiteConnection(token),
      user?.tenantId
        ? fetchDashboard(user.tenantId, token).catch(() => null)
        : Promise.resolve(null),
    ])
      .then(([connectPayload, dash]) => {
        if (cancelled) return;
        applyPayload(connectPayload);
        if (dash?.widget_api_key) setApiKey(dash.widget_api_key);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err.message || "Could not load connection status.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, user?.tenantId, applyPayload]);

  const apiBase =
    import.meta.env.VITE_API_BASE_URL ||
    "https://agentnexlify-production.up.railway.app";
  const embedCode = `<script async src="https://app.agentnexlify.com/widget/agentnexlify-widget.js" data-api-key="${apiKey || "your-api-key"}" data-api-base="${apiBase}"></script>`;

  async function handleConnect(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = await connectWebsite(token, {
        website_url: url,
        platform: platform || undefined,
      });
      applyPayload(payload);
    } catch (err) {
      setError(
        err.body?.detail || err.message || "Could not connect that website.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleVerify() {
    setVerifying(true);
    setError("");
    try {
      const payload = await verifyWebsiteConnection(token);
      applyPayload(payload);
    } catch (err) {
      setError(err.body?.detail || err.message || "Verification failed.");
    } finally {
      setVerifying(false);
    }
  }

  function handleCopy() {
    navigator.clipboard.writeText(embedCode).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  async function handlePluginDownload() {
    const resp = await fetch(wordpressPluginDownloadUrl(), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!resp.ok) {
      setError("Could not download the WordPress plugin.");
      return;
    }
    const blob = await resp.blob();
    const href = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = href;
    a.download = "agentnexlify.zip";
    a.click();
    URL.revokeObjectURL(href);
  }

  if (loading) return <SkeletonLoader />;

  const meta = statusMeta(status);
  const action = connection?.next_action;
  const live = status === "connected";
  const showSnippet =
    !live &&
    (action?.snippet_fallback ||
      ["wix", "squarespace", "godaddy", "custom"].includes(platform));

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Connect your website</h1>
        <p>
          Agent NexLiFy verifies the live page. Then the AI receptionist is
          live.
        </p>
      </div>

      <div
        className="settings-card"
        style={{
          borderColor: meta.color,
          background: meta.bg,
          marginBottom: 16,
        }}
        data-testid="connect-status"
      >
        <strong style={{ color: meta.color }}>{meta.label}</strong>
        {connection?.website_url && (
          <p className="settings-card-desc" style={{ marginBottom: 0 }}>
            {connection.website_url}
            {connection.platform && connection.platform !== "unknown"
              ? ` · ${connection.platform}`
              : ""}
          </p>
        )}
        {connection?.verification_detail && (
          <p className="settings-card-desc" style={{ marginBottom: 0 }}>
            {connection.verification_detail}
          </p>
        )}
      </div>

      <form className="settings-card" onSubmit={handleConnect}>
        <h3>Website URL</h3>
        <p className="settings-card-desc">
          We detect the platform when we can. You can override it. We never ask
          for your CMS password.
        </p>
        <label className="settings-label" htmlFor="website-url">
          Site address
        </label>
        <input
          id="website-url"
          type="url"
          required
          placeholder="https://yourbusiness.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          autoComplete="url"
        />

        <div className="platform-tabs" style={{ marginTop: 16 }}>
          {PLATFORMS.map((p) => (
            <button
              key={p.id}
              type="button"
              className={`platform-tab${platform === p.id ? " active" : ""}`}
              onClick={() => setPlatform(p.id)}
            >
              {p.label}
            </button>
          ))}
        </div>
        {connection?.detected_platform && (
          <p className="settings-card-desc">
            Detected: {connection.detected_platform}
            {connection.platform_override ? " (you overrode this)" : ""}
          </p>
        )}

        {error && <div className="onboarding-error">{error}</div>}

        <div
          style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}
        >
          <button className="btn-primary" type="submit" disabled={saving}>
            {saving
              ? "Checking…"
              : connection
                ? "Save website"
                : "Connect website"}
          </button>
          {connection && (
            <button
              className="btn-secondary"
              type="button"
              onClick={handleVerify}
              disabled={verifying}
            >
              {verifying ? "Verifying…" : "Verify now"}
            </button>
          )}
        </div>
      </form>

      {action && !live && (
        <div className="settings-card">
          <h3>{action.title}</h3>
          <ol className="settings-card-desc" style={{ paddingLeft: 18 }}>
            {(action.steps || []).map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          {platform === "wordpress" && (
            <button
              className="btn-primary"
              type="button"
              onClick={handlePluginDownload}
            >
              Download WordPress plugin
            </button>
          )}
        </div>
      )}

      {showSnippet && (
        <div className="settings-card">
          <h3>Embed snippet</h3>
          <p className="settings-card-desc">
            Fallback if the plugin or site builder block is not available.
          </p>
          <div className="embed-code-block">
            <code>{embedCode}</code>
          </div>
          <button className="btn-secondary" type="button" onClick={handleCopy}>
            {copied ? "Copied!" : "Copy snippet"}
          </button>
        </div>
      )}
    </div>
  );
}
