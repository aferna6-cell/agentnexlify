import { useState, useEffect, useCallback } from "react";
import { BASE } from "../utils/api/_client";

// ---------------------------------------------------------------------------
// Admin-secret pattern — identical to AdminFunnelPage + AdminAnalyticsPage.
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
  const res = await fetch(`${BASE}/api/v1/admin${path}`, {
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

// Status pill config
const STATUS_CONFIG = {
  active: { label: "Active", color: "#10b981", bg: "rgba(16,185,129,0.12)" },
  at_risk: { label: "At Risk", color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
  dormant: { label: "Dormant", color: "#f87171", bg: "rgba(248,113,113,0.12)" },
};

// Sort order: dormant paid first (hottest call list), then at_risk paid,
// then at_risk free, then dormant free, then active.
function sortTenants(tenants) {
  const priority = (t) => {
    const paid = t.is_paid;
    const s = t.status;
    if (s === "dormant" && paid) return 0;
    if (s === "at_risk" && paid) return 1;
    if (s === "dormant" && !paid) return 2;
    if (s === "at_risk" && !paid) return 3;
    return 4; // active
  };
  return [...tenants].sort((a, b) => priority(a) - priority(b));
}

function formatDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusPill({ status }) {
  const cfg = STATUS_CONFIG[status] || {
    label: status,
    color: "var(--text-muted)",
    bg: "rgba(255,255,255,0.06)",
  };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 10px",
        borderRadius: 99,
        fontSize: "0.75rem",
        fontWeight: 600,
        color: cfg.color,
        background: cfg.bg,
        letterSpacing: "0.02em",
        whiteSpace: "nowrap",
      }}
    >
      {cfg.label}
    </span>
  );
}

function PaidBadge({ isPaid }) {
  if (isPaid) {
    return (
      <span
        style={{
          display: "inline-block",
          padding: "2px 8px",
          borderRadius: 99,
          fontSize: "0.72rem",
          fontWeight: 700,
          color: "#6366f1",
          background: "rgba(99,102,241,0.12)",
          letterSpacing: "0.02em",
        }}
      >
        Paid
      </span>
    );
  }
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 99,
        fontSize: "0.72rem",
        fontWeight: 600,
        color: "var(--text-muted, #9ca3af)",
        background: "rgba(255,255,255,0.05)",
        letterSpacing: "0.02em",
      }}
    >
      Free
    </span>
  );
}

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

function SortIcon({ dir }) {
  if (!dir) {
    return (
      <span style={{ opacity: 0.3, marginLeft: 4, fontSize: "0.65rem" }}>
        ▲▼
      </span>
    );
  }
  return (
    <span style={{ marginLeft: 4, fontSize: "0.65rem", color: "#6366f1" }}>
      {dir === "asc" ? "▲" : "▼"}
    </span>
  );
}

const COLUMNS = [
  { key: "business_name", label: "Business", align: "left", sortable: true },
  { key: "plan", label: "Plan", align: "left", sortable: true },
  { key: "paid", label: "Paid", align: "left", sortable: true },
  { key: "status", label: "Status", align: "left", sortable: true },
  { key: "total_messages", label: "Msgs Total", align: "right", sortable: true },
  { key: "total_leads", label: "Leads Total", align: "right", sortable: true },
  { key: "total_appointments", label: "Appts Total", align: "right", sortable: true },
  { key: "messages_last_7d", label: "Msgs 7d", align: "right", sortable: true },
  { key: "leads_last_7d", label: "Leads 7d", align: "right", sortable: true },
  { key: "last_activity_at", label: "Last Activity", align: "left", sortable: true },
];

