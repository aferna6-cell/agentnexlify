/**
 * Integration Keys Settings page - GH #132
 *
 * Lets tenant owners save, verify, and delete third-party API keys
 * (Stripe, Twilio, Resend) managed by the backend vault.
 *
 * Health values from the backend:
 *   green  → healthy
 *   yellow → needs_attention
 *   red    → not_ready (or not configured)
 *
 * Critical: tenant_id comes from JWT on the backend. Never sent in request body.
 */
import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import {
  listKeys,
  saveKey,
  deleteKey,
  verifyKey,
  fetchIntegrationHealth,
} from "../utils/api/integrationKeys";

// ── Provider metadata ──────────────────────────────────────────────────────

const PROVIDERS = [
  {
    key: "stripe",
    label: "Stripe",
    description:
      "Processes payments and manages subscriptions for your clients. Required for billing features.",
    keyLabel: "Secret Key",
    keyPlaceholder: "Stripe secret key (starts with sk_live or sk_test)",
    docsUrl: "https://dashboard.stripe.com/apikeys",
    docsLabel: "Get key from Stripe Dashboard",
  },
  {
    key: "twilio",
    label: "Twilio",
    description:
      "Sends SMS messages and handles voice calls. Powers appointment reminders and lead follow-ups.",
    keyLabel: "Auth Token",
    keyPlaceholder: "Twilio Auth Token (32-character hex)",
    docsUrl: "https://console.twilio.com/",
    docsLabel: "Get token from Twilio Console",
  },
  {
    key: "resend",
    label: "Resend",
    description:
      "Delivers transactional email - confirmations, follow-ups, and automation sequences.",
    keyLabel: "API Key",
    keyPlaceholder: "re_...",
    docsUrl: "https://resend.com/api-keys",
    docsLabel: "Get key from Resend Dashboard",
  },
];

// ── Health badge ──────────────────────────────────────────────────────────

function HealthBadge({ health }) {
  const cfg = {
    green: {
      label: "Healthy",
      color: "var(--green)",
      bg: "var(--green-dim)",
    },
    yellow: {
      label: "Needs attention",
      color: "var(--yellow)",
      bg: "var(--yellow-dim)",
    },
    red: {
      label: "Not ready",
      color: "var(--red, #ef4444)",
      bg: "var(--red-dim, rgba(239,68,68,0.12))",
    },
  }[health] || {
    label: "Unknown",
    color: "var(--text-muted)",
    bg: "var(--bg-secondary)",
  };

  return (
    <span
      style={{
        display: "inline-block",
        fontSize: "0.6875rem",
        fontWeight: 600,
        letterSpacing: "0.3px",
        padding: "2px 8px",
        borderRadius: "4px",
        background: cfg.bg,
        color: cfg.color,
      }}
    >
      {cfg.label}
    </span>
  );
}

// ── Provider icon (simple letter avatar) ─────────────────────────────────

const PROVIDER_COLORS = {
  stripe: "#6772E5",
  twilio: "#F22F46",
  resend: "#000000",
};

function ProviderAvatar({ providerKey, label }) {
  return (
    <div
      style={{
        flexShrink: 0,
        width: 40,
        height: 40,
        borderRadius: "8px",
        background: PROVIDER_COLORS[providerKey] || "var(--bg-secondary)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "0.875rem",
        fontWeight: 700,
        color: "#fff",
        letterSpacing: "-0.5px",
      }}
    >
      {label.slice(0, 2).toUpperCase()}
    </div>
  );
}

// ── Per-provider card ─────────────────────────────────────────────────────

