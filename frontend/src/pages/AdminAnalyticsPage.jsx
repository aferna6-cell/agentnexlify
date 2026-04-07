import { useState, useEffect, useCallback } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  AreaChart,
  Area,
} from "recharts";

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

const PLAN_LABELS = {
  free: "Free",
  growth: "Growth",
  professional: "Professional",
  autopilot: "Autopilot",
  enterprise: "Enterprise",
};

const PLAN_COLORS = {
  free: "var(--green)",
  growth: "var(--accent)",
  professional: "var(--purple, #8b5cf6)",
  autopilot: "var(--yellow, #f59e0b)",
  enterprise: "#f87171",
};

const PIE_COLORS = [
  "var(--accent)",
  "var(--green)",
  "var(--purple, #8b5cf6)",
  "var(--yellow, #f59e0b)",
  "var(--green)",
  "#f87171",
];

// Admin secret is entered at runtime via prompt — never baked into the JS bundle.
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
  const res = await fetch(`/api/v1/admin${path}`, {
    headers: {
      "x-api-secret": secret,
      "Content-Type": "application/json",
    },
  });
  if (res.status === 401) {
    clearAdminSecret();
    throw new Error("Invalid admin secret — cleared. Refresh to retry.");
  }
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

function formatCurrency(cents) {
  return `$${(cents / 100).toLocaleString("en-US", { minimumFractionDigits: 0 })}`;
}

