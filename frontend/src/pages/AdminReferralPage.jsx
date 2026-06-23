import { useState, useEffect, useCallback } from "react";
import { BASE } from "../utils/api/_client";

// ---------------------------------------------------------------------------
// Admin-secret pattern — identical to AdminFunnelPage + AdminTenantHealthPage.
// Secret is entered at runtime via window.prompt; never baked into the bundle.
// ---------------------------------------------------------------------------
let _adminSecret = "";

function getAdminSecret() {
  if (!_adminSecret) {
    _adminSecret = window.prompt("Enter admin secret:") || "";
  }
  return _adminSecret;
}

function clearAdminSecret() {
  _adminSecret = "";
}

async function apiFetch(path) {
  const secret = getAdminSecret();
  if (!secret) throw new Error("No admin secret provided");
  const res = await fetch(`${BASE}/api/v1/referral${path}`, {
    headers: {
      "x-api-secret": secret,
      "Content-Type": "application/json",
    },
  });
  if (res.status === 401) {
    clearAdminSecret();
    throw new Error("Invalid admin secret - cleared. Refresh to retry.");
  }
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Styling helpers — match existing admin pages
// ---------------------------------------------------------------------------
const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

const TH_STYLE = {
  padding: "10px 14px",
  textAlign: "left",
  fontSize: "0.72rem",
  fontWeight: 700,
  color: "var(--text-muted, #9ca3af)",
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  borderBottom: "1px solid var(--border, #374151)",
  whiteSpace: "nowrap",
};

const TD_STYLE = {
  padding: "11px 14px",
  fontSize: "0.82rem",
  color: "var(--text-primary, #f1f5f9)",
  borderBottom: "1px solid var(--border, #1f2937)",
  whiteSpace: "nowrap",
};

const NUM_TD = {
  ...TD_STYLE,
  textAlign: "right",
  fontVariantNumeric: "tabular-nums",
  color: "var(--text-secondary, #94a3b8)",
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function TotalsBar({ totals }) {
  const cards = [
    {
      label: "Total Clicks",
      value: totals.total_clicks ?? 0,
      color: "var(--text-primary, #f1f5f9)",
    },
    {
      label: "Referred Signups",
      value: totals.total_referred_signups ?? 0,
      color: "#10b981",
    },
  ];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
        gap: 16,
        marginBottom: 28,
      }}
    >
      {cards.map((c) => (
        <div key={c.label} style={cardStyle}>
          <div
            style={{
              fontSize: "0.72rem",
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: 8,
            }}
          >
            {c.label}
          </div>
          <div
            style={{
              fontSize: "2rem",
              fontWeight: 700,
              color: c.color,
              lineHeight: 1,
            }}
          >
            {c.value}
          </div>
        </div>
      ))}
    </div>
  );
}

