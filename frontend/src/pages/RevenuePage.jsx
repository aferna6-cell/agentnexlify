import { useState, useEffect, useCallback, useMemo } from "react";
import { useAuth } from "../context/AuthContext";
import {
  fetchRevenueOverview,
  fetchRevenueTrend,
  fetchTopCustomers,
  fetchRevenueBreakdown,
} from "../utils/api/revenue";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from "recharts";
import SkeletonLoader from "../components/SkeletonLoader";

const PERIODS = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
];

function formatCurrency(val) {
  if (val === undefined || val === null) return "$0";
  return "$" + Number(val).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function formatCurrencyExact(val) {
  if (val === undefined || val === null) return "$0.00";
  return "$" + Number(val).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function getChartTheme() {
  const s = getComputedStyle(document.documentElement);
  const v = (name) => s.getPropertyValue(name).trim();
  return {
    bg: v("--bg-card") || "#1a1a2e",
    grid: v("--border") || "#2a2a3e",
    text: v("--text-secondary") || "#8888aa",
    accent: v("--accent") || "#3b82f6",
    green: v("--green") || "#22c55e",
    purple: v("--purple") || "#8b5cf6",
    yellow: v("--yellow") || "#eab308",
    red: v("--red") || "#ef4444",
  };
}

function RevenueStatCard({ label, value, change, prefix = "$", suffix = "" }) {
  const isPositive = change > 0;
  const isNeutral = change === 0 || change === undefined;
  return (
    <div style={{
      background: "var(--bg-card)", border: "1px solid var(--border)",
      borderRadius: "12px", padding: "20px", flex: "1 1 0",
      minWidth: "180px",
    }}>
      <div style={{ color: "var(--text-secondary)", fontSize: "0.8rem", fontWeight: 500, marginBottom: "6px" }}>
        {label}
      </div>
      <div style={{ fontSize: "1.6rem", fontWeight: 700, color: "var(--text-primary)" }}>
        {prefix}{typeof value === "number" ? value.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 }) : value}{suffix}
      </div>
      {change !== undefined && (
        <div style={{
          fontSize: "0.75rem", marginTop: "4px", fontWeight: 500,
          color: isPositive ? "var(--green)" : isNeutral ? "var(--text-secondary)" : "var(--red)",
        }}>
          {isPositive ? "\u2191" : isNeutral ? "\u2014" : "\u2193"} {Math.abs(change)}% vs prev period
        </div>
      )}
    </div>
  );
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "var(--bg-card)", border: "1px solid var(--border)",
      borderRadius: "8px", padding: "10px 14px", fontSize: "0.8rem",
    }}>
      <div style={{ fontWeight: 600, marginBottom: "6px", color: "var(--text-primary)" }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, marginBottom: "2px" }}>
          {p.name}: {formatCurrencyExact(p.value)}
        </div>
      ))}
    </div>
  );
}

function EmptyState({ title, description }) {
  return (
    <div style={{
      padding: "48px 24px", textAlign: "center",
      color: "var(--text-secondary)", fontSize: "0.9rem",
    }}>
      <div style={{ fontSize: "1rem", marginBottom: "8px", color: "var(--text-primary)" }}>{title}</div>
      <div style={{ lineHeight: "1.6", maxWidth: "400px", margin: "0 auto" }}>{description}</div>
    </div>
  );
}