function formatDollars(amount) {
  return `$${Number(amount || 0).toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
}

export default function AdminAnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState(null);
  const [weeklyGrowth, setWeeklyGrowth] = useState(null);
  const [monthlyGrowth, setMonthlyGrowth] = useState([]);
  const [planDist, setPlanDist] = useState([]);
  const [revenueTrends, setRevenueTrends] = useState([]);
  const [industryBreakdown, setIndustryBreakdown] = useState([]);
  const [months, setMonths] = useState(12);

  const loadData = useCallback(async () => {
    if (!getAdminSecret()) return;
    setLoading(true);
    try {
      const [
        overviewRes,
        weeklyRes,
        growthRes,
        distRes,
        revenueRes,
        industryRes,
      ] = await Promise.all([
        apiFetch("/overview").catch(() => null),
        apiFetch("/weekly-growth").catch(() => null),
        apiFetch(`/monthly-growth?months=${months}`).catch(() => null),
        apiFetch("/plan-distribution").catch(() => null),
        apiFetch(`/revenue-trends?months=${months}`).catch(() => null),
        apiFetch("/industry-breakdown").catch(() => null),
      ]);

      if (overviewRes) setOverview(overviewRes);
      if (weeklyRes) setWeeklyGrowth(weeklyRes);
      if (growthRes?.monthly_data) setMonthlyGrowth(growthRes.monthly_data);
      if (distRes?.distribution) setPlanDist(distRes.distribution);
      if (revenueRes?.revenue_trends)
        setRevenueTrends(revenueRes.revenue_trends);
      if (industryRes?.breakdown) setIndustryBreakdown(industryRes.breakdown);
    } catch (err) {
      console.error("Admin analytics load failed:", err.message);
    } finally {
      setLoading(false);
    }
  }, [months]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (!_adminSecret) {
    return (
      <div style={{ padding: "24px 32px", maxWidth: 1400 }}>
        <div
          style={{ ...cardStyle, textAlign: "center", padding: "60px 20px" }}
        >
          <h2 style={{ color: "var(--text-primary)" }}>
            Admin Access Required
          </h2>
          <p style={{ color: "var(--text-secondary)" }}>
            Refresh the page and enter the admin secret when prompted.
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ padding: "24px 32px", maxWidth: 1400 }}>
        <div
          style={{
            ...cardStyle,
            textAlign: "center",
            padding: "40px",
            color: "var(--text-secondary)",
          }}
        >
          Loading platform analytics...
        </div>
      </div>
    );
  }

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
            Platform Analytics
          </h1>
          <p
            style={{
              color: "var(--text-secondary)",
              margin: "4px 0 0",
              fontSize: "0.9rem",
            }}
          >
            Cross-tenant growth, revenue, and plan distribution
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {[6, 12, 24].map((m) => (
            <button
              key={m}
              onClick={() => setMonths(m)}
              style={{
                padding: "6px 16px",
                borderRadius: 8,
                cursor: "pointer",
                fontSize: "0.85rem",
                border:
                  months === m
                    ? "2px solid var(--accent)"
                    : "1px solid var(--border)",
                background:
                  months === m ? "var(--accent-dim)" : "var(--bg-primary)",
                color: months === m ? "var(--accent)" : "var(--text-secondary)",
                fontWeight: months === m ? 600 : 400,
              }}
            >
              {m}m
            </button>
          ))}
        </div>
      </div>

      {/* Overview Cards */}
      {overview && (
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
              label: "Total Businesses",
              value: overview.total_tenants,
              sub: `${overview.active_paid_subscriptions} paying`,
            },
            {
              label: "MRR",
              value: formatCurrency(overview.mrr_cents),
              sub: "Monthly recurring revenue",
            },
            {
              label: "New This Month",
              value: overview.new_signups_this_month,
              sub: `${overview.churned_this_month} churned`,
            },
            {
              label: "Free Trials",
              value: overview.free_trial_active,
              sub: `${overview.promoted_business} promoted`,
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
                style={{
                  fontSize: "1.5rem",
                  fontWeight: 700,
                  color: "var(--accent)",
                }}
              >
                {s.value}
              </div>
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "var(--text-muted)",
                  marginTop: 2,
                }}
              >
                {s.sub}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Weekly Growth Quick View */}
      {weeklyGrowth && (
        <div style={{ ...cardStyle, marginBottom: 24 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 16,
            }}
          >
            <h3
              style={{
                margin: 0,
                fontSize: "1rem",
                color: "var(--text-primary)",
              }}
            >
              This Week
            </h3>
            {weeklyGrowth.week_delta !== 0 && (
              <span
                style={{
                  fontSize: "0.85rem",
                  fontWeight: 600,
                  color:
                    weeklyGrowth.week_delta > 0 ? "var(--green)" : "#f87171",
                  background:
                    weeklyGrowth.week_delta > 0
                      ? "var(--green-dim)"
                      : "rgba(248,113,113,0.15)",
                  padding: "2px 10px",
                  borderRadius: 8,
                }}
              >
                {weeklyGrowth.week_delta > 0 ? "↑" : "↓"}{" "}
                {Math.abs(weeklyGrowth.week_delta)} (
                {weeklyGrowth.week_delta_pct > 0 ? "+" : ""}
                {weeklyGrowth.week_delta_pct}%)
              </span>
            )}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 16,
              marginBottom: 16,
            }}
          >
            {[
              {
                label: "New Signups",
                value: weeklyGrowth.this_week_signups,
                color: "var(--accent)",
              },
              {
                label: "New Paid",
                value: weeklyGrowth.this_week_paid,
                color: "var(--green)",
              },
              {
                label: "Weekly Revenue",
                value: formatCurrency(weeklyGrowth.this_week_revenue_cents),
                color: "var(--accent)",
              },
              {
                label: "Active Paid Subs",
                value: weeklyGrowth.active_paid_subscriptions,
                color: "var(--purple, #8b5cf6)",
              },
            ].map((s) => (
              <div key={s.label} style={{ textAlign: "center" }}>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-secondary)",
                    marginBottom: 4,
                  }}
                >
                  {s.label}
                </div>
                <div
                  style={{
                    fontSize: "1.2rem",
                    fontWeight: 700,
                    color: s.color,
                  }}
                >
                  {s.value}
                </div>
              </div>
            ))}
          </div>
          {weeklyGrowth.daily_data.length > 0 && (
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={weeklyGrowth.daily_data}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="label"
                  tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
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
                    fontSize: "0.75rem",
                  }}
                />
                <Bar
                  dataKey="paid"
                  fill="var(--green)"
                  radius={[3, 3, 0, 0]}
                  name="Paid"
                />
                <Bar
                  dataKey="free"
                  fill="var(--text-muted)"
                  radius={[3, 3, 0, 0]}
                  name="Free"
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 380px",
          gap: 16,
          marginBottom: 24,
        }}
      >
        {/* Monthly Growth Chart */}
        <div style={cardStyle}>
          <h3
            style={{
              margin: "0 0 16px",
              fontSize: "1rem",
              color: "var(--text-primary)",
            }}
          >
            Monthly Signups
          </h3>
          {monthlyGrowth.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={monthlyGrowth}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="month"
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
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
                <Area
                  type="monotone"
                  dataKey="new_signups"
                  stroke="var(--accent)"
                  fill="var(--accent-dim)"
                  strokeWidth={2}
                  name="New Signups"
                />
                <Area
                  type="monotone"
                  dataKey="new_paid"
                  stroke="var(--green)"
                  fill="var(--green-dim)"
                  strokeWidth={2}
                  name="New Paid"
                />
                <Area
                  type="monotone"
                  dataKey="new_free"
                  stroke="var(--text-muted)"
                  fill="var(--hover-overlay)"
                  strokeWidth={2}
                  name="New Free"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div
              style={{
                textAlign: "center",
                padding: 60,
                color: "var(--text-secondary)",
              }}
            >
              No growth data yet
            </div>
          )}
        </div>

        {/* Plan Distribution */}
        <div style={cardStyle}>
          <h3
            style={{
              margin: "0 0 16px",
              fontSize: "1rem",
              color: "var(--text-primary)",
            }}
          >
            Plan Distribution
          </h3>
          {planDist.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={planDist}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="total"
                  >
                    {planDist.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
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
                </PieChart>
              </ResponsiveContainer>
              <div style={{ marginTop: 12 }}>
                {planDist.map((p) => (
                  <div
                    key={p.plan}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 6,
                      fontSize: "0.85rem",
                    }}
                  >
                    <span
                      style={{
                        color: PLAN_COLORS[p.plan] || "var(--text-primary)",
                        fontWeight: 600,
                      }}
                    >
                      {PLAN_LABELS[p.plan] || p.plan}
                    </span>
                    <span style={{ color: "var(--text-secondary)" }}>
                      {p.total} ({p.percentage}%)
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div
              style={{
                textAlign: "center",
                padding: 60,
                color: "var(--text-secondary)",
              }}
            >
              No plan data yet
            </div>
          )}
        </div>
      </div>

      {/* Revenue Trends */}
      <div style={{ ...cardStyle, marginBottom: 24 }}>
        <h3
          style={{
            margin: "0 0 16px",
            fontSize: "1rem",
            color: "var(--text-primary)",
          }}
        >
          Revenue Trends (MRR)
        </h3>
        {revenueTrends.length > 0 ? (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={revenueTrends}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis
                dataKey="month"
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => v?.slice(0, 7) || ""}
              />
              <YAxis
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => formatDollars(v)}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--bg-primary)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  color: "var(--text-primary)",
                }}
                formatter={(v, name) =>
                  name === "MRR ($)" ? formatDollars(v) : v
                }
              />
              <Legend
                wrapperStyle={{
                  color: "var(--text-secondary)",
                  fontSize: "0.8rem",
                }}
              />
              <Line
                type="monotone"
                dataKey="mrr_dollars"
                stroke="var(--accent)"
                strokeWidth={2}
                dot
                name="MRR ($)"
              />
              <Line
                type="monotone"
                dataKey="total_subscriptions"
                stroke="var(--green)"
                strokeWidth={2}
                dot
                name="Active Subscriptions"
                yAxisId="right"
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
            No revenue data yet. Subscribe tenants to see trends.
          </div>
        )}
      </div>

      {/* Industry Breakdown Table */}
      <div style={cardStyle}>
        <h3
          style={{
            margin: "0 0 16px",
            fontSize: "1rem",
            color: "var(--text-primary)",
          }}
        >
          Industry Breakdown
        </h3>
        {industryBreakdown.length > 0 ? (
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
                  {["Industry", "Total", "Paid", "Free", "Conversion %"].map(
                    (h) => (
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
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {industryBreakdown.map((ind) => (
                  <tr
                    key={ind.industry}
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
                        textTransform: "capitalize",
                      }}
                    >
                      {ind.industry}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {ind.total}
                    </td>
                    <td style={{ padding: "12px 16px", color: "var(--green)" }}>
                      {ind.paid}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        color: "var(--text-muted)",
                      }}
                    >
                      {ind.free}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        fontWeight: 600,
                        color:
                          ind.paid_percentage > 50
                            ? "var(--green)"
                            : "var(--accent)",
                      }}
                    >
                      {ind.paid_percentage}%
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
            No industry data available yet
          </div>
        )}
      </div>
    </div>
  );
}