function TenantTable({ tenants }) {
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState("asc");

  function handleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  // Apply sort on top of the default priority ordering
  const sorted = (() => {
    const base = sortTenants(tenants);
    if (!sortKey) return base;
    return [...base].sort((a, b) => {
      let av = a[sortKey === "paid" ? "is_paid" : sortKey];
      let bv = b[sortKey === "paid" ? "is_paid" : sortKey];
      // Nulls last
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      if (typeof av === "string") av = av.toLowerCase();
      if (typeof bv === "string") bv = bv.toLowerCase();
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
  })();

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
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                style={{
                  ...TH_STYLE,
                  textAlign: col.align || "left",
                  cursor: col.sortable ? "pointer" : "default",
                  userSelect: "none",
                }}
                onClick={col.sortable ? () => handleSort(col.key) : undefined}
              >
                {col.label}
                {col.sortable && (
                  <SortIcon
                    dir={sortKey === col.key ? sortDir : null}
                  />
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((t) => (
            <tr
              key={t.tenant_id}
              style={{
                background:
                  t.status === "dormant" && t.is_paid
                    ? "rgba(248,113,113,0.04)"
                    : t.status === "at_risk" && t.is_paid
                    ? "rgba(245,158,11,0.04)"
                    : "transparent",
              }}
            >
              <td style={TD_STYLE}>
                <span style={{ fontWeight: 600 }}>
                  {t.business_name || "—"}
                </span>
              </td>
              <td style={TD_STYLE}>
                <span
                  style={{
                    fontSize: "0.78rem",
                    color: "var(--text-secondary, #94a3b8)",
                    fontFamily: "monospace",
                  }}
                >
                  {t.plan || "—"}
                </span>
              </td>
              <td style={TD_STYLE}>
                <PaidBadge isPaid={t.is_paid} />
              </td>
              <td style={TD_STYLE}>
                <StatusPill status={t.status} />
              </td>
              <td style={NUM_TD}>{t.total_messages ?? "—"}</td>
              <td style={NUM_TD}>{t.total_leads ?? "—"}</td>
              <td style={NUM_TD}>{t.total_appointments ?? "—"}</td>
              <td
                style={{
                  ...NUM_TD,
                  color:
                    t.messages_last_7d > 0
                      ? "var(--text-primary, #f1f5f9)"
                      : "var(--text-muted, #9ca3af)",
                  fontWeight: t.messages_last_7d > 0 ? 600 : 400,
                }}
              >
                {t.messages_last_7d ?? "—"}
              </td>
              <td
                style={{
                  ...NUM_TD,
                  color:
                    t.leads_last_7d > 0
                      ? "var(--text-primary, #f1f5f9)"
                      : "var(--text-muted, #9ca3af)",
                  fontWeight: t.leads_last_7d > 0 ? 600 : 400,
                }}
              >
                {t.leads_last_7d ?? "—"}
              </td>
              <td
                style={{
                  ...TD_STYLE,
                  color: "var(--text-muted, #9ca3af)",
                  fontSize: "0.78rem",
                }}
              >
                {formatDate(t.last_activity_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SummaryBar({ tenants }) {
  const total = tenants.length;
  const paid = tenants.filter((t) => t.is_paid).length;
  const active = tenants.filter((t) => t.status === "active").length;
  const atRisk = tenants.filter((t) => t.status === "at_risk").length;
  const dormant = tenants.filter((t) => t.status === "dormant").length;
  const dormantPaid = tenants.filter(
    (t) => t.status === "dormant" && t.is_paid,
  ).length;

  const cards = [
    { label: "Total Tenants", value: total, color: "var(--text-primary, #f1f5f9)" },
    { label: "Paid", value: paid, color: "#6366f1" },
    { label: "Active", value: active, color: "#10b981" },
    { label: "At Risk", value: atRisk, color: "#f59e0b" },
    { label: "Dormant", value: dormant, color: "#f87171" },
    {
      label: "Dormant + Paid",
      value: dormantPaid,
      color: "#ef4444",
      sub: "Call list",
    },
  ];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
        gap: 12,
        marginBottom: 24,
      }}
    >
      {cards.map((c) => (
        <div key={c.label} style={cardStyle}>
          <div
            style={{
              fontSize: "0.7rem",
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: 6,
            }}
          >
            {c.label}
          </div>
          <div
            style={{
              fontSize: "1.75rem",
              fontWeight: 700,
              color: c.color,
              lineHeight: 1,
            }}
          >
            {c.value}
          </div>
          {c.sub && (
            <div
              style={{
                fontSize: "0.7rem",
                color: "var(--text-muted)",
                marginTop: 4,
              }}
            >
              {c.sub}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function AdminTenantHealthPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch("/tenant-health");
      setData(result);
    } catch (err) {
      setError(err.message || "Failed to load tenant health data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const tenants = data?.tenants ?? [];

  return (
    <div
      style={{
        padding: "32px 32px 64px",
        maxWidth: 1300,
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
            Tenant Health
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
          Loading tenant health data...
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
            No tenants found
          </div>
          <p
            style={{
              fontSize: "0.85rem",
              margin: 0,
              maxWidth: 400,
              marginInline: "auto",
            }}
          >
            The tenant health table will populate once tenants exist in the
            system. Health status (active / at_risk / dormant) is computed from
            message and lead activity over the last 7 days.
          </p>
        </div>
      )}

      {/* Main content */}
      {!loading && data && tenants.length > 0 && (
        <>
          {/* Summary stat bar */}
          <SummaryBar tenants={tenants} />

          {/* Call list callout */}
          {tenants.filter((t) => t.status === "dormant" && t.is_paid).length >
            0 && (
            <div
              style={{
                ...cardStyle,
                borderColor: "#ef4444",
                background: "rgba(239,68,68,0.06)",
                marginBottom: 20,
                display: "flex",
                alignItems: "center",
                gap: 14,
                flexWrap: "wrap",
              }}
            >
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "#ef4444",
                  flexShrink: 0,
                }}
              />
              <div>
                <span
                  style={{
                    fontSize: "0.85rem",
                    fontWeight: 600,
                    color: "#f87171",
                  }}
                >
                  {
                    tenants.filter(
                      (t) => t.status === "dormant" && t.is_paid,
                    ).length
                  }{" "}
                  paying tenant
                  {tenants.filter(
                    (t) => t.status === "dormant" && t.is_paid,
                  ).length > 1
                    ? "s are"
                    : " is"}{" "}
                  dormant
                </span>
                <span
                  style={{
                    fontSize: "0.82rem",
                    color: "var(--text-muted)",
                    marginLeft: 8,
                  }}
                >
                  — these surface first in the table below. Call or email before
                  they churn.
                </span>
              </div>
            </div>
          )}

          {/* Table */}
          <div style={cardStyle}>
            <TenantTable tenants={tenants} />
          </div>
        </>
      )}
    </div>
  );
}
