import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { notify } from "../utils/notify";
import { fetchBridgeConfig, setBridgeToggle } from "../utils/api/os-inbound";
import SkeletonLoader from "../components/SkeletonLoader";

const SOURCES = [
  {
    key: "widget",
    label: "Website Widget",
    description:
      "Embed chat from your site flows into the Agent OS inbox so the orchestrator can read every visitor message.",
  },
  {
    key: "email",
    label: "Inbound Email",
    description:
      "Postmark or Mailgun delivers customer email to the OS inbox. Auto-replies stay tagged so the agent does not loop on them.",
  },
  {
    key: "sms",
    label: "SMS (Twilio)",
    description:
      "Customer texts to your business number land in the inbox. STOP/UNSUBSCRIBE flips the lead's unsubscribed flag automatically.",
  },
  {
    key: "facebook",
    label: "Facebook Messenger",
    description:
      "Page DMs ingested via the existing Facebook webhook are mirrored into OS threads, idempotent on Facebook message id.",
  },
];

const CARD_STYLE = {
  background: "#0f0f17",
  border: "1px solid #1f1f2e",
  borderRadius: "10px",
  padding: "20px",
  marginBottom: "16px",
};

const HEADER_STYLE = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  gap: "16px",
};

function ToggleSwitch({ enabled, disabled, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={enabled}
      style={{
        position: "relative",
        width: "44px",
        height: "24px",
        borderRadius: "12px",
        border: "none",
        background: enabled ? "#3b82f6" : "#3a3a4a",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        transition: "background 0.15s ease",
        flexShrink: 0,
      }}
    >
      <span
        style={{
          position: "absolute",
          top: "2px",
          left: enabled ? "22px" : "2px",
          width: "20px",
          height: "20px",
          borderRadius: "50%",
          background: "#fff",
          transition: "left 0.15s ease",
        }}
      />
    </button>
  );
}

export default function SettingsInboundChannels() {
  const { token } = useAuth();
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pending, setPending] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBridgeConfig(token);
      setConfig(data);
    } catch (err) {
      setError(err?.message || "Failed to load bridge config");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const handleToggle = async (source, nextEnabled) => {
    setPending((p) => ({ ...p, [source]: true }));
    try {
      const updated = await setBridgeToggle(source, nextEnabled, token);
      setConfig(updated);
      notify(
        `${source} bridge ${nextEnabled ? "enabled" : "disabled"}`,
        "success",
      );
    } catch (err) {
      notify(err?.message || "Toggle failed", "error");
    } finally {
      setPending((p) => ({ ...p, [source]: false }));
    }
  };

  const isEnabled = (source) => {
    if (!config) return false;
    return Boolean(config[`${source}_enabled`]);
  };

  return (
    <div style={{ padding: "24px", maxWidth: "880px" }}>
      <div style={{ marginBottom: "24px" }}>
        <h1
          style={{
            fontSize: "1.5rem",
            fontWeight: 600,
            color: "#fff",
            marginBottom: "6px",
          }}
        >
          Inbound Channels
        </h1>
        <p style={{ color: "#9ca3af", fontSize: "0.9rem", margin: 0 }}>
          Control which customer-facing channels bridge into the Agent OS inbox.
          Owner role required to flip toggles.
        </p>
      </div>

      {loading && <SkeletonLoader rows={4} />}

      {error && !loading && (
        <div
          style={{
            background: "#3a1414",
            border: "1px solid #7a2222",
            color: "#fecaca",
            padding: "12px 16px",
            borderRadius: "8px",
            marginBottom: "16px",
          }}
        >
          {error}
          <button
            type="button"
            onClick={load}
            style={{
              marginLeft: "12px",
              background: "transparent",
              border: "1px solid #fecaca",
              color: "#fecaca",
              padding: "4px 10px",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "0.8rem",
            }}
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && config && (
        <div>
          {SOURCES.map((s) => {
            const enabled = isEnabled(s.key);
            const busy = Boolean(pending[s.key]);
            return (
              <div key={s.key} style={CARD_STYLE}>
                <div style={HEADER_STYLE}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        color: "#fff",
                        fontSize: "1rem",
                        fontWeight: 600,
                        marginBottom: "4px",
                      }}
                    >
                      {s.label}
                    </div>
                    <div
                      style={{
                        color: "#9ca3af",
                        fontSize: "0.85rem",
                        lineHeight: 1.5,
                      }}
                    >
                      {s.description}
                    </div>
                    <div
                      style={{
                        marginTop: "10px",
                        fontSize: "0.75rem",
                        color: enabled ? "#34d399" : "#6b7280",
                      }}
                    >
                      {busy
                        ? "Saving…"
                        : enabled
                          ? "Active - messages routing to inbox"
                          : "Disabled - bridge skipped"}
                    </div>
                  </div>
                  <ToggleSwitch
                    enabled={enabled}
                    disabled={busy}
                    onClick={() => handleToggle(s.key, !enabled)}
                  />
                </div>
              </div>
            );
          })}

          <div
            style={{
              marginTop: "20px",
              padding: "14px 16px",
              background: "#11131a",
              border: "1px dashed #2a2a3e",
              borderRadius: "8px",
              color: "#9ca3af",
              fontSize: "0.8rem",
            }}
          >
            Bridges are fail-open. Flipping a bridge off stops new messages from
            being mirrored into the OS inbox but leaves existing threads intact.
            Email inbound address and provider routing are configured in{" "}
            <strong style={{ color: "#cbd5e1" }}>Integrations</strong>.
          </div>
        </div>
      )}
    </div>
  );
}