function ReferralTable({ tenants }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: "0.85rem",
        }}
      >
        <thead>
          <tr>
            <th style={{ ...TH_STYLE, width: "2rem" }}>#</th>
            <th style={TH_STYLE}>Business</th>
            <th style={{ ...TH_STYLE, fontFamily: "monospace" }}>Ref Code</th>
            <th style={{ ...TH_STYLE, textAlign: "right" }}>Clicks</th>
            <th style={{ ...TH_STYLE, textAlign: "right" }}>
              Referred Signups
            </th>
          </tr>
        </thead>
        <tbody>
          {tenants.map((t, i) => {
            const hasSignups = (t.referred_signups ?? 0) > 0;
            return (
              <tr
                key={t.tenant_id}
                style={{
                  background: hasSignups
                    ? "rgba(16,185,129,0.04)"
                    : "transparent",
                }}
              >
                <td
                  style={{
                    ...TD_STYLE,
                    color: "var(--text-muted, #9ca3af)",
                    fontSize: "0.75rem",
                    width: "2rem",
                  }}
                >
                  {i + 1}
                </td>
                <td style={TD_STYLE}>
                  <span style={{ fontWeight: hasSignups ? 600 : 400 }}>
                    {t.business_name || "—"}
                  </span>
                </td>
                <td style={TD_STYLE}>
                  <span
                    style={{
                      fontFamily: "monospace",
                      fontSize: "0.78rem",
                      color: "var(--text-secondary, #94a3b8)",
                      background: "rgba(255,255,255,0.05)",
                      padding: "2px 8px",
                      borderRadius: 4,
                    }}
                  >
                    {t.ref_code || "—"}
                  </span>
                </td>
                <td style={NUM_TD}>{t.total_clicks ?? 0}</td>
                <td
                  style={{
                    ...NUM_TD,
                    color: hasSignups ? "#10b981" : "var(--text-muted, #9ca3af)",
                    fontWeight: hasSignups ? 700 : 400,
                  }}
                >
                  {t.referred_signups ?? 0}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function AdminReferralPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch("/admin/overview");
      setData(result);
    } catch (err) {
      setError(err.message || "Failed to load referral data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const tenants = data?.tenants ?? [];
  const totals = data?.totals ?? { total_clicks: 0, total_referred_signups: 0 };

  return (
    <div
      style={{
        padding: "32px 32px 64px",
        maxWidth: 1100,
        margin: "0 auto",
        color: "var(--text-primary, #f1f5f9)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 28,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div>
          <h1
            style={{
              margin: 0,
              fontSize: "1.5rem",
              fontWeight: 700,
              color: "var(--text-primary, #f1f5f9)",
            }}
          >
            Referral Overview
          </h1>
          {data?.computed_at && (
            <p
              style={{
                margin: "4px 0 0",
                fontSize: "0.75rem",
                color: "var(--text-muted)",
              }}
            >
              Computed at {new Date(data.computed_at).toLocaleString()}
            </p>
          )}
        </div>
        <button
          onClick={load}
          disabled={loading}
          style={{
            background: "var(--accent, #6366f1)",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "8px 18px",
            fontSize: "0.85rem",
            fontWeight: 600,
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {/* Error state */}
      {error && !loading && (
        <div
          style={{
            ...cardStyle,
            borderColor: "#f87171",
            background: "rgba(239,68,68,0.08)",
            marginBottom: 24,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            flexWrap: "wrap",
          }}
        >
          <span style={{ color: "#f87171", fontSize: "0.9rem" }}>{error}</span>
          <button
            onClick={load}
            style={{
              background: "transparent",
              color: "#f87171",
              border: "1px solid #f87171",
              borderRadius: 6,
              padding: "6px 14px",
              fontSize: "0.8rem",
              cursor: "pointer",
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && !data && (
        <div
          style={{
            ...cardStyle,
            textAlign: "center",
            padding: 60,
            color: "var(--text-muted)",
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              border: "3px solid rgba(255,255,255,0.1)",
              borderTopColor: "#6366f1",
              borderRadius: "50%",
              animation: "spin 0.8s linear infinite",
              margin: "0 auto 16px",
            }}
          />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          Loading referral data...
        </div>
      )}

      {/* Empty state */}
      {!loading && data && tenants.length === 0 && (
        <div
          style={{
            ...cardStyle,
            textAlign: "center",
            padding: 60,
            color: "var(--text-muted)",
          }}
        >
          <div
            style={{
              fontSize: "1rem",
              fontWeight: 600,
              color: "var(--text-secondary)",
              marginBottom: 8,
            }}
          >
            No referral data yet
          </div>
          <p
            style={{
              fontSize: "0.85rem",
              margin: 0,
              maxWidth: 400,
              marginInline: "auto",
            }}
          >
            This table populates once tenants have referral codes and their
            links receive clicks. Share the referral program with tenants to
            start generating data here.
          </p>
        </div>
      )}

      {/* Main content */}
      {!loading && data && tenants.length > 0 && (
        <>
          {/* Totals summary */}
          <TotalsBar totals={totals} />

          {/* Per-tenant table */}
          <div style={cardStyle}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 16,
                flexWrap: "wrap",
                gap: 8,
              }}
            >
              <h2
                style={{
                  margin: 0,
                  fontSize: "0.9rem",
                  fontWeight: 600,
                  color: "var(--text-secondary, #94a3b8)",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Tenants — ranked by referred signups
              </h2>
              <span
                style={{
                  fontSize: "0.78rem",
                  color: "var(--text-muted)",
                }}
              >
                {tenants.length} tenant{tenants.length !== 1 ? "s" : ""}
              </span>
            </div>
            <ReferralTable tenants={tenants} />
          </div>
        </>
      )}
    </div>
  );
}
