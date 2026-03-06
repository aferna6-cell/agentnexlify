import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";

const BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://agentnexlify-production.up.railway.app";

async function fetchGoogleStatus(token) {
  const res = await fetch(`${BASE}/api/v1/integrations/google/status`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch Google status");
  return res.json();
}

async function startGoogleAuth(token) {
  const res = await fetch(`${BASE}/api/v1/integrations/google/auth`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to start Google auth");
  return res.json();
}

async function disconnectGoogle(token) {
  const res = await fetch(`${BASE}/api/v1/integrations/google`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to disconnect Google");
}

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
      {/* Background */}
      <rect x="8" y="8" width="32" height="32" rx="4" fill="#fff" />
      {/* Top strip (blue) */}
      <rect x="8" y="8" width="32" height="8" rx="4" fill="#4285F4" />
      <rect x="8" y="12" width="32" height="4" fill="#4285F4" />
      {/* Left border (green) */}
      <rect x="8" y="16" width="4" height="20" fill="#0F9D58" />
      <rect x="8" y="36" width="4" height="4" rx="0" fill="#0F9D58" />
      {/* Right border (yellow) */}
      <rect x="36" y="16" width="4" height="20" fill="#F4B400" />
      <rect x="36" y="36" width="4" height="4" rx="0" fill="#F4B400" />
      {/* Bottom border (red) */}
      <rect x="12" y="36" width="24" height="4" fill="#DB4437" />
      {/* Bottom-left corner */}
      <rect x="8" y="36" width="4" height="4" fill="#0F9D58" />
      {/* Bottom-right corner */}
      <rect x="36" y="36" width="4" height="4" fill="#DB4437" />
      {/* Grid lines */}
      <rect x="12" y="20" width="24" height="1" fill="#E0E0E0" />
      <rect x="12" y="25" width="24" height="1" fill="#E0E0E0" />
      <rect x="12" y="30" width="24" height="1" fill="#E0E0E0" />
      <rect x="20" y="16" width="1" height="20" fill="#E0E0E0" />
      <rect x="28" y="16" width="1" height="20" fill="#E0E0E0" />
    </svg>
  );
}

export default function IntegrationsPage({ onNavigate }) {
  const { user, token } = useAuth();

  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(null); // { connected, email, calendar_id, ... }
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [toast, setToast] = useState(null);
  const [error, setError] = useState(null);

  /* ── Show success toast if redirected back with ?google=connected ── */
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("google") === "connected") {
      setToast("Google Calendar connected successfully!");
      // Clean up the URL without reloading
      const url = new URL(window.location);
      url.searchParams.delete("google");
      window.history.replaceState({}, "", url.pathname + url.search);
      // Auto-dismiss toast
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
  }, []);

  /* ── Load connection status ── */
  const loadStatus = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGoogleStatus(token);
      setStatus(data);
    } catch (err) {
      console.error("Failed to load Google status", err);
      setError("Failed to load integration status.");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  /* ── Connect handler ── */
  const handleConnect = async () => {
    if (!user?.tenantId) return;
    setConnecting(true);
    try {
      const data = await startGoogleAuth(token);
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (err) {
      console.error("Failed to start Google auth", err);
      setError("Failed to start Google authorization. Please try again.");
    } finally {
      setConnecting(false);
    }
  };

  /* ── Disconnect handler ── */
  const handleDisconnect = async () => {
    if (!user?.tenantId) return;
    setDisconnecting(true);
    try {
      await disconnectGoogle(token);
      setToast("Google Calendar disconnected.");
      setTimeout(() => setToast(null), 4000);
      await loadStatus();
    } catch (err) {
      console.error("Failed to disconnect Google", err);
      setError("Failed to disconnect. Please try again.");
    } finally {
      setDisconnecting(false);
    }
  };

  if (loading) return <SkeletonLoader />;

  const connected = status?.connected;

  return (
    <div className="fade-in">
      {/* ── Toast ── */}
      {toast && (
        <div style={styles.toast}>
          <span style={styles.toastIcon}>&#10003;</span>
          {toast}
          <button
            onClick={() => setToast(null)}
            style={styles.toastClose}
            aria-label="Dismiss"
          >
            &times;
          </button>
        </div>
      )}

      {/* ── Page Header ── */}
      <div className="page-header">
        <h1>Integrations</h1>
        <p>Connect third-party services</p>
      </div>

      {/* ── Error Banner ── */}
      {error && (
        <div className="error-banner" style={{ marginBottom: "1.25rem" }}>
          {error}
        </div>
      )}

      {/* ── Google Calendar Card ── */}
      <div style={styles.card}>
        <div style={styles.cardTop}>
          <div style={styles.iconWrap}>
            <GoogleCalendarIcon size={40} />
          </div>
          <div style={styles.cardInfo}>
            <div style={styles.cardTitle}>
              Google Calendar
              {connected && (
                <span style={styles.connectedBadge}>Connected</span>
              )}
            </div>
            <div style={styles.cardDesc}>
              Sync appointments to your Google Calendar and check availability
              against existing events
            </div>
          </div>
        </div>

        {/* ── Connected Details ── */}
        {connected && (status?.email || status?.calendar_name) && (
          <div style={styles.details}>
            {status.email && (
              <div style={styles.detailRow}>
                <span style={styles.detailLabel}>Account</span>
                <span style={styles.detailValue}>{status.email}</span>
              </div>
            )}
            {status.calendar_id && (
              <div style={styles.detailRow}>
                <span style={styles.detailLabel}>Calendar</span>
                <span style={styles.detailValue}>{status.calendar_id}</span>
              </div>
            )}
          </div>
        )}

        {/* ── Actions ── */}
        <div style={styles.cardActions}>
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
    </div>
  );
}

/* ── Inline Styles (dark theme) ── */
const styles = {
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
  cardInfo: {
    flex: 1,
    minWidth: 0,
  },
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
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
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
  toastIcon: {
    fontSize: "1rem",
    fontWeight: 700,
  },
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