export default function RevenuePage() {
  const { user, token } = useAuth();
  const [period, setPeriod] = useState("30d");
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState(null);
  const [trend, setTrend] = useState(null);
  const [customers, setCustomers] = useState(null);
  const [breakdown, setBreakdown] = useState(null);
  const [error, setError] = useState(null);

  const chartTheme = useMemo(() => getChartTheme(), []);

  const SOURCE_COLORS = useMemo(() => ({
    "Invoices": chartTheme.accent,
    "Pipeline Deals": chartTheme.green,
    "Orders": chartTheme.purple,
    "Accepted Bids": chartTheme.yellow,
  }), [chartTheme]);

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    setError(null);
    try {
      const [ovRes, trRes, custRes, bkRes] = await Promise.allSettled([
        fetchRevenueOverview(user.tenantId, token, period),
        fetchRevenueTrend(user.tenantId, token, period),
        fetchTopCustomers(user.tenantId, token, period),
        fetchRevenueBreakdown(user.tenantId, token, period),
      ]);
      if (ovRes.status === "fulfilled") setOverview(ovRes.value);
      if (trRes.status === "fulfilled") setTrend(trRes.value);
      if (custRes.status === "fulfilled") setCustomers(custRes.value);
      if (bkRes.status === "fulfilled") setBreakdown(bkRes.value);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, period]);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div style={{ padding: "24px" }}>
        <SkeletonLoader lines={8} />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "24px", color: "var(--red)" }}>
        Failed to load revenue data: {error}
      </div>
    );
  }

  const hasRevenue = overview && overview.total_revenue > 0;
  const hasTrend = trend && trend.data && trend.data.some(d => d.total > 0);

  return (
    <div style={{ padding: "24px", maxWidth: "1200px" }}>
      {/* Header */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        marginBottom: "24px", flexWrap: "wrap", gap: "12px",
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.5rem", fontWeight: 700 }}>Revenue</h1>
          <p style={{ margin: "4px 0 0", color: "var(--text-secondary)", fontSize: "0.85rem" }}>
            Unified financial overview across all revenue streams
          </p>
        </div>
        <div style={{ display: "flex", gap: "6px" }}>
          {PERIODS.map(p => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              style={{
                padding: "6px 14px", borderRadius: "8px", fontSize: "0.8rem",
                fontWeight: 500, cursor: "pointer", border: "1px solid var(--border)",
                background: period === p.value ? "var(--accent)" : "var(--bg-card)",
                color: period === p.value ? "#fff" : "var(--text-secondary)",
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Top Stats */}
      {overview && (
        <div style={{ display: "flex", gap: "16px", marginBottom: "24px", flexWrap: "wrap" }}>
          <RevenueStatCard
            label="Total Revenue"
            value={overview.total_revenue}
            change={overview.revenue_change}
          />
          <RevenueStatCard
            label="Invoices Paid"
            value={overview.invoices.paid}
            change={overview.invoices.paid_change}
          />
          <RevenueStatCard
            label="Outstanding"
            value={overview.invoices.outstanding}
          />
          <RevenueStatCard
            label="Overdue"
            value={overview.invoices.overdue}
          />
        </div>
      )}

      {/* Secondary Stats */}
      {overview && (
        <div style={{ display: "flex", gap: "16px", marginBottom: "24px", flexWrap: "wrap" }}>
          <RevenueStatCard
            label="Pipeline Won"
            value={overview.pipeline.won_value}
            change={overview.pipeline.won_change}
          />
          <RevenueStatCard
            label="Order Revenue"
            value={overview.orders.revenue}
            change={overview.orders.revenue_change}
          />
          <RevenueStatCard
            label="Bids Accepted"
            value={overview.bids.accepted_value}
            change={overview.bids.accepted_change}
          />
          <RevenueStatCard
            label="Bid Win Rate"
            value={overview.bids.win_rate}
            prefix=""
            suffix="%"
          />
        </div>
      )}

      {/* Charts Row */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "16px", marginBottom: "24px" }}>
        {/* Revenue Trend Chart */}
        <div style={{
          background: "var(--bg-card)", border: "1px solid var(--border)",
          borderRadius: "12px", padding: "20px",
        }}>
          <h3 style={{ margin: "0 0 16px", fontSize: "0.95rem", fontWeight: 600 }}>Revenue Over Time</h3>
          {hasTrend ? (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={trend.data} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorInvoices" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={chartTheme.accent} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={chartTheme.accent} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorOrders" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={chartTheme.purple} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={chartTheme.purple} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorPipeline" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={chartTheme.green} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={chartTheme.green} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorBids" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={chartTheme.yellow} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={chartTheme.yellow} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: chartTheme.text, fontSize: 11 }}
                  tickFormatter={(d) => {
                    const dt = new Date(d + "T00:00:00");
                    return dt.toLocaleDateString("en-US", { month: "short", day: "numeric" });
                  }}
                  interval={period === "7d" ? 0 : period === "30d" ? 6 : 13}
                />
                <YAxis
                  tick={{ fill: chartTheme.text, fontSize: 11 }}
                  tickFormatter={(v) => v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v}`}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="invoices" name="Invoices" stroke={chartTheme.accent} fill="url(#colorInvoices)" strokeWidth={2} />
                <Area type="monotone" dataKey="orders" name="Orders" stroke={chartTheme.purple} fill="url(#colorOrders)" strokeWidth={2} />
                <Area type="monotone" dataKey="pipeline" name="Pipeline" stroke={chartTheme.green} fill="url(#colorPipeline)" strokeWidth={2} />
                <Area type="monotone" dataKey="bids" name="Bids" stroke={chartTheme.yellow} fill="url(#colorBids)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState
              title="No revenue data yet"
              description="Revenue will appear here as you create invoices, close deals in the pipeline, receive orders, and accept bids. Start by sending your first invoice."
            />
          )}
        </div>

        {/* Revenue Breakdown Pie */}
        <div style={{
          background: "var(--bg-card)", border: "1px solid var(--border)",
          borderRadius: "12px", padding: "20px",
        }}>
          <h3 style={{ margin: "0 0 16px", fontSize: "0.95rem", fontWeight: 600 }}>Revenue by Source</h3>
          {breakdown && breakdown.sources && breakdown.sources.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={breakdown.sources}
                  dataKey="value"
                  nameKey="source"
                  cx="50%"
                  cy="45%"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={3}
                  label={({ source, value }) => `${formatCurrency(value)}`}
                >
                  {breakdown.sources.map((entry) => (
                    <Cell
                      key={entry.source}
                      fill={SOURCE_COLORS[entry.source] || chartTheme.accent}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => formatCurrencyExact(value)}
                  contentStyle={{
                    background: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    fontSize: "0.8rem",
                  }}
                />
                <Legend
                  wrapperStyle={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}
                  formatter={(value) => <span style={{ color: "var(--text-secondary)" }}>{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState
              title="No breakdown available"
              description="Revenue sources will be shown once you have paid invoices, closed deals, or accepted bids."
            />
          )}
        </div>
      </div>

      {/* Top Customers */}
      <div style={{
        background: "var(--bg-card)", border: "1px solid var(--border)",
        borderRadius: "12px", padding: "20px",
      }}>
        <h3 style={{ margin: "0 0 16px", fontSize: "0.95rem", fontWeight: 600 }}>Top Customers by Revenue</h3>
        {customers && customers.customers && customers.customers.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  <th style={{ textAlign: "left", padding: "10px 12px", color: "var(--text-secondary)", fontWeight: 500 }}>Rank</th>
                  <th style={{ textAlign: "left", padding: "10px 12px", color: "var(--text-secondary)", fontWeight: 500 }}>Customer</th>
                  <th style={{ textAlign: "right", padding: "10px 12px", color: "var(--text-secondary)", fontWeight: 500 }}>Revenue</th>
                  <th style={{ textAlign: "right", padding: "10px 12px", color: "var(--text-secondary)", fontWeight: 500 }}>Invoices</th>
                </tr>
              </thead>
              <tbody>
                {customers.customers.map((c, i) => (
                  <tr key={c.lead_id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 12px" }}>
                      <span style={{
                        display: "inline-flex", alignItems: "center", justifyContent: "center",
                        width: "24px", height: "24px", borderRadius: "50%",
                        background: i === 0 ? chartTheme.yellow : i === 1 ? "var(--text-secondary)" : i === 2 ? "#cd7f32" : "var(--border)",
                        color: i < 3 ? "#000" : "var(--text-secondary)",
                        fontSize: "0.7rem", fontWeight: 700,
                      }}>
                        {i + 1}
                      </span>
                    </td>
                    <td style={{ padding: "10px 12px", fontWeight: 500 }}>{c.name}</td>
                    <td style={{ padding: "10px 12px", textAlign: "right", fontWeight: 600, color: "var(--green)" }}>
                      {formatCurrencyExact(c.revenue)}
                    </td>
                    <td style={{ padding: "10px 12px", textAlign: "right", color: "var(--text-secondary)" }}>
                      {c.invoice_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No customer revenue data yet"
            description="Your top customers will appear here once you start sending and collecting on invoices. Link invoices to leads to see per-customer revenue."
          />
        )}
      </div>
    </div>
  );
}
