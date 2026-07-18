import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchAttribution } from "../utils/api/analytics";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// ---------------------------------------------------------------------------
// AttributionPage - GH #453. Visualizes leads.attribution (migration 172):
// which channel, medium, and campaign each captured lead came from. Data has
// been captured on every widget lead since the migration; this page is the
// first surface that shows it.
// ---------------------------------------------------------------------------

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

function BreakdownChart({ title, data }) {
  const rows = (data || []).slice(0, 8);
  return (
    <div style={cardStyle}>
      <h3
        style={{
          margin: "0 0 16px",
          fontSize: "1rem",
          fontWeight: 600,
          color: "var(--text-primary, #f1f5f9)",
        }}
      >
        {title}
      </h3>
      {rows.length === 0 ? (
        <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
          No data yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={Math.max(160, rows.length * 36)}>
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border, #374151)"
              horizontal={false}
            />
            <XAxis
              type="number"
              allowDecimals={false}
              tick={{ fill: "var(--text-muted, #9ca3af)", fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={120}
              tick={{ fill: "var(--text-muted, #9ca3af)", fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              cursor={{ fill: "rgba(99,102,241,0.08)" }}
              contentStyle={{
                background: "var(--bg-secondary, #1f2937)",
                border: "1px solid var(--border, #374151)",
                borderRadius: 8,
              }}
            />
            <Bar dataKey="count" fill="#6366f1" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function BreakdownTable({ data }) {
  const rows = data?.by_campaign || [];
  return (
    <div style={{ ...cardStyle, gridColumn: "1 / -1" }}>
      <h3
        style={{
          margin: "0 0 14px",
          fontSize: "1rem",
          fontWeight: 600,
          color: "var(--text-primary, #f1f5f9)",
        }}
      >
        Campaigns
      </h3>
      {rows.length === 0 ? (
        <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
          No campaign data yet
        </div>
      ) : (
        <table style={{ width: "100%", fontSize: "0.85rem" }}>
          <thead>
            <tr>
              <th
                style={{
                  textAlign: "left",
                  color: "var(--text-muted)",
                  fontWeight: 500,
                  paddingBottom: 8,
                }}
              >
                Campaign
              </th>
              <th
                style={{
                  textAlign: "right",
                  color: "var(--text-muted)",
                  fontWeight: 500,
                  paddingBottom: 8,
                }}
              >
                Leads
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.name}>
                <td
                  style={{
                    padding: "6px 0",
                    color: "var(--text-primary, #f1f5f9)",
                  }}
                >
                  {row.name}
                </td>
                <td style={{ textAlign: "right", fontWeight: 600 }}>
                  {row.count}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function AttributionPage() {
  const { user, token } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchAttribution(user.tenantId, token);
      setData(payload);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div style={{ padding: 32, color: "var(--text-muted)" }}>
        Loading attribution...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 32 }}>
        <div style={{ ...cardStyle, borderColor: "#f87171" }}>
          <div style={{ color: "#f87171", fontWeight: 600, marginBottom: 8 }}>
            Failed to load attribution
          </div>
          <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
            {error}
          </div>
          <button
            className="btn-secondary"
            style={{ marginTop: 14 }}
            onClick={load}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const total = data?.total ?? 0;
  const attributed = data?.attributed ?? 0;

  if (total === 0) {
    return (
      <div style={{ padding: 32 }}>
        <h2 style={{ margin: "0 0 8px", color: "var(--text-primary, #f1f5f9)" }}>
          Lead Attribution
        </h2>
        <div style={cardStyle}>
          <div style={{ color: "var(--text-primary, #f1f5f9)", fontWeight: 600 }}>
            No leads yet
          </div>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", margin: "8px 0 0" }}>
            Once your widget captures leads, this page shows which channel,
            medium, and campaign each one came from. Add utm_source,
            utm_medium, and utm_campaign parameters to your ad and social
            links so they are attributed automatically.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: 32, display: "grid", gap: 20 }}>
      <div>
        <h2
          style={{
            margin: 0,
            color: "var(--text-primary, #f1f5f9)",
            fontSize: "1.4rem",
          }}
        >
          Lead Attribution
        </h2>
        <div
          style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4 }}
        >
          {attributed} of {total} lead{total === 1 ? "" : "s"} attributed ·
          unattributed leads show as (none) · add utm_ parameters to your
          links to improve coverage
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: 16,
        }}
      >
        <BreakdownChart title="Leads by source" data={data?.by_source} />
        <BreakdownChart title="Leads by medium" data={data?.by_medium} />
        <BreakdownTable data={data} />
      </div>
    </div>
  );
}
