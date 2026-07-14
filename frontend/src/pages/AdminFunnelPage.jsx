import { useState, useEffect, useCallback } from "react";
import { BASE } from "../utils/api/_client";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

// ---------------------------------------------------------------------------
// Admin-secret pattern - identical to AdminAnalyticsPage + AdminHealthPage.
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
// Styling helpers - match existing admin pages
// ---------------------------------------------------------------------------
const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

// Funnel step colours: each stage gets progressively more "earned"
const FUNNEL_COLORS = ["#6366f1", "#8b5cf6", "#f59e0b", "#10b981"];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatCard({ label, value, sub }) {
  return (
    <div style={cardStyle}>
      <div
        style={{
          fontSize: "0.75rem",
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "2rem",
          fontWeight: 700,
          color: "var(--text-primary, #f1f5f9)",
          lineHeight: 1,
        }}
      >
        {value ?? "-"}
      </div>
      {sub && (
        <div
          style={{
            fontSize: "0.75rem",
            color: "var(--text-muted)",
            marginTop: 6,
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

function ErrorList({ errors }) {
  if (!errors || errors.length === 0) return null;
  return (
    <div
      style={{
        ...cardStyle,
        borderColor: "#f87171",
        background: "rgba(239,68,68,0.08)",
      }}
    >
      <div
        style={{
          fontSize: "0.85rem",
          fontWeight: 600,
          color: "#f87171",
          marginBottom: 10,
        }}
      >
        Partial data - {errors.length} metric{errors.length > 1 ? "s" : ""} failed
      </div>
      <ul style={{ margin: 0, paddingLeft: 16 }}>
        {errors.map((e, i) => (
          <li
            key={i}
            style={{
              fontSize: "0.8rem",
              color: "var(--text-muted)",
              marginBottom: 4,
            }}
          >
            {e}
          </li>
        ))}
      </ul>
    </div>
  );
}

function FunnelChart({ data }) {
  const max = data[0]?.value || 1;

  return (
    <div style={{ ...cardStyle, gridColumn: "1 / -1" }}>
      <h3
        style={{
          margin: "0 0 20px",
          fontSize: "1rem",
          fontWeight: 600,
          color: "var(--text-primary, #f1f5f9)",
        }}
      >
        Signup → Activation → Lead → Paid
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart
          data={data}
          margin={{ top: 8, right: 16, left: 0, bottom: 4 }}
          layout="vertical"
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--border, #374151)"
            horizontal={false}
          />
          <XAxis
            type="number"
            tick={{ fill: "var(--text-muted, #9ca3af)", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={110}
            tick={{ fill: "var(--text-muted, #9ca3af)", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "var(--bg-secondary, #1e2030)",
              border: "1px solid var(--border, #374151)",
              borderRadius: 8,
              color: "var(--text-primary, #f1f5f9)",
              fontSize: "0.85rem",
            }}
            formatter={(value, name, props) => {
              const pct =
                max > 0 ? ((value / max) * 100).toFixed(1) : "0.0";
              return [`${value} (${pct}% of signups)`, props.payload.name];
            }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell key={entry.name} fill={FUNNEL_COLORS[index % FUNNEL_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {/* Conversion labels */}
      <div
        style={{
          display: "flex",
          gap: 24,
          marginTop: 16,
          flexWrap: "wrap",
        }}
      >
        {data.map((step, i) => {
          const pct =
            max > 0 ? ((step.value / max) * 100).toFixed(1) : "0.0";
          return (
            <div key={step.name} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 2,
                  background: FUNNEL_COLORS[i % FUNNEL_COLORS.length],
                  display: "inline-block",
                  flexShrink: 0,
                }}
              />
              <span
                style={{ fontSize: "0.8rem", color: "var(--text-muted, #9ca3af)" }}
              >
                {step.name}: {step.value} ({pct}%)
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function WeeklyCard({ label, value, color }) {
  return (
    <div
      style={{
        ...cardStyle,
        borderTop: `3px solid ${color}`,
      }}
    >
      <div
        style={{
          fontSize: "0.75rem",
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "2.2rem",
          fontWeight: 700,
          color: color,
          lineHeight: 1,
        }}
      >
        {value ?? "-"}
      </div>
      <div
        style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 6 }}
      >
        last 7 days
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function AdminFunnelPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch("/product-funnel");
      setData(result);
    } catch (err) {
      setError(err.message || "Failed to load funnel data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Build the ordered funnel array for the chart
  const funnelSteps = data
    ? [
        { name: "Signed Up", value: data.total_tenants ?? 0 },
        { name: "Activated", value: data.activated ?? 0 },
        { name: "Has Leads", value: data.with_leads ?? 0 },
        { name: "Booked", value: data.with_appointments ?? 0 },
        { name: "Paid", value: data.paid ?? 0 },
        { name: "Retained 30d+", value: data.retained_30d ?? 0 },
      ]
    : [];

  // Derived conversion rates (only when data present)
  function convRate(num, denom) {
    if (!denom) return "-";
    return `${((num / denom) * 100).toFixed(1)}%`;
  }

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
            Product Funnel
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
          {loading ? "Refreshing…" : "Refresh"}
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

      {/* Loading skeleton */}
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
          Loading funnel data…
        </div>
      )}

      {/* Empty state - backend returned zeros across the board */}
      {!loading && data && data.total_tenants === 0 && (
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
            No tenant data yet
          </div>
          <p style={{ fontSize: "0.85rem", margin: 0, maxWidth: 400, marginInline: "auto" }}>
            The funnel will populate once tenants start signing up. Data is
            best-effort - check the errors list if metrics look incorrect.
          </p>
        </div>
      )}

      {/* Main content */}
      {!loading && data && data.total_tenants > 0 && (
        <>
          {/* Partial-data errors (best-effort endpoint) */}
          {data.errors && data.errors.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <ErrorList errors={data.errors} />
            </div>
          )}

          {/* Funnel chart */}
          <div style={{ marginBottom: 24 }}>
            <FunnelChart data={funnelSteps} />
          </div>

          {/* Top-line stat cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 16,
              marginBottom: 24,
            }}
          >
            <StatCard
              label="Signed Up"
              value={data.total_tenants}
              sub="all-time"
            />
            <StatCard
              label="Activated"
              value={data.activated}
              sub={convRate(data.activated, data.total_tenants) + " of signups"}
            />
            <StatCard
              label="Has Leads"
              value={data.with_leads}
              sub={convRate(data.with_leads, data.activated) + " of activated"}
            />
            <StatCard
              label="Booked"
              value={data.with_appointments ?? 0}
              sub={convRate(data.with_appointments ?? 0, data.with_leads) + " of has-leads"}
            />
            <StatCard
              label="Paid"
              value={data.paid}
              sub={convRate(data.paid, data.total_tenants) + " of signups"}
            />
            <StatCard
              label="Retained 30d+"
              value={data.retained_30d ?? 0}
              sub={convRate(data.retained_30d ?? 0, data.paid) + " of paid"}
            />
          </div>

          {/* Weekly counters */}
          <h2
            style={{
              margin: "0 0 16px",
              fontSize: "1rem",
              fontWeight: 600,
              color: "var(--text-secondary, #94a3b8)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            Last 7 Days
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 16,
            }}
          >
            <WeeklyCard
              label="New Signups"
              value={data.new_signups_week}
              color="#6366f1"
            />
            <WeeklyCard
              label="New Leads"
              value={data.new_leads_week}
              color="#f59e0b"
            />
            <WeeklyCard
              label="New Appointments"
              value={data.new_appointments_week}
              color="#10b981"
            />
          </div>
        </>
      )}
    </div>
  );
}
