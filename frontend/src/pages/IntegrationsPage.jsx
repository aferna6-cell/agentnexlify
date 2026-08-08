import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import {
  fetchWebhooks,
  createWebhook,
  updateWebhook,
  toggleWebhook,
  deleteWebhook,
  fetchWebhookLogs,
  testWebhook,
} from "../utils/api/webhooks";
import {
  fetchGoogleCalendarStatus,
  startGoogleCalendarAuth,
  disconnectGoogleCalendar,
  fetchM365CalendarStatus,
  startM365CalendarAuth,
  disconnectM365Calendar,
  fetchHubSpotStatus,
  startHubSpotAuth,
  disconnectHubSpot,
  fetchFacebookStatus,
  getFacebookAuthUrl,
  disconnectFacebook,
  fetchInstagramStatus,
  getInstagramAuthUrl,
  disconnectInstagram,
  fetchBridgeConfig,
  toggleBridge,
  saveBridgeConfig,
  startGmailAuth,
  fetchGmailStatus,
  disconnectGmail,
} from "../utils/api/integrations";
import { fetchConnectorsStatus } from "../utils/api/connectors";
import SkeletonLoader from "../components/SkeletonLoader";

/* ── Inline SVG: Google Calendar logo ── */
function GoogleCalendarIcon({ size = 40 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect x="8" y="8" width="32" height="32" rx="4" fill="#fff" />
      <rect x="8" y="8" width="32" height="8" rx="4" fill="#4285F4" />
      <rect x="8" y="12" width="32" height="4" fill="#4285F4" />
      <rect x="8" y="16" width="4" height="20" fill="#0F9D58" />
      <rect x="8" y="36" width="4" height="4" fill="#0F9D58" />
      <rect x="36" y="16" width="4" height="20" fill="#F4B400" />
      <rect x="36" y="36" width="4" height="4" fill="#F4B400" />
      <rect x="12" y="36" width="24" height="4" fill="#DB4437" />
      <rect x="8" y="36" width="4" height="4" fill="#0F9D58" />
      <rect x="36" y="36" width="4" height="4" fill="#DB4437" />
      <rect x="12" y="20" width="24" height="1" fill="#E0E0E0" />
      <rect x="12" y="25" width="24" height="1" fill="#E0E0E0" />
      <rect x="12" y="30" width="24" height="1" fill="#E0E0E0" />
      <rect x="20" y="16" width="1" height="20" fill="#E0E0E0" />
      <rect x="28" y="16" width="1" height="20" fill="#E0E0E0" />
    </svg>
  );
}

/* ── Inline SVG: Facebook 'f' logo ── */
function FacebookIcon({ size = 40 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect width="48" height="48" rx="8" fill="#1877F2" />
      <path
        d="M33 24h-6v-4c0-1.1.9-2 2-2h4v-6h-4c-4.4 0-8 3.6-8 8v4h-4v6h4v14h6V30h4l2-6z"
        fill="#fff"
      />
    </svg>
  );
}

/* ── Inline SVG: Instagram glyph ── */
function InstagramIcon({ size = 40 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="igGrad" x1="0" y1="48" x2="48" y2="0">
          <stop offset="0%" stopColor="#FD5949" />
          <stop offset="50%" stopColor="#D6249F" />
          <stop offset="100%" stopColor="#285AEB" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="12" fill="url(#igGrad)" />
      <rect
        x="12"
        y="12"
        width="24"
        height="24"
        rx="7"
        fill="none"
        stroke="#fff"
        strokeWidth="3"
      />
      <circle
        cx="24"
        cy="24"
        r="6"
        fill="none"
        stroke="#fff"
        strokeWidth="3"
      />
      <circle cx="31.5" cy="16.5" r="2" fill="#fff" />
    </svg>
  );
}

