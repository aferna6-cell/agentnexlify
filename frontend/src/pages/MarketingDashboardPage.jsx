import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { BASE } from "../utils/api/_client";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

const inputStyle = {
  width: "100%",
  padding: "10px 14px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--bg-primary)",
  color: "var(--text-primary)",
  fontSize: "0.9rem",
  boxSizing: "border-box",
};

const btnPrimary = {
  background: "var(--accent)",
  color: "#fff",
  border: "none",
  padding: "10px 20px",
  borderRadius: 8,
  fontWeight: 600,
  cursor: "pointer",
  fontSize: "0.9rem",
};

const COLORS = [
  "var(--accent)",
  "var(--green)",
  "var(--purple, #8b5cf6)",
  "var(--yellow, #f59e0b)",
  "#f87171",
];

const API_BASE = `${BASE}/api/v1`;

async function apiFetch(path, token, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...opts.headers,
    },
    ...opts,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

export default function MarketingDashboardPage() {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total_campaigns: 0,
    total_sent: 0,
    avg_open_rate: null,
    avg_click_rate: null,
  });
  const [trends, setTrends] = useState([]);
  const [topCampaigns, setTopCampaigns] = useState([]);
  const [breakdown, setBreakdown] = useState([]);
  const [period, setPeriod] = useState("30d");

  const loadData = useCallback(async () => {
    if (!user?.tenantId || !token) return;
    setLoading(true);
    try {
      const [dashRes, trendsRes] = await Promise.all([
        apiFetch(`/marketing/${user.tenantId}/dashboard`, token).catch(
          () => null,
        ),
        apiFetch(
          `/marketing/${user.tenantId}/trends?period=${period}`,
          token,
        ).catch(() => null),
      ]);

      if (dashRes) {
        setStats({
          total_campaigns: dashRes.total_campaigns || 0,
          total_sent: dashRes.campaigns_sent || 0,
          avg_open_rate: dashRes.avg_open_rate ?? null,
          avg_click_rate: dashRes.avg_click_rate ?? null,
        });
        if (dashRes.top_performing_campaign) {
          setTopCampaigns(
            Array.isArray(dashRes.top_performing_campaign)
              ? dashRes.top_performing_campaign
              : [dashRes.top_performing_campaign],
          );
        }
        if (dashRes.email_vs_sms_breakdown) {
          // Backend returns a plain dict {email: N, sms: N} — convert to array for Recharts
          const raw = dashRes.email_vs_sms_breakdown;
          setBreakdown(
            Array.isArray(raw)
              ? raw
              : Object.entries(raw).map(([type, count]) => ({ type, count })),
          );
        }
      }
      // Backend key is "trends" not "trend_data"
      if (trendsRes?.trends) {
        setTrends(trendsRes.trends);
      } else if (trendsRes?.trend_data) {
        setTrends(trendsRes.trend_data);
      } else if (trendsRes && Array.isArray(trendsRes)) {
        setTrends(trendsRes);
      }
    } catch {
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, period]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openRate =
    stats.avg_open_rate != null ? `${stats.avg_open_rate.toFixed(1)}%` : "--";
  const clickRate =
    stats.avg_click_rate != null ? `${stats.avg_click_rate.toFixed(1)}%` : "--";

  const pieData = breakdown.map((b) => ({
    name: b.type || b.label || "Unknown",
    value: b.count || b.value || 0,
  }));

  if (loading) return <SkeletonLoader />;

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1400 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 24,
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              margin: 0,
              color: "var(--text-primary)",
            }}
          >
            Marketing Dashboard
          </h1>
          <p
            style={{
              color: "var(--text-secondary)",
              margin: "4px 0 0",
              fontSize: "0.9rem",
            }}
          >
            Campaign performance overview and trends
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {["30d", "90d"].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              style={{
                padding: "6px 16px",
                borderRadius: 8,
                cursor: "pointer",
                fontSize: "0.85rem",
                border:
                  period === p
                    ? "2px solid var(--accent)"
                    : "1px solid var(--border)",
                background:
                  period === p ? "var(--accent-dim)" : "var(--bg-primary)",
                color: period === p ? "var(--accent)" : "var(--text-secondary)",
                fontWeight: period === p ? 600 : 400,
              }}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Overview Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 16,
          marginBottom: 24,
        }}
      >
        {[
          {
            label: "Total Campaigns",
            value: stats.total_campaigns,
            color: "var(--accent)",
          },
          {
            label: "Total Sent",
            value: stats.total_sent.toLocaleString(),
            color: "var(--green)",
          },
          {
            label: "Avg Open Rate",
            value: openRate,
            color: "var(--purple, #8b5cf6)",
          },
          {
            label: "Avg Click Rate",
            value: clickRate,
            color: "var(--yellow, #f59e0b)",
          },
        ].map((s) => (
          <div key={s.label} style={cardStyle}>
            <div
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                marginBottom: 4,
              }}
            >
              {s.label}
            </div>
            <div
              style={{ fontSize: "1.5rem", fontWeight: 700, color: s.color }}
            >
              {s.value}
            </div>
          </div>
        ))}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 320px",
          gap: 16,
          marginBottom: 24,
        }}
      >
        {/* Trend Chart */}
        <div style={cardStyle}>
          <h3
            style={{
              margin: "0 0 16px",
              fontSize: "1rem",
              color: "var(--text-primary)",
            }}
          >
            Open & Click Rate Trends
          </h3>
          {trends.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `${v.toFixed(0)}%`}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    color: "var(--text-primary)",
                  }}
                  formatter={(v) => [`${v.toFixed(1)}%`]}
                />
                <Legend
                  wrapperStyle={{
                    color: "var(--text-secondary)",
                    fontSize: "0.8rem",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="open_rate"
                  stroke="var(--accent)"
                  strokeWidth={2}
                  dot={false}
                  name="Open Rate"
                />
                <Line
                  type="monotone"
                  dataKey="click_rate"
                  stroke="var(--green)"
                  strokeWidth={2}
                  dot={false}
                  name="Click Rate"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div
              style={{
                textAlign: "center",
                padding: 60,
                color: "var(--text-secondary)",
              }}
            >
              No trend data available yet
            </div>
          )}
        </div>

        {/* Email vs SMS Breakdown */}
        <div style={cardStyle}>
          <h3
            style={{
              margin: "0 0 16px",
              fontSize: "1rem",
              color: "var(--text-primary)",
            }}
          >
            Email vs SMS
          </h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    color: "var(--text-primary)",
                  }}
                />
                <Legend
                  wrapperStyle={{
                    color: "var(--text-secondary)",
                    fontSize: "0.8rem",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div
              style={{
                textAlign: "center",
                padding: 60,
                color: "var(--text-secondary)",
              }}
            >
              No breakdown data available
            </div>
          )}
        </div>
      </div>

      {/* Top Campaigns Table */}
      <div style={cardStyle}>
        <h3
          style={{
            margin: "0 0 16px",
            fontSize: "1rem",
            color: "var(--text-primary)",
          }}
        >
          Top Campaigns by Open Rate
        </h3>
        {topCampaigns.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "separate",
                borderSpacing: 0,
              }}
            >
              <thead>
                <tr>
                  {[
                    "Campaign",
                    "Type",
                    "Sent",
                    "Open Rate",
                    "Click Rate",
                    "Sent Date",
                  ].map((h) => (
                    <th
                      key={h}
                      style={{
                        textAlign: "left",
                        padding: "10px 16px",
                        fontSize: "0.75rem",
                        color: "var(--text-muted)",
                        fontWeight: 600,
                        borderBottom: "1px solid var(--border)",
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {topCampaigns.slice(0, 5).map((c, i) => (
                  <tr
                    key={c.id || i}
                    style={{ transition: "background 0.15s" }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.background =
                        "var(--hover-overlay)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background = "transparent")
                    }
                  >
                    <td
                      style={{
                        padding: "12px 16px",
                        color: "var(--text-primary)",
                        fontWeight: 600,
                      }}
                    >
                      {c.name || "Untitled"}
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <span
                        style={{
                          padding: "2px 10px",
                          borderRadius: 12,
                          fontSize: "0.75rem",
                          fontWeight: 600,
                          color:
                            c.type === "email"
                              ? "var(--accent)"
                              : "var(--green)",
                          background:
                            c.type === "email"
                              ? "var(--accent-dim)"
                              : "var(--green-dim)",
                        }}
                      >
                        {c.type?.toUpperCase() || "EMAIL"}
                      </span>
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {c.total_sent?.toLocaleString() ?? "--"}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        color: "var(--accent)",
                        fontWeight: 600,
                      }}
                    >
                      {c.open_rate != null
                        ? `${c.open_rate.toFixed(1)}%`
                        : "--"}
                    </td>
                    <td style={{ padding: "12px 16px", color: "var(--green)" }}>
                      {c.click_rate != null
                        ? `${c.click_rate.toFixed(1)}%`
                        : "--"}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        fontSize: "0.85rem",
                        color: "var(--text-muted)",
                      }}
                    >
                      {c.sent_at
                        ? new Date(c.sent_at).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          })
                        : "--"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div
            style={{
              textAlign: "center",
              padding: "40px 20px",
              color: "var(--text-secondary)",
            }}
          >
            No campaign data available yet
          </div>
        )}
      </div>
    </div>
  );
}
