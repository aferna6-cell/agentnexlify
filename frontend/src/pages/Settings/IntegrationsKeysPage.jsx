import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  listIntegrationKeys,
  saveIntegrationKey,
  verifyIntegrationKey,
  deleteIntegrationKey,
} from "../../utils/api/integrationKeys";
import ProviderKeyCard from "./ProviderKeyCard";

const PROVIDERS = [
  {
    key: "stripe",
    label: "Stripe",
    description: "Payment processing - required for billing and subscriptions.",
  },
  {
    key: "twilio",
    label: "Twilio",
    description: "SMS and voice - used for appointment reminders and missed-call text-back.",
  },
  {
    key: "resend",
    label: "Resend",
    description: "Transactional email - powers drip sequences, review requests, and onboarding emails.",
  },
];

function indexByProvider(list) {
  const map = {};
  for (const item of list) {
    map[item.provider] = item;
  }
  return map;
}

export default function IntegrationsKeysPage() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [keysMap, setKeysMap] = useState({});

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const list = await listIntegrationKeys(token);
      setKeysMap(indexByProvider(Array.isArray(list) ? list : []));
    } catch (err) {
      setError(err?.body?.detail || err?.message || "Failed to load integration keys.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = useCallback(
    async (provider, plaintext) => {
      const result = await saveIntegrationKey(provider, plaintext, {}, token);
      // Refresh list so masked_key and last_verified_at are current
      const list = await listIntegrationKeys(token);
      setKeysMap(indexByProvider(Array.isArray(list) ? list : []));
      return result;
    },
    [token],
  );

  const handleVerify = useCallback(
    async (provider) => {
      const result = await verifyIntegrationKey(provider, token);
      // Patch health in place so the pill updates without a full reload
      if (result) {
        setKeysMap((prev) => ({
          ...prev,
          [provider]: {
            ...(prev[provider] || { provider }),
            health: result.health,
            detail: result.detail,
          },
        }));
      }
      return result;
    },
    [token],
  );

  const handleRemove = useCallback(
    async (provider) => {
      await deleteIntegrationKey(provider, token);
      setKeysMap((prev) => {
        const next = { ...prev };
        delete next[provider];
        return next;
      });
    },
    [token],
  );

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Integration Keys</h1>
        <p>
          Securely store API keys for Stripe, Twilio, and Resend. Keys are
          encrypted at rest and never returned in full - only a masked preview is
          shown.
        </p>
      </div>

      {loading && (
        <div
          style={{
            padding: "40px 0",
            textAlign: "center",
            color: "var(--text-muted, #6b7280)",
            fontSize: "0.9rem",
          }}
        >
          Loading integration keys...
        </div>
      )}

      {!loading && error && (
        <div
          style={{
            padding: "16px",
            background: "#1c0000",
            border: "1px solid #7f1d1d",
            borderRadius: "8px",
            color: "#f87171",
            fontSize: "0.875rem",
            marginBottom: "24px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "12px",
          }}
        >
          <span>{error}</span>
          <button
            className="btn-secondary"
            style={{ fontSize: "0.8rem", padding: "5px 12px", flexShrink: 0 }}
            onClick={load}
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && (
        <div>
          {PROVIDERS.map(({ key, label, description }) => (
            <div key={key} style={{ marginBottom: "8px" }}>
              <p
                style={{
                  fontSize: "0.8rem",
                  color: "var(--text-muted, #6b7280)",
                  marginBottom: "6px",
                  marginTop: "4px",
                }}
              >
                {description}
              </p>
              <ProviderKeyCard
                provider={key}
                label={label}
                data={keysMap[key] || null}
                onSave={handleSave}
                onVerify={handleVerify}
                onRemove={handleRemove}
              />
            </div>
          ))}

          {Object.keys(keysMap).length === 0 && (
            <div
              style={{
                textAlign: "center",
                padding: "40px 24px",
                color: "var(--text-muted, #6b7280)",
                background: "#0f0f17",
                border: "1px dashed #2e2e4e",
                borderRadius: "10px",
                marginTop: "8px",
              }}
            >
              <p style={{ marginBottom: "8px", fontWeight: 500 }}>
                No integration keys saved yet
              </p>
              <p style={{ fontSize: "0.85rem" }}>
                Add your Stripe, Twilio, and Resend keys above to enable
                payments, SMS, and email features.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
