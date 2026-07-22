import { useCallback, useEffect, useState } from "react";

import { useAuth } from "../context/AuthContext";
import {
  generateZapierKey,
  listZapierKeys,
  revokeZapierKey,
} from "../utils/api/zapierKeys";

// Plans that unlock Zapier API keys. Mirrors backend
// plan_catalog.PREMIUM_PLANS (agent_os + grandfathered legacy plans).
// chatbot + free are entry/lapsed tiers and see the upgrade CTA.
const ZAPIER_PLANS = new Set([
  "agent_os",
  "growth",
  "autopilot",
  "professional",
  "enterprise",
]);

// #61 publishes the real deep link. Until then the connect button points at
// the docs article and is labeled as pending publish rather than dead.
const ZAPIER_APP_URL = "";
const DOCS_URL = "https://docs.agentnexlify.com/integrations/zapier";

const CRM_CARDS = [
  {
    name: "Jobber",
    bestFor: "Best for home-service teams already invoicing in Jobber.",
  },
  {
    name: "ServiceTitan",
    bestFor: "Best for larger trades shops running dispatch in ServiceTitan.",
  },
  {
    name: "Housecall Pro",
    bestFor: "Best for solo operators who want leads in Housecall Pro fast.",
  },
];

const card = {
  background: "var(--surface, #111827)",
  border: "1px solid var(--border, #1f2937)",
  borderRadius: 10,
  padding: 16,
};

function fmtDate(iso) {
  if (!iso) return "-";
  return iso.slice(0, 10);
}