function ProviderCard({ provider, keyData, token, onSaved, onDeleted }) {
  const [editing, setEditing] = useState(false);
  const [keyInput, setKeyInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [saveResult, setSaveResult] = useState(null);

  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);

  const [deleting, setDeleting] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  const isConfigured = !!keyData;
  const health = keyData?.health || null;

  const handleSave = async () => {
    if (!keyInput.trim()) return;
    setSaving(true);
    setSaveError(null);
    setSaveResult(null);
    try {
      const result = await saveKey(provider.key, keyInput.trim(), token);
      setSaveResult(result);
      setKeyInput("");
      setEditing(false);
      onSaved(provider.key, result);
    } catch (err) {
      const msg =
        err?.body?.detail ||
        err?.message ||
        "Failed to save key. Check the value and try again.";
      setSaveError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    setVerifyResult(null);
    try {
      const result = await verifyKey(provider.key, token);
      setVerifyResult(result);
      // Propagate updated health to parent so the list reflects it
      onSaved(provider.key, { verified: result.health, masked: keyData?.masked_key || "" });
    } catch (err) {
      const msg =
        err?.body?.detail || err?.message || "Verification failed.";
      setVerifyResult({ health: "red", detail: msg });
    } finally {
      setVerifying(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) {
      setDeleteConfirm(true);
      return;
    }
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteKey(provider.key, token);
      setDeleteConfirm(false);
      onDeleted(provider.key);
    } catch (err) {
      if (err?.status === 409) {
        setDeleteError(
          "Cannot remove the Stripe key while there is an active subscription. " +
            "Cancel or migrate the subscription first.",
        );
      } else {
        setDeleteError(
          err?.body?.detail || err?.message || "Failed to delete key.",
        );
      }
      setDeleteConfirm(false);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        padding: "1.5rem",
        maxWidth: 640,
        marginBottom: "1rem",
      }}
    >
      {/* Card header */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: "1rem" }}>
        <ProviderAvatar providerKey={provider.key} label={provider.label} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: "1rem",
              fontWeight: 600,
              color: "var(--text-primary)",
              display: "flex",
              alignItems: "center",
              gap: "0.625rem",
              marginBottom: "0.25rem",
            }}
          >
            {provider.label}
            {isConfigured && health && <HealthBadge health={health} />}
          </div>
          <div
            style={{
              fontSize: "0.8125rem",
              color: "var(--text-secondary)",
              lineHeight: 1.5,
            }}
          >
            {provider.description}
          </div>
        </div>
      </div>

      {/* Masked key + detail when configured */}
      {isConfigured && (
        <div
          style={{
            marginTop: "1rem",
            padding: "0.75rem 1rem",
            background: "var(--bg-secondary)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              fontSize: "0.8125rem",
              marginBottom: keyData?.detail ? "0.375rem" : 0,
            }}
          >
            <span
              style={{ color: "var(--text-muted)", fontWeight: 500, minWidth: 60 }}
            >
              Key
            </span>
            <span
              style={{
                color: "var(--text-primary)",
                fontFamily: "monospace",
                fontSize: "0.8rem",
                wordBreak: "break-all",
              }}
            >
              {keyData.masked_key || "••••••••"}
            </span>
          </div>
          {keyData?.detail && (
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "0.75rem",
                fontSize: "0.8125rem",
              }}
            >
              <span
                style={{
                  color: "var(--text-muted)",
                  fontWeight: 500,
                  minWidth: 60,
                }}
              >
                Status
              </span>
              <span style={{ color: "var(--text-secondary)", lineHeight: 1.4 }}>
                {keyData.detail}
              </span>
            </div>
          )}
          {keyData?.last_verified_at && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                fontSize: "0.75rem",
                marginTop: "0.375rem",
              }}
            >
              <span
                style={{
                  color: "var(--text-muted)",
                  fontWeight: 500,
                  minWidth: 60,
                }}
              >
                Verified
              </span>
              <span style={{ color: "var(--text-muted)" }}>
                {new Date(keyData.last_verified_at).toLocaleString()}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Inline verify result */}
      {verifyResult && (
        <div
          style={{
            marginTop: "0.75rem",
            padding: "0.5rem 0.875rem",
            borderRadius: "var(--radius-sm)",
            fontSize: "0.8125rem",
            background:
              verifyResult.health === "green"
                ? "var(--green-dim)"
                : verifyResult.health === "yellow"
                  ? "var(--yellow-dim)"
                  : "var(--red-dim, rgba(239,68,68,0.12))",
            color:
              verifyResult.health === "green"
                ? "var(--green)"
                : verifyResult.health === "yellow"
                  ? "var(--yellow)"
                  : "var(--red, #ef4444)",
            border: `1px solid ${
              verifyResult.health === "green"
                ? "var(--green)"
                : verifyResult.health === "yellow"
                  ? "var(--yellow)"
                  : "var(--red, #ef4444)"
            }`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "0.5rem",
          }}
        >
          <span>{verifyResult.detail}</span>
          <button
            onClick={() => setVerifyResult(null)}
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

      {/* Save result after key submission */}
      {saveResult && (
        <div
          style={{
            marginTop: "0.75rem",
            padding: "0.5rem 0.875rem",
            borderRadius: "var(--radius-sm)",
            fontSize: "0.8125rem",
            background: "var(--green-dim)",
            color: "var(--green)",
            border: "1px solid var(--green)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "0.5rem",
          }}
        >
          <span>Key saved. Health check: {saveResult.verified}. Masked: {saveResult.masked}</span>
          <button
            onClick={() => setSaveResult(null)}
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

      {/* Delete error */}
      {deleteError && (
        <div
          className="error-banner"
          style={{ marginTop: "0.75rem" }}
        >
          {deleteError}
          <button
            onClick={() => setDeleteError(null)}
            style={{
              background: "none",
              border: "none",
              color: "inherit",
              cursor: "pointer",
              fontSize: "1rem",
              marginLeft: "0.5rem",
              opacity: 0.7,
              lineHeight: 1,
              padding: 0,
            }}
            aria-label="Dismiss"
          >
            &times;
          </button>
        </div>
      )}

      {/* Save error */}
      {saveError && (
        <div
          className="error-banner"
          style={{ marginTop: "0.75rem" }}
        >
          {saveError}
        </div>
      )}

      {/* Key input form */}
      {editing && (
        <div
          style={{
            marginTop: "1rem",
            padding: "1rem",
            background: "var(--bg-secondary)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <label
            style={{
              display: "block",
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              fontWeight: 500,
              marginBottom: "0.375rem",
            }}
          >
            {provider.keyLabel}
          </label>
          <input
            type="password"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder={provider.keyPlaceholder}
            autoComplete="off"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSave();
              if (e.key === "Escape") {
                setEditing(false);
                setKeyInput("");
                setSaveError(null);
              }
            }}
            style={{
              width: "100%",
              padding: "0.5rem 0.75rem",
              fontSize: "0.8125rem",
              background: "var(--bg-primary)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
              color: "var(--text-primary)",
              fontFamily: "monospace",
              boxSizing: "border-box",
            }}
          />
          <p
            style={{
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              margin: "0.375rem 0 0",
              lineHeight: 1.5,
            }}
          >
            The key is encrypted at rest and never stored in plaintext. &nbsp;
            <a
              href={provider.docsUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "var(--accent)" }}
            >
              {provider.docsLabel}
            </a>
          </p>
          <div
            style={{
              display: "flex",
              gap: "0.5rem",
              marginTop: "0.875rem",
            }}
          >
            <button
              className="btn-primary"
              onClick={handleSave}
              disabled={saving || !keyInput.trim()}
              style={{ fontSize: "0.8125rem" }}
            >
              {saving ? "Saving..." : isConfigured ? "Update Key" : "Save Key"}
            </button>
            <button
              className="btn-secondary"
              onClick={() => {
                setEditing(false);
                setKeyInput("");
                setSaveError(null);
              }}
              style={{ fontSize: "0.8125rem" }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div
        style={{
          marginTop: "1.25rem",
          display: "flex",
          alignItems: "center",
          gap: "0.625rem",
          flexWrap: "wrap",
        }}
      >
        {!editing && (
          <button
            className="btn-primary"
            onClick={() => {
              setEditing(true);
              setSaveError(null);
              setSaveResult(null);
            }}
            style={{ fontSize: "0.8125rem" }}
          >
            {isConfigured ? "Update Key" : "Add Key"}
          </button>
        )}

        {isConfigured && !editing && (
          <button
            className="btn-secondary"
            onClick={handleVerify}
            disabled={verifying}
            style={{ fontSize: "0.8125rem" }}
          >
            {verifying ? "Checking..." : "Verify Now"}
          </button>
        )}

        {isConfigured && !editing && (
          <button
            className="btn-danger"
            onClick={handleDelete}
            disabled={deleting}
            style={{ fontSize: "0.8125rem" }}
          >
            {deleting
              ? "Removing..."
              : deleteConfirm
                ? "Confirm remove?"
                : "Remove Key"}
          </button>
        )}

        {deleteConfirm && !deleting && (
          <button
            className="btn-secondary"
            onClick={() => setDeleteConfirm(false)}
            style={{ fontSize: "0.8125rem" }}
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

// ── Aggregate health banner ───────────────────────────────────────────────

function AggregateHealthBanner({ overall }) {
  if (!overall) return null;

  const cfg = {
    healthy: {
      text: "All integrations are healthy.",
      color: "var(--green)",
      bg: "var(--green-dim)",
      border: "var(--green)",
    },
    needs_attention: {
      text: "One or more integrations need attention.",
      color: "var(--yellow)",
      bg: "var(--yellow-dim)",
      border: "var(--yellow)",
    },
    not_ready: {
      text: "Some integrations are not configured or failing.",
      color: "var(--red, #ef4444)",
      bg: "var(--red-dim, rgba(239,68,68,0.12))",
      border: "var(--red, #ef4444)",
    },
  }[overall];

  if (!cfg) return null;

  return (
    <div
      style={{
        padding: "0.625rem 1rem",
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        borderRadius: "var(--radius-sm)",
        color: cfg.color,
        fontSize: "0.8125rem",
        fontWeight: 500,
        marginBottom: "1.5rem",
        maxWidth: 640,
      }}
    >
      {cfg.text}
    </div>
  );
}

// ── Empty / not-configured callout ────────────────────────────────────────

function EmptyState() {
  return (
    <div
      className="empty-card"
      style={{ maxWidth: 640, marginBottom: "1.5rem" }}
    >
      <p style={{ marginBottom: "0.5rem", fontWeight: 600, color: "var(--text-primary)" }}>
        No integration keys configured yet
      </p>
      <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: "0.875rem", lineHeight: 1.6 }}>
        Add your Stripe, Twilio, and Resend API keys below to unlock payments,
        SMS follow-ups, and transactional email. Each key is encrypted at rest
        and health-checked automatically after saving.
      </p>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────

export default function IntegrationKeysSettings() {
  const { token } = useAuth();

  const [keyMap, setKeyMap] = useState({}); // { [provider]: ProviderHealth }
  const [overall, setOverall] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [toast, setToast] = useState(null);

  const loadKeys = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setLoadError(null);
    try {
      const [keys, health] = await Promise.all([
        listKeys(token),
        fetchIntegrationHealth(token),
      ]);
      const map = {};
      (keys || []).forEach((k) => {
        map[k.provider] = k;
      });
      setKeyMap(map);
      setOverall(health?.overall || null);
    } catch (err) {
      setLoadError(
        err?.body?.detail ||
          err?.message ||
          "Failed to load integration keys.",
      );
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadKeys();
  }, [loadKeys]);

  const handleSaved = useCallback((providerKey, result) => {
    // Merge updated health into the keyMap optimistically.
    // result is either a SaveKeyResult { saved, verified, masked }
    // or a verifyKey result { health, detail }.
    setKeyMap((prev) => {
      const existing = prev[providerKey] || {};
      const updatedHealth = result.verified || result.health || existing.health;
      const updatedMasked = result.masked || existing.masked_key;
      return {
        ...prev,
        [providerKey]: {
          ...existing,
          provider: providerKey,
          health: updatedHealth,
          masked_key: updatedMasked,
          detail: result.detail || existing.detail || "",
          last_verified_at:
            result.last_verified_at ||
            existing.last_verified_at ||
            new Date().toISOString(),
        },
      };
    });
    setToast("Key saved and verified.");
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, []);

  const handleDeleted = useCallback((providerKey) => {
    setKeyMap((prev) => {
      const next = { ...prev };
      delete next[providerKey];
      return next;
    });
    setToast("Key removed.");
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, []);

  const configuredCount = Object.keys(keyMap).length;

  return (
    <div className="fade-in">
      {/* Toast */}
      {toast && (
        <div
          style={{
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
          }}
        >
          <span style={{ fontWeight: 700 }}>&#10003;</span>
          {toast}
          <button
            onClick={() => setToast(null)}
            style={{
              marginLeft: "0.5rem",
              background: "none",
              border: "none",
              color: "var(--green)",
              fontSize: "1.125rem",
              cursor: "pointer",
              padding: 0,
              lineHeight: 1,
              opacity: 0.7,
            }}
            aria-label="Dismiss"
          >
            &times;
          </button>
        </div>
      )}

      {/* Page header */}
      <div className="page-header">
        <h1>Integration Keys</h1>
        <p>
          Manage encrypted API keys for Stripe, Twilio, and Resend. Keys are
          health-checked after saving and can be verified or rotated at any
          time.
        </p>
      </div>

      {/* Loading state */}
      {loading && (
        <div
          style={{
            color: "var(--text-muted)",
            fontSize: "0.875rem",
            padding: "2rem 0",
          }}
        >
          Loading integration keys...
        </div>
      )}

      {/* Load error */}
      {!loading && loadError && (
        <div
          className="error-banner"
          style={{ maxWidth: 640, marginBottom: "1rem" }}
        >
          {loadError}
          <button
            className="btn-secondary"
            onClick={loadKeys}
            style={{ marginLeft: "1rem", fontSize: "0.8125rem" }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Content */}
      {!loading && !loadError && (
        <>
          {/* Aggregate health banner */}
          <AggregateHealthBanner overall={overall} />

          {/* Empty state - shown only when no keys are configured */}
          {configuredCount === 0 && <EmptyState />}

          {/* Provider cards */}
          {PROVIDERS.map((provider) => (
            <ProviderCard
              key={provider.key}
              provider={provider}
              keyData={keyMap[provider.key] || null}
              token={token}
              onSaved={handleSaved}
              onDeleted={handleDeleted}
            />
          ))}
        </>
      )}
    </div>
  );
}