/* ── Inline SVG: Gmail envelope ── */
function GmailIcon({ size = 40 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect
        x="4"
        y="10"
        width="40"
        height="28"
        rx="4"
        fill="#fff"
        stroke="#E0E0E0"
        strokeWidth="1"
      />
      <path
        d="M4 14l20 14 20-14"
        stroke="#EA4335"
        strokeWidth="3"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M4 12v22" stroke="#4285F4" strokeWidth="3" strokeLinecap="round" />
      <path d="M44 12v22" stroke="#34A853" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

/* ── Inline SVG: HubSpot sprocket logo ── */
function HubSpotIcon({ size = 40 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect width="48" height="48" rx="8" fill="#FF7A59" />
      <circle cx="32" cy="32" r="6" fill="#fff" />
      <circle cx="32" cy="32" r="3" fill="#FF7A59" />
      <circle
        cx="32"
        cy="14"
        r="3.5"
        fill="none"
        stroke="#fff"
        strokeWidth="2"
      />
      <rect x="31" y="17.5" width="2" height="9" fill="#fff" />
      <rect x="14" y="22" width="14" height="2" fill="#fff" />
      <rect x="14" y="22" width="2" height="14" fill="#fff" />
    </svg>
  );
}

/* ── Inline SVG: Microsoft 365 logo (four-square) ── */
function Microsoft365CalendarIcon({ size = 40 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect x="6" y="6" width="17" height="17" fill="#F25022" />
      <rect x="25" y="6" width="17" height="17" fill="#7FBA00" />
      <rect x="6" y="25" width="17" height="17" fill="#00A4EF" />
      <rect x="25" y="25" width="17" height="17" fill="#FFB900" />
    </svg>
  );
}

/* ── Facebook Messenger Section ── */
function FacebookMessengerSection({ token }) {
  const { user } = useAuth();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const [error, setError] = useState(null);

  const loadStatus = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const data = await fetchFacebookStatus(user.tenantId, token);
      setStatus(data);
    } catch (err) {
      console.error("Failed to load Facebook status", err);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleConnect = async () => {
    setConnecting(true);
    setError(null);
    try {
      const data = await getFacebookAuthUrl(user.tenantId, token);
      if (data.auth_url)
        window.open(data.auth_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError("Failed to start Facebook authorization.");
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirmDisconnect) {
      setConfirmDisconnect(true);
      return;
    }
    setDisconnecting(true);
    setError(null);
    try {
      await disconnectFacebook(user.tenantId, token);
      setConfirmDisconnect(false);
      await loadStatus();
    } catch (err) {
      setError("Failed to disconnect.");
    } finally {
      setDisconnecting(false);
    }
  };

  const connected = status?.connected;

  return (
    <div style={{ ...gcStyles.card, marginTop: "1rem" }}>
      <div style={gcStyles.cardTop}>
        <div style={gcStyles.iconWrap}>
          <FacebookIcon size={40} />
        </div>
        <div style={gcStyles.cardInfo}>
          <div style={gcStyles.cardTitle}>
            Facebook Messenger
            {connected && (
              <span style={gcStyles.connectedBadge}>Connected</span>
            )}
          </div>
          <div style={gcStyles.cardDesc}>
            Receive and reply to Facebook Messenger conversations from your
            shared inbox
          </div>
        </div>
      </div>
      {loading && (
        <div
          style={{
            marginTop: "0.75rem",
            color: "var(--text-muted)",
            fontSize: "0.8125rem",
          }}
        >
          Checking connection status...
        </div>
      )}
      {!loading && connected && status?.page_name && (
        <div style={gcStyles.details}>
          <div style={gcStyles.detailRow}>
            <span style={gcStyles.detailLabel}>Page</span>
            <span style={gcStyles.detailValue}>{status.page_name}</span>
          </div>
          {status.page_id && (
            <div style={{ ...gcStyles.detailRow, marginTop: "0.375rem" }}>
              <span style={gcStyles.detailLabel}>Page ID</span>
              <span
                style={{
                  ...gcStyles.detailValue,
                  color: "var(--text-muted)",
                  fontSize: "0.75rem",
                }}
              >
                {status.page_id}
              </span>
            </div>
          )}
        </div>
      )}
      {error && (
        <div className="error-banner" style={{ marginTop: "0.75rem" }}>
          {error}
        </div>
      )}
      <div style={gcStyles.cardActions}>
        {!loading && connected ? (
          <button
            className="btn-danger"
            onClick={handleDisconnect}
            disabled={disconnecting}
          >
            {disconnecting
              ? "Disconnecting..."
              : confirmDisconnect
                ? "Confirm disconnect?"
                : "Disconnect"}
          </button>
        ) : (
          !loading && (
            <button
              onClick={handleConnect}
              disabled={connecting}
              style={{
                background: connecting ? "var(--bg-secondary)" : "#1877F2",
                color: "#fff",
                border: "none",
                borderRadius: "var(--radius-sm)",
                padding: "0.5rem 1.125rem",
                fontWeight: 600,
                fontSize: "0.875rem",
                cursor: connecting ? "not-allowed" : "pointer",
                opacity: connecting ? 0.7 : 1,
                transition: "opacity 0.15s",
              }}
            >
              {connecting ? "Opening..." : "Connect Facebook"}
            </button>
          )
        )}
        {!loading && connected && confirmDisconnect && (
          <button
            className="btn-secondary"
            onClick={() => setConfirmDisconnect(false)}
            style={{ fontSize: "0.8125rem" }}
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

/* ── Instagram Business Section ── */
function InstagramSection({ token }) {
  const { user } = useAuth();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const [error, setError] = useState(null);

  const loadStatus = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const data = await fetchInstagramStatus(user.tenantId, token);
      setStatus(data);
    } catch (err) {
      console.error("Failed to load Instagram status", err);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleConnect = async () => {
    setConnecting(true);
    setError(null);
    try {
      const data = await getInstagramAuthUrl(user.tenantId, token);
      if (data.auth_url)
        window.open(data.auth_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      const msg =
        err?.message && err.message.includes("503")
          ? "Instagram connection isn't set up on this platform yet."
          : "Failed to start Instagram authorization.";
      setError(msg);
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirmDisconnect) {
      setConfirmDisconnect(true);
      return;
    }
    setDisconnecting(true);
    setError(null);
    try {
      await disconnectInstagram(user.tenantId, token);
      setConfirmDisconnect(false);
      await loadStatus();
    } catch (err) {
      setError("Failed to disconnect.");
    } finally {
      setDisconnecting(false);
    }
  };

  const connected = status?.connected;
  const platformConfigured = status?.platform_configured !== false;

  return (
    <div style={{ ...gcStyles.card, marginTop: "1rem" }}>
      <div style={gcStyles.cardTop}>
        <div style={gcStyles.iconWrap}>
          <InstagramIcon size={40} />
        </div>
        <div style={gcStyles.cardInfo}>
          <div style={gcStyles.cardTitle}>
            Instagram Business
            {connected && (
              <span style={gcStyles.connectedBadge}>Connected</span>
            )}
          </div>
          <div style={gcStyles.cardDesc}>
            Let your AI staff draft and publish Instagram posts. Requires an
            Instagram Business account linked to a Facebook Page.
          </div>
        </div>
      </div>
      {loading && (
        <div
          style={{
            marginTop: "0.75rem",
            color: "var(--text-muted)",
            fontSize: "0.8125rem",
          }}
        >
          Checking connection status...
        </div>
      )}
      {!loading && connected && (
        <div style={gcStyles.details}>
          {status?.instagram_username && (
            <div style={gcStyles.detailRow}>
              <span style={gcStyles.detailLabel}>Account</span>
              <span style={gcStyles.detailValue}>
                @{status.instagram_username}
              </span>
            </div>
          )}
          {status?.page_name && (
            <div style={{ ...gcStyles.detailRow, marginTop: "0.375rem" }}>
              <span style={gcStyles.detailLabel}>Page</span>
              <span style={gcStyles.detailValue}>{status.page_name}</span>
            </div>
          )}
        </div>
      )}
      {!loading && !connected && !platformConfigured && (
        <div
          style={{
            marginTop: "0.75rem",
            color: "var(--text-muted)",
            fontSize: "0.8125rem",
          }}
        >
          Instagram connection isn't set up on this platform yet.
        </div>
      )}
      {error && (
        <div className="error-banner" style={{ marginTop: "0.75rem" }}>
          {error}
        </div>
      )}
      <div style={gcStyles.cardActions}>
        {!loading && connected ? (
          <button
            className="btn-danger"
            onClick={handleDisconnect}
            disabled={disconnecting}
          >
            {disconnecting
              ? "Disconnecting..."
              : confirmDisconnect
                ? "Confirm disconnect?"
                : "Disconnect"}
          </button>
        ) : (
          !loading && (
            <button
              onClick={handleConnect}
              disabled={connecting || !platformConfigured}
              style={{
                background:
                  connecting || !platformConfigured
                    ? "var(--bg-secondary)"
                    : "#D6249F",
                color: "#fff",
                border: "none",
                borderRadius: "var(--radius-sm)",
                padding: "0.5rem 1.125rem",
                fontWeight: 600,
                fontSize: "0.875rem",
                cursor:
                  connecting || !platformConfigured
                    ? "not-allowed"
                    : "pointer",
                opacity: connecting || !platformConfigured ? 0.7 : 1,
                transition: "opacity 0.15s",
              }}
            >
              {connecting ? "Opening..." : "Connect Instagram"}
            </button>
          )
        )}
        {!loading && connected && confirmDisconnect && (
          <button
            className="btn-secondary"
            onClick={() => setConfirmDisconnect(false)}
            style={{ fontSize: "0.8125rem" }}
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

const ALL_EVENTS = [
  {
    value: "lead.created",
    label: "Lead Created",
    desc: "When a new lead is captured",
  },
  {
    value: "lead.updated",
    label: "Lead Updated",
    desc: "When lead stage/score changes",
  },
  {
    value: "appointment.booked",
    label: "Appointment Booked",
    desc: "When an appointment is created",
  },
  {
    value: "appointment.cancelled",
    label: "Appointment Cancelled",
    desc: "When an appointment is cancelled",
  },
  {
    value: "conversation.started",
    label: "Conversation Started",
    desc: "New chat session begins",
  },
  {
    value: "conversation.message",
    label: "Conversation Message",
    desc: "Each new chat message",
  },
  {
    value: "automation.email_sent",
    label: "Automation Email Sent",
    desc: "When automation sends an email",
  },
];

const TEMPLATES = [
  {
    title: "Send new leads to Google Sheets",
    desc: "Automatically add each captured lead as a new row in a Google Sheet.",
  },
  {
    title: "Create Slack notification on new lead",
    desc: "Post a message to a Slack channel when a new lead comes in.",
  },
  {
    title: "Add leads to Mailchimp",
    desc: "Subscribe new leads to your Mailchimp audience automatically.",
  },
  {
    title: "Create Trello card for new appointment",
    desc: "Add a card to your Trello board when a new appointment is booked.",
  },
];

function StatusBadge({ active, failureCount }) {
  if (!active && failureCount >= 10) {
    return <span className="wh-badge wh-badge-error">Auto-disabled</span>;
  }
  if (!active) {
    return <span className="wh-badge wh-badge-inactive">Inactive</span>;
  }
  return <span className="wh-badge wh-badge-active">Active</span>;
}

function truncateUrl(url, max = 50) {
  if (!url) return "";
  return url.length > max ? url.slice(0, max) + "..." : url;
}

function formatTime(ts) {
  if (!ts) return "Never";
  const d = new Date(ts);
  return (
    d.toLocaleDateString() +
    " " +
    d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  );
}

/* ── Google Calendar Section ── */
function GoogleCalendarSection({ token }) {
  const { user } = useAuth();
  const [status, setStatus] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [error, setError] = useState(null);

  const loadStatus = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const data = await fetchGoogleCalendarStatus(user.tenantId, token);
      setStatus(data);
    } catch (err) {
      console.error("Failed to load Google status", err);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const data = await startGoogleCalendarAuth(user.tenantId, token);
      if (data.auth_url) window.location.href = data.auth_url;
    } catch (err) {
      setError("Failed to start Google authorization.");
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    setDisconnecting(true);
    try {
      await disconnectGoogleCalendar(user.tenantId, token);
      await loadStatus();
    } catch (err) {
      setError("Failed to disconnect.");
    } finally {
      setDisconnecting(false);
    }
  };

  const connected = status?.connected;

  return (
    <div style={gcStyles.card}>
      <div style={gcStyles.cardTop}>
        <div style={gcStyles.iconWrap}>
          <GoogleCalendarIcon size={40} />
        </div>
        <div style={gcStyles.cardInfo}>
          <div style={gcStyles.cardTitle}>
            Google Calendar
            {connected && (
              <span style={gcStyles.connectedBadge}>Connected</span>
            )}
          </div>
          <div style={gcStyles.cardDesc}>
            Sync appointments to your Google Calendar and check availability
            against existing events
          </div>
        </div>
      </div>
      {connected && status?.email && (
        <div style={gcStyles.details}>
          <div style={gcStyles.detailRow}>
            <span style={gcStyles.detailLabel}>Account</span>
            <span style={gcStyles.detailValue}>{status.email}</span>
          </div>
        </div>
      )}
      {error && (
        <div className="error-banner" style={{ marginTop: "0.75rem" }}>
          {error}
        </div>
      )}
      <div style={gcStyles.cardActions}>
        {connected ? (
          <button
            className="btn-danger"
            onClick={handleDisconnect}
            disabled={disconnecting}
          >
            {disconnecting ? "Disconnecting..." : "Disconnect"}
          </button>
        ) : (
          <button
            className="btn-primary"
            onClick={handleConnect}
            disabled={connecting}
          >
            {connecting ? "Connecting..." : "Connect"}
          </button>
        )}
      </div>
    </div>
  );
}

/* ── Microsoft 365 Calendar Section ── */
function M365CalendarSection({ token }) {
  const { user } = useAuth();
  const [status, setStatus] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [error, setError] = useState(null);

  const loadStatus = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const data = await fetchM365CalendarStatus(user.tenantId, token);
      setStatus(data);
    } catch (err) {
      console.error("Failed to load Microsoft 365 status", err);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const data = await startM365CalendarAuth(user.tenantId, token);
      if (data.auth_url) window.location.href = data.auth_url;
    } catch (err) {
      setError("Failed to start Microsoft 365 authorization.");
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    setDisconnecting(true);
    try {
      await disconnectM365Calendar(user.tenantId, token);
      await loadStatus();
    } catch (err) {
      setError("Failed to disconnect.");
    } finally {
      setDisconnecting(false);
    }
  };

  const connected = status?.connected;

  return (
    <div style={{ ...gcStyles.card, marginTop: "1rem" }}>
      <div style={gcStyles.cardTop}>
        <div style={gcStyles.iconWrap}>
          <Microsoft365CalendarIcon size={40} />
        </div>
        <div style={gcStyles.cardInfo}>
          <div style={gcStyles.cardTitle}>
            Microsoft 365 Calendar
            {connected && (
              <span style={gcStyles.connectedBadge}>Connected</span>
            )}
          </div>
          <div style={gcStyles.cardDesc}>
            Sync appointments to your Outlook calendar and send email through
            Microsoft Graph
          </div>
        </div>
      </div>
      {connected && status?.email && (
        <div style={gcStyles.details}>
          <div style={gcStyles.detailRow}>
            <span style={gcStyles.detailLabel}>Account</span>
            <span style={gcStyles.detailValue}>{status.email}</span>
          </div>
          {status.calendar_name && (
            <div style={{ ...gcStyles.detailRow, marginTop: "0.375rem" }}>
              <span style={gcStyles.detailLabel}>Calendar</span>
              <span style={gcStyles.detailValue}>{status.calendar_name}</span>
            </div>
          )}
        </div>
      )}
      {error && (
        <div className="error-banner" style={{ marginTop: "0.75rem" }}>
          {error}
        </div>
      )}
      <div style={gcStyles.cardActions}>
        {connected ? (
          <button
            className="btn-danger"
            onClick={handleDisconnect}
            disabled={disconnecting}
          >
            {disconnecting ? "Disconnecting..." : "Disconnect"}
          </button>
        ) : (
          <button
            className="btn-primary"
            onClick={handleConnect}
            disabled={connecting}
          >
            {connecting ? "Connecting..." : "Connect"}
          </button>
        )}
      </div>
    </div>
  );
}

/* ── Gmail Section ── */
function GmailSection({ token }) {
  const { user } = useAuth();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const [error, setError] = useState(null);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchGmailStatus(user?.tenantId, token);
      setStatus(data);
    } catch (err) {
      console.error("Failed to load Gmail status", err);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleConnect = async () => {
    setConnecting(true);
    setError(null);
    try {
      const data = await startGmailAuth(user?.tenantId, token);
      if (data.auth_url)
        window.open(data.auth_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError("Failed to start Gmail authorization.");
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirmDisconnect) {
      setConfirmDisconnect(true);
      return;
    }
    setDisconnecting(true);
    setError(null);
    try {
      await disconnectGmail(user?.tenantId, token);
      setConfirmDisconnect(false);
      await loadStatus();
    } catch (err) {
      setError("Failed to disconnect.");
    } finally {
      setDisconnecting(false);
    }
  };

  const connected = status?.connected;

  return (
    <div style={{ ...gcStyles.card, marginTop: "1rem" }}>
      <div style={gcStyles.cardTop}>
        <div style={gcStyles.iconWrap}>
          <GmailIcon size={40} />
        </div>
        <div style={gcStyles.cardInfo}>
          <div style={gcStyles.cardTitle}>
            Gmail
            {connected && (
              <span style={gcStyles.connectedBadge}>Connected</span>
            )}
          </div>
          <div style={gcStyles.cardDesc}>
            Let the Agent OS read and send email through your Gmail account
            for outreach and inbound replies
          </div>
        </div>
      </div>
      {loading && (
        <div
          style={{
            marginTop: "0.75rem",
            color: "var(--text-muted)",
            fontSize: "0.8125rem",
          }}
        >
          Checking connection status...
        </div>
      )}
      {!loading && connected && status?.email_address && (
        <div style={gcStyles.details}>
          <div style={gcStyles.detailRow}>
            <span style={gcStyles.detailLabel}>Account</span>
            <span style={gcStyles.detailValue}>{status.email_address}</span>
          </div>
        </div>
      )}
      {error && (
        <div className="error-banner" style={{ marginTop: "0.75rem" }}>
          {error}
        </div>
      )}
      <div style={gcStyles.cardActions}>
        {!loading && connected ? (
          <button
            className="btn-danger"
            onClick={handleDisconnect}
            disabled={disconnecting}
          >
            {disconnecting
              ? "Disconnecting..."
              : confirmDisconnect
                ? "Confirm disconnect?"
                : "Disconnect"}
          </button>
        ) : (
          !loading && (
            <button
              className="btn-primary"
              onClick={handleConnect}
              disabled={connecting}
            >
              {connecting ? "Opening..." : "Connect Gmail"}
            </button>
          )
        )}
        {!loading && connected && confirmDisconnect && (
          <button
            className="btn-secondary"
            onClick={() => setConfirmDisconnect(false)}
            style={{ fontSize: "0.8125rem" }}
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

/* ── Connectors status strip - registry-driven, additive to the hardcoded
   cards above. Only renders once data loads and the registry isn't empty,
   so it never adds a blank card to the page. ── */
function ConnectorsStrip({ token }) {
  const [connectors, setConnectors] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchConnectorsStatus(token)
      .then((res) => {
        if (cancelled) return;
        const list = Array.isArray(res) ? res : res?.connectors || [];
        setConnectors(list);
      })
      .catch((err) => console.error("Failed to load connector registry", err))
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (loading || connectors.length === 0) return null;

  return (
    <div style={{ ...gcStyles.card, marginBottom: "1rem" }}>
      <div
        style={{
          fontSize: "0.8125rem",
          fontWeight: 600,
          color: "var(--text-primary)",
          marginBottom: "0.75rem",
        }}
      >
        All Connectors
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {connectors.map((c) => (
          <div
            key={c.key}
            onClick={() => {
              if (c.connected || !c.connect_path) return;
              if (/^https?:\/\//.test(c.connect_path)) {
                window.open(c.connect_path, "_blank", "noopener,noreferrer");
              } else {
                window.location.href = c.connect_path;
              }
            }}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "5px 12px",
              borderRadius: 16,
              border: "1px solid var(--border)",
              background: "var(--bg-secondary)",
              fontSize: "0.78rem",
              color: "var(--text-secondary)",
              cursor: c.connected ? "default" : "pointer",
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: c.connected ? "var(--green)" : "var(--text-muted)",
                flexShrink: 0,
              }}
            />
            {c.label || c.key}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── HubSpot Section ── */
function HubSpotSection({ token }) {
  const { user } = useAuth();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const [error, setError] = useState(null);

  const loadStatus = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const data = await fetchHubSpotStatus(user.tenantId, token);
      setStatus(data);
    } catch (err) {
      console.error("Failed to load HubSpot status", err);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleConnect = async () => {
    setConnecting(true);
    setError(null);
    try {
      const data = await startHubSpotAuth(user.tenantId, token);
      if (data.auth_url) window.location.href = data.auth_url;
    } catch (err) {
      const msg =
        err?.message && err.message.includes("503")
          ? "HubSpot OAuth not configured on this server."
          : "Failed to start HubSpot authorization.";
      setError(msg);
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirmDisconnect) {
      setConfirmDisconnect(true);
      return;
    }
    setDisconnecting(true);
    setError(null);
    try {
      await disconnectHubSpot(user.tenantId, token);
      setConfirmDisconnect(false);
      await loadStatus();
    } catch (err) {
      setError("Failed to disconnect.");
    } finally {
      setDisconnecting(false);
    }
  };

  const connected = status?.connected;

  return (
    <div style={{ ...gcStyles.card, marginTop: "1rem" }}>
      <div style={gcStyles.cardTop}>
        <div style={gcStyles.iconWrap}>
          <HubSpotIcon size={40} />
        </div>
        <div style={gcStyles.cardInfo}>
          <div style={gcStyles.cardTitle}>
            HubSpot CRM
            {connected && (
              <span style={gcStyles.connectedBadge}>Connected</span>
            )}
          </div>
          <div style={gcStyles.cardDesc}>
            Push leads captured by the Agent OS into your HubSpot contacts.
            Internal CRM continues to capture every lead either way.
          </div>
        </div>
      </div>
      {loading && (
        <div
          style={{
            marginTop: "0.75rem",
            color: "var(--text-muted)",
            fontSize: "0.8125rem",
          }}
        >
          Checking connection status...
        </div>
      )}
      {!loading && connected && (
        <div style={gcStyles.details}>
          {status?.portal_id && (
            <div style={gcStyles.detailRow}>
              <span style={gcStyles.detailLabel}>Portal</span>
              <span style={gcStyles.detailValue}>{status.portal_id}</span>
            </div>
          )}
          {status?.hub_domain && (
            <div style={{ ...gcStyles.detailRow, marginTop: "0.375rem" }}>
              <span style={gcStyles.detailLabel}>Domain</span>
              <span style={gcStyles.detailValue}>{status.hub_domain}</span>
            </div>
          )}
          {status?.user && (
            <div style={{ ...gcStyles.detailRow, marginTop: "0.375rem" }}>
              <span style={gcStyles.detailLabel}>User</span>
              <span style={gcStyles.detailValue}>{status.user}</span>
            </div>
          )}
        </div>
      )}
      {error && (
        <div className="error-banner" style={{ marginTop: "0.75rem" }}>
          {error}
        </div>
      )}
      <div style={gcStyles.cardActions}>
        {!loading && connected ? (
          <button
            className="btn-danger"
            onClick={handleDisconnect}
            disabled={disconnecting}
          >
            {disconnecting
              ? "Disconnecting..."
              : confirmDisconnect
                ? "Confirm disconnect?"
                : "Disconnect"}
          </button>
        ) : (
          !loading && (
            <button
              className="btn-primary"
              onClick={handleConnect}
              disabled={connecting}
            >
              {connecting ? "Connecting..." : "Connect HubSpot"}
            </button>
          )
        )}
        {!loading && connected && confirmDisconnect && (
          <button
            className="btn-secondary"
            onClick={() => setConfirmDisconnect(false)}
            style={{ fontSize: "0.8125rem" }}
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

/* ── Agent OS Inbound Bridges Section ── */
const BRIDGE_SOURCES = [
  {
    key: "widget_enabled",
    source: "widget",
    label: "Widget chat",
    desc: "Embedded chat on tenant sites. Default on.",
  },
  {
    key: "email_enabled",
    source: "email",
    label: "Email inbound",
    desc: "Postmark or Mailgun webhook posts inbound replies.",
  },
  {
    key: "sms_enabled",
    source: "sms",
    label: "SMS inbound",
    desc: "Twilio webhook posts inbound texts.",
  },
  {
    key: "facebook_enabled",
    source: "facebook",
    label: "Facebook DM inbound",
    desc: "Messenger webhook posts inbound DMs.",
  },
];

function InboundBridgesSection({ token }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [savingToggle, setSavingToggle] = useState(null);
  const [savingConfig, setSavingConfig] = useState(false);
  const [error, setError] = useState(null);
  const [emailAddress, setEmailAddress] = useState("");
  const [emailProvider, setEmailProvider] = useState("");

  const loadConfig = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchBridgeConfig(token);
      setConfig(data);
      setEmailAddress(data?.email_inbound_address || "");
      setEmailProvider(data?.email_provider || "");
    } catch (err) {
      console.error("Failed to load bridge config", err);
      setError("Failed to load bridge config.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const handleToggle = async (source, key) => {
    if (!config) return;
    const next = !(config[key] ?? true);
    setSavingToggle(source);
    setError(null);
    try {
      const updated = await toggleBridge(source, next, token);
      setConfig(updated);
    } catch (err) {
      console.error("Toggle failed", err);
      setError(`Failed to toggle ${source}.`);
    } finally {
      setSavingToggle(null);
    }
  };

  const dirty =
    (config?.email_inbound_address || "") !==
      emailAddress.trim().toLowerCase() ||
    (config?.email_provider || "") !== emailProvider;

  const handleSaveEmailConfig = async () => {
    setSavingConfig(true);
    setError(null);
    try {
      const updates = {};
      const normalizedAddr = emailAddress.trim().toLowerCase();
      if ((config?.email_inbound_address || "") !== normalizedAddr) {
        updates.email_inbound_address = normalizedAddr || null;
      }
      if ((config?.email_provider || "") !== emailProvider) {
        updates.email_provider = emailProvider || null;
      }
      if (Object.keys(updates).length === 0) {
        setSavingConfig(false);
        return;
      }
      const updated = await saveBridgeConfig(updates, token);
      setConfig(updated);
      setEmailAddress(updated?.email_inbound_address || "");
      setEmailProvider(updated?.email_provider || "");
    } catch (err) {
      console.error("Save failed", err);
      const msg =
        err?.message && err.message.includes("400")
          ? "Invalid email provider. Use postmark or mailgun."
          : "Failed to save email bridge config.";
      setError(msg);
    } finally {
      setSavingConfig(false);
    }
  };

  return (
    <div style={{ ...gcStyles.card, marginBottom: "1rem" }}>
      <div style={gcStyles.cardTop}>
        <div style={gcStyles.cardInfo}>
          <div style={gcStyles.cardTitle}>Agent OS Inbound Bridges</div>
          <div style={gcStyles.cardDesc}>
            Per-source switches and email routing for the unified Agent OS
            inbound pipeline. Disable a source to stop the OS reading messages
            from that channel without removing the integration itself.
          </div>
        </div>
      </div>

      {loading && (
        <div
          style={{
            marginTop: "0.75rem",
            color: "var(--text-muted)",
            fontSize: "0.8125rem",
          }}
        >
          Loading bridge config...
        </div>
      )}

      {!loading && config && (
        <>
          <div style={{ marginTop: "1.25rem" }}>
            {BRIDGE_SOURCES.map(({ key, source, label, desc }) => {
              const enabled = config[key] ?? true;
              const isSaving = savingToggle === source;
              return (
                <div
                  key={source}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "0.75rem 0",
                    borderBottom: "1px solid var(--border)",
                    gap: "1rem",
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: "0.875rem",
                        fontWeight: 600,
                        color: "var(--text-primary)",
                        marginBottom: "0.125rem",
                      }}
                    >
                      {label}
                    </div>
                    <div
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--text-muted)",
                      }}
                    >
                      {desc}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleToggle(source, key)}
                    disabled={isSaving}
                    style={{
                      flexShrink: 0,
                      minWidth: 92,
                      padding: "0.375rem 0.875rem",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--border)",
                      cursor: isSaving ? "default" : "pointer",
                      background: enabled
                        ? "var(--green-dim)"
                        : "var(--bg-secondary)",
                      color: enabled ? "var(--green)" : "var(--text-muted)",
                    }}
                  >
                    {isSaving ? "..." : enabled ? "Enabled" : "Disabled"}
                  </button>
                </div>
              );
            })}
          </div>

          <div style={{ ...gcStyles.details, marginTop: "1.25rem" }}>
            <div
              style={{
                fontSize: "0.8125rem",
                fontWeight: 600,
                color: "var(--text-primary)",
                marginBottom: "0.75rem",
              }}
            >
              Email inbound routing
            </div>
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                marginBottom: "0.875rem",
                lineHeight: 1.5,
              }}
            >
              Inbound address must match the Reply-To we send on outbound mail.
              Provider sets which webhook handler verifies the signature.
            </div>

            <div style={{ marginBottom: "0.75rem" }}>
              <label
                style={{
                  display: "block",
                  fontSize: "0.75rem",
                  color: "var(--text-muted)",
                  marginBottom: "0.25rem",
                }}
              >
                Inbound address
              </label>
              <input
                type="email"
                value={emailAddress}
                onChange={(e) => setEmailAddress(e.target.value)}
                placeholder="replies@tenant.example.com"
                style={{
                  width: "100%",
                  padding: "0.5rem 0.75rem",
                  fontSize: "0.8125rem",
                  background: "var(--bg-primary)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text-primary)",
                }}
              />
            </div>

            <div style={{ marginBottom: "0.75rem" }}>
              <label
                style={{
                  display: "block",
                  fontSize: "0.75rem",
                  color: "var(--text-muted)",
                  marginBottom: "0.25rem",
                }}
              >
                Provider
              </label>
              <select
                value={emailProvider}
                onChange={(e) => setEmailProvider(e.target.value)}
                style={{
                  width: "100%",
                  padding: "0.5rem 0.75rem",
                  fontSize: "0.8125rem",
                  background: "var(--bg-primary)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text-primary)",
                }}
              >
                <option value="">- Not set -</option>
                <option value="postmark">Postmark</option>
                <option value="mailgun">Mailgun</option>
              </select>
            </div>

            <button
              type="button"
              className="btn-primary"
              onClick={handleSaveEmailConfig}
              disabled={!dirty || savingConfig}
              style={{ fontSize: "0.8125rem" }}
            >
              {savingConfig ? "Saving..." : "Save email config"}
            </button>
          </div>
        </>
      )}

      {error && (
        <div className="error-banner" style={{ marginTop: "0.75rem" }}>
          {error}
        </div>
      )}
    </div>
  );
}

/* ── Main Page ── */
export default function IntegrationsPage({ onNavigate }) {
  const { user, token } = useAuth();
  const [webhooks, setWebhooks] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [selectedLog, setSelectedLog] = useState(null);
  const [activeTab, setActiveTab] = useState("services");
  const [form, setForm] = useState({
    name: "",
    url: "",
    events: [],
    secret: "",
  });
  const [toast, setToast] = useState(null);
  const [testingId, setTestingId] = useState(null);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("google") === "connected") {
      setToast("Google Calendar connected successfully!");
      const url = new URL(window.location);
      url.searchParams.delete("google");
      window.history.replaceState({}, "", url.pathname + url.search);
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
    if (params.get("m365") === "connected") {
      setToast("Microsoft 365 Calendar connected successfully!");
      const url = new URL(window.location);
      url.searchParams.delete("m365");
      window.history.replaceState({}, "", url.pathname + url.search);
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
    if (params.get("instagram_connected") === "true") {
      setToast("Instagram connected successfully!");
      const url = new URL(window.location);
      url.searchParams.delete("instagram_connected");
      window.history.replaceState({}, "", url.pathname + url.search);
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
    if (params.get("hubspot") === "connected") {
      setToast("HubSpot connected successfully!");
      const url = new URL(window.location);
      url.searchParams.delete("hubspot");
      window.history.replaceState({}, "", url.pathname + url.search);
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
  }, []);

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const [wh, lg] = await Promise.all([
        fetchWebhooks(user.tenantId, token),
        fetchWebhookLogs(user.tenantId, token),
      ]);
      setWebhooks(wh || []);
      setLogs(lg || []);
    } catch (err) {
      console.error("Failed to load webhooks", err);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    load();
  }, [load]);

  const handleToggleEvent = (eventValue) => {
    setForm((f) => ({
      ...f,
      events: f.events.includes(eventValue)
        ? f.events.filter((e) => e !== eventValue)
        : [...f.events, eventValue],
    }));
  };

  const handleSave = async () => {
    if (!form.name.trim() || !form.url.trim() || form.events.length === 0)
      return;
    setSaving(true);
    try {
      if (editId) {
        const updated = await updateWebhook(user.tenantId, token, editId, form);
        setWebhooks((prev) => prev.map((w) => (w.id === editId ? updated : w)));
      } else {
        const created = await createWebhook(user.tenantId, token, form);
        setWebhooks((prev) => [created, ...prev]);
      }
      resetForm();
    } catch (err) {
      console.error("Failed to save webhook", err);
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (webhook) => {
    setForm({
      name: webhook.name,
      url: webhook.url,
      events: webhook.events || [],
      secret: webhook.secret || "",
    });
    setEditId(webhook.id);
    setShowForm(true);
    setActiveTab("webhooks");
  };

  const handleToggle = async (id) => {
    try {
      const result = await toggleWebhook(user.tenantId, token, id);
      setWebhooks((prev) =>
        prev.map((w) =>
          w.id === id
            ? {
                ...w,
                is_active: result.is_active,
                failure_count: result.is_active ? 0 : w.failure_count,
              }
            : w,
        ),
      );
    } catch (err) {
      console.error("Failed to toggle webhook", err);
    }
  };

  const handleDelete = async (id) => {
    if (deleteConfirm !== id) {
      setDeleteConfirm(id);
      return;
    }
    try {
      await deleteWebhook(user.tenantId, token, id);
      setWebhooks((prev) => prev.filter((w) => w.id !== id));
      setDeleteConfirm(null);
    } catch (err) {
      console.error("Failed to delete webhook", err);
    }
  };

  const resetForm = () => {
    setForm({ name: "", url: "", events: [], secret: "" });
    setEditId(null);
    setShowForm(false);
  };

  const handleTest = async (webhookId) => {
    setTestingId(webhookId);
    setTestResult(null);
    try {
      const res = await testWebhook(user.tenantId, token, webhookId);
      setTestResult({
        webhookId,
        success: res.success,
        statusCode: res.status_code,
        event: res.event,
      });
    } catch (err) {
      setTestResult({
        webhookId,
        success: false,
        statusCode: null,
        event: null,
      });
    } finally {
      setTestingId(null);
    }
  };

  if (loading) return <SkeletonLoader />;

  return (
    <div className="fade-in">
      {toast && (
        <div style={gcStyles.toast}>
          <span style={gcStyles.toastIcon}>&#10003;</span>
          {toast}
          <button
            onClick={() => setToast(null)}
            style={gcStyles.toastClose}
            aria-label="Dismiss"
          >
            &times;
          </button>
        </div>
      )}

      <div className="page-header">
        <h1>Integrations</h1>
        <p>Connect AgentNexLiFy to third-party services and webhooks</p>
      </div>

      {/* Tabs */}
      <div className="wh-tabs">
        <button
          className={`wh-tab${activeTab === "services" ? " wh-tab-active" : ""}`}
          onClick={() => setActiveTab("services")}
        >
          Connected Services
        </button>
        <button
          className={`wh-tab${activeTab === "webhooks" ? " wh-tab-active" : ""}`}
          onClick={() => setActiveTab("webhooks")}
        >
          Webhooks
        </button>
        <button
          className={`wh-tab${activeTab === "logs" ? " wh-tab-active" : ""}`}
          onClick={() => setActiveTab("logs")}
        >
          Recent Deliveries
        </button>
        <button
          className={`wh-tab${activeTab === "templates" ? " wh-tab-active" : ""}`}
          onClick={() => setActiveTab("templates")}
        >
          Integration Guides
        </button>
      </div>

      {/* Services Tab */}
      {activeTab === "services" && (
        <>
          <ConnectorsStrip token={token} />
          <InboundBridgesSection token={token} />
          <GoogleCalendarSection token={token} />
          <GmailSection token={token} />
          <FacebookMessengerSection token={token} />
          <InstagramSection token={token} />
          {/* M365CalendarSection + HubSpotSection deferred 2026-08-01 (owner
              decision) - components kept below; re-add here when needed. */}
        </>
      )}

      {/* Webhooks Tab */}
      {activeTab === "webhooks" && (
        <>
          <div style={{ marginBottom: "1rem" }}>
            <button
              className="btn-primary"
              onClick={() => (showForm ? resetForm() : setShowForm(true))}
            >
              {showForm ? "Cancel" : "+ Add Webhook"}
            </button>
          </div>

          {showForm && (
            <div className="settings-card" style={{ marginBottom: "1.5rem" }}>
              <h3>{editId ? "Edit Webhook" : "New Webhook"}</h3>
              <div className="settings-field">
                <label>Name</label>
                <input
                  value={form.name}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, name: e.target.value }))
                  }
                  placeholder="My Zapier Integration"
                />
              </div>
              <div className="settings-field">
                <label>Webhook URL</label>
                <input
                  value={form.url}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, url: e.target.value }))
                  }
                  placeholder="https://hooks.zapier.com/hooks/catch/..."
                />
              </div>
              <div className="settings-field">
                <label>Events</label>
                <div className="wh-events-grid">
                  {ALL_EVENTS.map((evt) => (
                    <label key={evt.value} className="wh-event-checkbox">
                      <input
                        type="checkbox"
                        checked={form.events.includes(evt.value)}
                        onChange={() => handleToggleEvent(evt.value)}
                      />
                      <div>
                        <div className="wh-event-label">{evt.label}</div>
                        <div className="wh-event-desc">{evt.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
              <div className="settings-field">
                <label>Secret (optional)</label>
                <input
                  value={form.secret}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, secret: e.target.value }))
                  }
                  placeholder="Auto-generated if left blank"
                  type="password"
                />
                <p
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-muted)",
                    marginTop: "0.25rem",
                  }}
                >
                  Used to sign payloads with HMAC-SHA256 (X-Webhook-Signature
                  header)
                </p>
              </div>
              <button
                className="btn-primary"
                onClick={handleSave}
                disabled={
                  saving ||
                  !form.name.trim() ||
                  !form.url.trim() ||
                  form.events.length === 0
                }
              >
                {saving
                  ? "Saving..."
                  : editId
                    ? "Update Webhook"
                    : "Create Webhook"}
              </button>
            </div>
          )}

          {webhooks.length === 0 && !showForm ? (
            <div className="empty-card">
              <p>
                No webhooks configured yet. Add a webhook to send data to
                Zapier, Make, or n8n when events happen.
              </p>
            </div>
          ) : (
            <div className="wh-list">
              {webhooks.map((wh) => (
                <div key={wh.id} className="wh-item">
                  <div className="wh-item-header">
                    <div className="wh-item-title">
                      <strong>{wh.name}</strong>
                      <StatusBadge
                        active={wh.is_active}
                        failureCount={wh.failure_count}
                      />
                    </div>
                    <div className="wh-item-actions">
                      <button
                        className="wh-btn-sm"
                        onClick={() => handleTest(wh.id)}
                        disabled={testingId === wh.id}
                        title="Send test event"
                        style={{
                          fontSize: "0.7rem",
                          fontWeight: 600,
                          letterSpacing: "0.3px",
                          padding: "0.3rem 0.5rem",
                        }}
                      >
                        {testingId === wh.id ? "..." : "Test"}
                      </button>
                      <button
                        className="wh-btn-sm"
                        onClick={() => handleEdit(wh)}
                        title="Edit"
                      >
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                      </button>
                      <button
                        className="wh-btn-sm"
                        onClick={() => handleToggle(wh.id)}
                        title={wh.is_active ? "Disable" : "Enable"}
                      >
                        {wh.is_active ? (
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                          >
                            <circle cx="12" cy="12" r="10" />
                            <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
                          </svg>
                        ) : (
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="var(--green)"
                            strokeWidth="2"
                          >
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                            <polyline points="22 4 12 14.01 9 11.01" />
                          </svg>
                        )}
                      </button>
                      <button
                        className={`wh-btn-sm wh-btn-danger${deleteConfirm === wh.id ? " confirming" : ""}`}
                        onClick={() => handleDelete(wh.id)}
                        title="Delete"
                      >
                        {deleteConfirm === wh.id ? (
                          "OK?"
                        ) : (
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                          >
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6l-2 14H7L5 6m5 0V4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v2" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>
                  <div className="wh-item-url">{truncateUrl(wh.url, 60)}</div>
                  <div className="wh-item-meta">
                    <div className="wh-item-events">
                      {(wh.events || []).map((e) => (
                        <span key={e} className="wh-event-tag">
                          {e}
                        </span>
                      ))}
                    </div>
                    <div className="wh-item-triggered">
                      Last triggered: {formatTime(wh.last_triggered_at)}
                      {wh.failure_count > 0 && (
                        <span className="wh-failure-count">
                          {" "}
                          ({wh.failure_count} failures)
                        </span>
                      )}
                    </div>
                  </div>
                  {testResult && testResult.webhookId === wh.id && (
                    <div
                      style={{
                        marginTop: "0.5rem",
                        padding: "0.5rem 0.75rem",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "0.8rem",
                        fontWeight: 500,
                        background: testResult.success
                          ? "var(--green-dim)"
                          : "var(--red-dim)",
                        color: testResult.success
                          ? "var(--green)"
                          : "var(--red)",
                        border: `1px solid ${testResult.success ? "var(--green)" : "var(--red)"}`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                      }}
                    >
                      <span>
                        {testResult.success
                          ? `Delivered${testResult.statusCode ? ` (${testResult.statusCode})` : ""}${testResult.event ? ` - ${testResult.event}` : ""}`
                          : `Failed${testResult.statusCode ? ` (HTTP ${testResult.statusCode})` : " - could not reach URL"}`}
                      </span>
                      <button
                        onClick={() => setTestResult(null)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "inherit",
                          cursor: "pointer",
                          fontSize: "1rem",
                          lineHeight: 1,
                          padding: 0,
                          opacity: 0.7,
                        }}
                        aria-label="Dismiss"
                      >
                        &times;
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Logs Tab */}
      {activeTab === "logs" && (
        <>
          <div style={{ marginBottom: "1rem" }}>
            <button className="btn-primary" onClick={load}>
              Refresh
            </button>
          </div>
          {logs.length === 0 ? (
            <div className="empty-card">
              <p>
                No webhook deliveries yet. Events will appear here once webhooks
                are triggered.
              </p>
            </div>
          ) : (
            <div className="wh-logs-list">
              {logs.map((log) => (
                <div
                  key={log.id}
                  className={`wh-log-item${selectedLog === log.id ? " wh-log-expanded" : ""}`}
                  onClick={() =>
                    setSelectedLog(selectedLog === log.id ? null : log.id)
                  }
                  style={{ cursor: "pointer" }}
                >
                  <div className="wh-log-header">
                    <span
                      className={`wh-log-status ${log.success ? "wh-log-ok" : "wh-log-fail"}`}
                    >
                      {log.response_status || "ERR"}
                    </span>
                    <span className="wh-event-tag">{log.event}</span>
                    <span className="wh-log-time">
                      {formatTime(log.created_at)}
                    </span>
                  </div>
                  {selectedLog === log.id && (
                    <div className="wh-log-detail">
                      <div className="wh-log-section">
                        <strong>Payload</strong>
                        <pre>{JSON.stringify(log.payload, null, 2)}</pre>
                      </div>
                      <div className="wh-log-section">
                        <strong>
                          Response ({log.response_status || "N/A"})
                        </strong>
                        <pre>{log.response_body || "No response"}</pre>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Templates Tab */}
      {activeTab === "templates" && (
        <>
          {/* Zapier Instructions */}
          <div className="settings-card" style={{ marginBottom: "1.5rem" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                marginBottom: "1rem",
              }}
            >
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--accent)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
              </svg>
              <h3 style={{ margin: 0 }}>Connect with Zapier / Make / n8n</h3>
            </div>
            <ol
              style={{
                color: "var(--text-secondary)",
                lineHeight: 1.8,
                paddingLeft: "1.25rem",
              }}
            >
              <li>
                In your automation tool, create a new workflow and choose{" "}
                <strong>"Webhooks"</strong> as the trigger
              </li>
              <li>
                Select <strong>"Catch Hook"</strong> (Zapier) or{" "}
                <strong>"Custom Webhook"</strong> (Make/n8n)
              </li>
              <li>Copy the webhook URL provided by the tool</li>
              <li>
                Come back here, go to the <strong>Webhooks</strong> tab, click{" "}
                <strong>"+ Add Webhook"</strong>
              </li>
              <li>Paste the URL and select which events to send</li>
              <li>
                Go back to your automation tool and test the trigger - it should
                receive a sample payload
              </li>
              <li>
                Add your action step (Google Sheets, Slack, Mailchimp, CRM,
                etc.)
              </li>
            </ol>
          </div>

          {/* Template Ideas */}
          <h3 style={{ marginBottom: "1rem" }}>Popular Integration Ideas</h3>
          <div className="wh-templates-grid">
            {TEMPLATES.map((tpl, i) => (
              <div key={i} className="wh-template-card">
                <h4>{tpl.title}</h4>
                <p>{tpl.desc}</p>
              </div>
            ))}
          </div>

          {/* Payload Reference */}
          <div className="settings-card" style={{ marginTop: "1.5rem" }}>
            <h3>Webhook Payload Format</h3>
            <p
              style={{
                color: "var(--text-secondary)",
                fontSize: "0.85rem",
                marginBottom: "0.75rem",
              }}
            >
              Every webhook delivery sends a JSON POST with this structure:
            </p>
            <pre className="wh-code-block">{`{
  "event": "lead.created",
  "timestamp": "2026-03-06T12:00:00Z",
  "data": {
    "lead_id": "uuid",
    "name": "John Smith",
    "email": "john@example.com",
    "phone": "555-0100",
    "source": "widget"
  }
}`}</pre>
            <p
              style={{
                color: "var(--text-muted)",
                fontSize: "0.8rem",
                marginTop: "0.75rem",
              }}
            >
              Payloads are signed with HMAC-SHA256 using your webhook secret.
              Verify the
              <code style={{ color: "var(--accent)" }}>
                {" "}
                X-Webhook-Signature
              </code>{" "}
              header to authenticate deliveries.
            </p>
          </div>
        </>
      )}
    </div>
  );
}

/* ── Google Calendar inline styles (dark theme) ── */
const gcStyles = {
  card: {
    background: "var(--bg-card)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: "1.5rem",
    maxWidth: 600,
  },
  cardTop: {
    display: "flex",
    alignItems: "flex-start",
    gap: "1rem",
  },
  iconWrap: {
    flexShrink: 0,
    width: 48,
    height: 48,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "rgba(255,255,255,0.06)",
    borderRadius: "var(--radius-sm)",
  },
  cardInfo: { flex: 1, minWidth: 0 },
  cardTitle: {
    fontSize: "1rem",
    fontWeight: 600,
    color: "var(--text-primary)",
    display: "flex",
    alignItems: "center",
    gap: "0.625rem",
    marginBottom: "0.25rem",
  },
  cardDesc: {
    fontSize: "0.8125rem",
    color: "var(--text-secondary)",
    lineHeight: 1.5,
  },
  connectedBadge: {
    display: "inline-block",
    fontSize: "0.6875rem",
    fontWeight: 600,
    letterSpacing: "0.3px",
    padding: "2px 8px",
    borderRadius: "4px",
    background: "var(--green-dim)",
    color: "var(--green)",
  },
  details: {
    marginTop: "1rem",
    padding: "0.75rem 1rem",
    background: "var(--bg-secondary)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",
  },
  detailRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.75rem",
    fontSize: "0.8125rem",
  },
  detailLabel: {
    color: "var(--text-muted)",
    fontWeight: 500,
    minWidth: 60,
  },
  detailValue: {
    color: "var(--text-primary)",
    wordBreak: "break-all",
  },
  cardActions: {
    marginTop: "1.25rem",
    display: "flex",
    alignItems: "center",
    gap: "0.75rem",
  },
  toast: {
    position: "fixed",
    top: 24,
    right: 24,
    zIndex: 9999,
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    padding: "0.75rem 1.25rem",
    background: "var(--green-dim)",
    border: "1px solid var(--green)",
    borderRadius: "var(--radius)",
    color: "var(--green)",
    fontSize: "0.875rem",
    fontWeight: 500,
    animation: "fadeIn 0.3s ease forwards",
  },
  toastIcon: { fontSize: "1rem", fontWeight: 700 },
  toastClose: {
    marginLeft: "0.5rem",
    background: "none",
    border: "none",
    color: "var(--green)",
    fontSize: "1.125rem",
    cursor: "pointer",
    padding: 0,
    lineHeight: 1,
    opacity: 0.7,
  },
};