function GenerateModal({ onClose, onGenerated, token }) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [rawKey, setRawKey] = useState(null);
  const [copied, setCopied] = useState(false);

  const submit = async () => {
    if (!name.trim()) {
      setError("Give the key a name so you can recognize it later.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await generateZapierKey(name.trim(), token);
      setRawKey(created.raw_key);
      onGenerated();
    } catch (e) {
      setError(e?.body?.detail || e?.message || "Could not generate the key.");
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(rawKey);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: 16,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ ...card, width: "100%", maxWidth: 460 }}
      >
        {rawKey ? (
          <>
            <h2 style={{ margin: 0, fontSize: "1.2rem", color: "var(--text-primary)" }}>
              Copy your API key now
            </h2>
            <p
              style={{
                color: "#f59e0b",
                fontSize: "0.85rem",
                margin: "10px 0 0",
                fontWeight: 600,
              }}
            >
              Store this securely. You cannot view it again after you close this
              window.
            </p>
            <code
              style={{
                display: "block",
                marginTop: 12,
                padding: "10px 12px",
                background: "var(--bg, #0b0f19)",
                border: "1px solid var(--border, #1f2937)",
                borderRadius: 6,
                color: "var(--text-primary)",
                fontSize: "0.85rem",
                wordBreak: "break-all",
              }}
            >
              {rawKey}
            </code>
            <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
              <button type="button" className="btn-primary" onClick={copy}>
                {copied ? "Copied" : "Copy key"}
              </button>
              <button
                type="button"
                onClick={onClose}
                style={{
                  background: "none",
                  border: "1px solid var(--border, #1f2937)",
                  color: "var(--text-muted)",
                  borderRadius: 6,
                  padding: "8px 14px",
                  cursor: "pointer",
                }}
              >
                Done
              </button>
            </div>
          </>
        ) : (
          <>
            <h2 style={{ margin: 0, fontSize: "1.2rem", color: "var(--text-primary)" }}>
              Generate API key
            </h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: "8px 0 14px" }}>
              Name this key so you can tell your Zapier connections apart.
            </p>
            <input
              autoFocus
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder="My Zapier Integration"
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "9px 12px",
                background: "var(--bg, #0b0f19)",
                border: "1px solid var(--border, #1f2937)",
                borderRadius: 6,
                color: "var(--text-primary)",
                fontSize: "0.9rem",
              }}
            />
            {error && (
              <p style={{ color: "#ef4444", fontSize: "0.8rem", margin: "10px 0 0" }}>
                {error}
              </p>
            )}
            <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
              <button type="button" className="btn-primary" onClick={submit} disabled={busy}>
                {busy ? "Generating..." : "Generate"}
              </button>
              <button
                type="button"
                onClick={onClose}
                style={{
                  background: "none",
                  border: "1px solid var(--border, #1f2937)",
                  color: "var(--text-muted)",
                  borderRadius: 6,
                  padding: "8px 14px",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function RevokeModal({ keyRow, onClose, onConfirm, busy }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: 16,
      }}
    >
      <div onClick={(e) => e.stopPropagation()} style={{ ...card, width: "100%", maxWidth: 420 }}>
        <h2 style={{ margin: 0, fontSize: "1.15rem", color: "var(--text-primary)" }}>
          Revoke this key?
        </h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: "10px 0 0" }}>
          Any Zapier connection using <strong>{keyRow.name}</strong> (
          {keyRow.key_prefix}...) stops working immediately. This cannot be
          undone.
        </p>
        <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            style={{
              background: "#ef4444",
              border: "none",
              color: "#fff",
              borderRadius: 6,
              padding: "8px 14px",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            {busy ? "Revoking..." : "Revoke key"}
          </button>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: "none",
              border: "1px solid var(--border, #1f2937)",
              color: "var(--text-muted)",
              borderRadius: 6,
              padding: "8px 14px",
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

function UpgradeGate() {
  return (
    <div style={{ ...card, textAlign: "center", padding: 32, maxWidth: 560 }}>
      <h2 style={{ margin: 0, fontSize: "1.25rem", color: "var(--text-primary)" }}>
        Zapier is part of Agent OS
      </h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", margin: "10px 0 18px" }}>
        Push new leads into Jobber, ServiceTitan, Housecall Pro, and 6,000+ apps
        the moment they come in. Upgrade to Agent OS to generate API keys and
        connect Zapier.
      </p>
      <a href="/dashboard/billing" className="btn-primary" style={{ textDecoration: "none" }}>
        Upgrade to Agent OS
      </a>
    </div>
  );
}

export default function IntegrationsZapierPage() {
  const { user, token } = useAuth();
  const plan = user?.plan || "free";
  const allowed = ZAPIER_PLANS.has(plan);

  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showGenerate, setShowGenerate] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState(null);
  const [revoking, setRevoking] = useState(false);

  const load = useCallback(async () => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const rows = await listZapierKeys(token);
      setKeys(Array.isArray(rows) ? rows : []);
    } catch (e) {
      setError(e?.body?.detail || e?.message || "Failed to load API keys.");
    } finally {
      setLoading(false);
    }
  }, [allowed, token]);

  useEffect(() => {
    load();
  }, [load]);

  const confirmRevoke = async () => {
    setRevoking(true);
    try {
      await revokeZapierKey(revokeTarget.id, token);
      setRevokeTarget(null);
      load();
    } catch (e) {
      setError(e?.body?.detail || e?.message || "Failed to revoke the key.");
    } finally {
      setRevoking(false);
    }
  };

  const activeKeys = keys.filter((k) => !k.revoked_at);

  return (
    <div style={{ padding: "24px 28px", maxWidth: 900, margin: "0 auto" }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ margin: 0, fontSize: "1.5rem", color: "var(--text-primary)" }}>
          Zapier
        </h1>
        <p style={{ margin: "6px 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>
          Generate an API key, then connect AgentNexLiFy to your CRM through
          Zapier so new leads sync automatically.{" "}
          <a href={DOCS_URL} style={{ color: "var(--purple, #8b5cf6)" }}>
            Read the setup guide
          </a>
          .
        </p>
      </div>

      {!allowed ? (
        <UpgradeGate />
      ) : (
        <>
          <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" }}>
            <button type="button" className="btn-primary" onClick={() => setShowGenerate(true)}>
              Generate API key
            </button>
            {ZAPIER_APP_URL ? (
              <a
                href={ZAPIER_APP_URL}
                target="_blank"
                rel="noreferrer"
                style={{
                  background: "none",
                  border: "1px solid var(--border, #1f2937)",
                  color: "var(--text-primary)",
                  borderRadius: 6,
                  padding: "8px 14px",
                  textDecoration: "none",
                  alignSelf: "center",
                }}
              >
                Connect to Zapier
              </a>
            ) : (
              <span
                title="The AgentNexLiFy Zapier app is pending publication."
                style={{
                  border: "1px solid var(--border, #1f2937)",
                  color: "var(--text-muted)",
                  borderRadius: 6,
                  padding: "8px 14px",
                  fontSize: "0.85rem",
                  alignSelf: "center",
                }}
              >
                Connect to Zapier (coming soon)
              </span>
            )}
          </div>

          {loading && <p style={{ color: "var(--text-muted)" }}>Loading API keys...</p>}

          {error && !loading && <p style={{ color: "#ef4444" }}>{error}</p>}

          {!loading && !error && activeKeys.length === 0 && (
            <div
              style={{
                border: "1px dashed var(--border, #1f2937)",
                borderRadius: 10,
                padding: 32,
                textAlign: "center",
                color: "var(--text-muted)",
              }}
            >
              <p style={{ margin: 0 }}>No API keys yet.</p>
              <p style={{ margin: "8px 0 0", fontSize: "0.85rem" }}>
                Generate your first to connect Zapier.
              </p>
            </div>
          )}

          {!loading && !error && activeKeys.length > 0 && (
            <div style={{ overflowX: "auto", marginBottom: 28 }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
                <thead>
                  <tr style={{ color: "var(--text-muted)", textAlign: "left" }}>
                    <th style={{ padding: 8 }}>Name</th>
                    <th style={{ padding: 8 }}>Key</th>
                    <th style={{ padding: 8 }}>Created</th>
                    <th style={{ padding: 8 }}>Last used</th>
                    <th style={{ padding: 8 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {activeKeys.map((k) => (
                    <tr
                      key={k.id}
                      style={{
                        borderTop: "1px solid var(--border, #1f2937)",
                        color: "var(--text-primary)",
                      }}
                    >
                      <td style={{ padding: 8 }}>{k.name}</td>
                      <td style={{ padding: 8, fontFamily: "monospace" }}>
                        {k.key_prefix}...
                      </td>
                      <td style={{ padding: 8, whiteSpace: "nowrap" }}>{fmtDate(k.created_at)}</td>
                      <td style={{ padding: 8, whiteSpace: "nowrap" }}>
                        {k.last_used_at ? fmtDate(k.last_used_at) : "Never"}
                      </td>
                      <td style={{ padding: 8, textAlign: "right" }}>
                        <button
                          type="button"
                          onClick={() => setRevokeTarget(k)}
                          style={{
                            background: "none",
                            border: "1px solid var(--border, #1f2937)",
                            color: "#ef4444",
                            borderRadius: 5,
                            cursor: "pointer",
                            fontSize: "0.8rem",
                            padding: "4px 10px",
                          }}
                        >
                          Revoke
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h2 style={{ fontSize: "1.05rem", color: "var(--text-primary)", margin: "8px 0 12px" }}>
            Popular CRM connections
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 12,
            }}
          >
            {CRM_CARDS.map((c) => (
              <div key={c.name} style={card}>
                <div style={{ color: "var(--text-primary)", fontWeight: 600 }}>{c.name}</div>
                <div style={{ color: "var(--text-muted)", fontSize: "0.82rem", marginTop: 6 }}>
                  {c.bestFor}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {showGenerate && (
        <GenerateModal
          token={token}
          onClose={() => {
            setShowGenerate(false);
            load();
          }}
          onGenerated={load}
        />
      )}

      {revokeTarget && (
        <RevokeModal
          keyRow={revokeTarget}
          busy={revoking}
          onClose={() => setRevokeTarget(null)}
          onConfirm={confirmRevoke}
        />
      )}
    </div>
  );
}
