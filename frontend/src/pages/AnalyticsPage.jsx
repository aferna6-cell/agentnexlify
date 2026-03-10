import { useState, useEffect, useCallback, useMemo } from "react";
import { useAuth } from "../context/AuthContext";
import {
  fetchAnalyticsOverview,
  fetchAnalyticsConversations,
  fetchAnalyticsLeads,
  fetchAnalyticsResponseTimes,
  fetchAnalyticsWidget,
} from "../utils/api";
import {
  LineChart, Line, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Area, AreaChart,
} from "recharts";
import SkeletonLoader from "../components/SkeletonLoader";

const PERIODS = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
];

function StatCard({ label, value, change, suffix = "" }) {
  const isPositive = change > 0;
  const isNeutral = change === 0;
  return (
    <div className="analytics-stat-card">
      <div className="analytics-stat-label">{label}</div>
      <div className="analytics-stat-value">
        {value}{suffix}
      </div>
      {change !== undefined && (
        <div className={`analytics-stat-change ${isPositive ? "positive" : isNeutral ? "neutral" : "negative"}`}>
          <span className="analytics-change-arrow">{isPositive ? "\u2191" : isNeutral ? "\u2014" : "\u2193"}</span>
          {Math.abs(change)}% vs prev period
        </div>
      )}
    </div>
  );
}

function getChartTheme() {
  const s = getComputedStyle(document.documentElement);
  const v = (name) => s.getPropertyValue(name).trim();
  return {
    bg: v("--bg-card"),
    grid: v("--border"),
    text: v("--text-secondary"),
    accent: v("--accent"),
    green: v("--green"),
    purple: v("--purple") || "#8b5cf6",
    yellow: v("--yellow"),
    red: v("--red"),
  };
}

function CustomTooltip({ active, payload, label, valueSuffix = "" }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="analytics-tooltip">
      <div className="analytics-tooltip-label">{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color }}>
          {p.name}: {p.value}{valueSuffix}
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const { user, token } = useAuth();
  const [period, setPeriod] = useState("30d");
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState(null);
  const [convoTrend, setConvoTrend] = useState([]);
  const [leadsData, setLeadsData] = useState(null);
  const [responseTimes, setResponseTimes] = useState(null);
  const [widgetData, setWidgetData] = useState(null);
  const [error, setError] = useState(null);

  const [currentTheme, setCurrentTheme] = useState(
    () => document.querySelector(".app")?.getAttribute("data-theme") || "dark"
  );
  useEffect(() => {
    const appEl = document.querySelector(".app");
    if (!appEl) return;
    const observer = new MutationObserver(() => {
      setCurrentTheme(appEl.getAttribute("data-theme") || "dark");
    });
    observer.observe(appEl, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);
  const chartTheme = useMemo(() => getChartTheme(), [currentTheme]);

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    setError(null);
    try {
      const [ov, conv, leads, resp, wid] = await Promise.allSettled([
        fetchAnalyticsOverview(user.tenantId, token, period),
        fetchAnalyticsConversations(user.tenantId, token, period),
        fetchAnalyticsLeads(user.tenantId, token, period),
        fetchAnalyticsResponseTimes(user.tenantId, token, period),
        fetchAnalyticsWidget(user.tenantId, token, period),
      ]);
      if (ov.status === "fulfilled") setOverview(ov.value);
      if (conv.status === "fulfilled") setConvoTrend(conv.value.data || []);
      if (leads.status === "fulfilled") setLeadsData(leads.value);
      if (resp.status === "fulfilled") setResponseTimes(resp.value);
      if (wid.status === "fulfilled") setWidgetData(wid.value);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, period]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) return <SkeletonLoader />;

  if (error) {
    return (
      <div className="fade-in">
        <div className="page-header"><h1>Analytics</h1></div>
        <div className="error-banner">Failed to load analytics: {error}</div>
      </div>
    );
  }

  const stageData = leadsData?.by_stage
    ? Object.entries(leadsData.by_stage).map(([stage, count]) => ({
        stage: stage.replace("_", " "),
        count,
      }))
    : [];

  const stageColors = {
    new: chartTheme.accent,
    contacted: chartTheme.yellow,
    "appointment booked": chartTheme.purple,
    closed: chartTheme.green,
    lost: chartTheme.red,
  };

  const responseTimeTrend = (responseTimes?.trend || []).filter(d => d.avg_seconds !== null);

  // Top performing days
  const topDays = [...convoTrend]
    .filter(d => d.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

  // Leads needing attention: high score but old stage
  const highScoreStale = leadsData?.by_stage
    ? Object.entries(leadsData.by_stage)
        .filter(([stage]) => stage === "new" || stage === "contacted")
        .reduce((sum, [, count]) => sum + count, 0)
    : 0;

  return (
    <div className="fade-in analytics-page">
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1>Analytics</h1>
          <p>Performance overview for your business</p>
        </div>
        <div className="analytics-period-selector">
          {PERIODS.map(p => (
            <button
              key={p.value}
              className={`analytics-period-btn ${period === p.value ? "active" : ""}`}
              onClick={() => setPeriod(p.value)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Overview stat cards */}
      <div className="analytics-stats-row">
        <StatCard
          label="Conversations"
          value={overview?.total_conversations ?? 0}
          change={overview?.changes?.conversations}
        />
        <StatCard
          label="Leads Captured"
          value={overview?.total_leads ?? 0}
          change={overview?.changes?.leads}
        />
        <StatCard
          label="Conversion Rate"
          value={overview?.conversion_rate ?? 0}
          suffix="%"
          change={overview?.changes?.conversion_rate}
        />
        <StatCard
          label="Appointments"
          value={overview?.total_appointments ?? 0}
          change={overview?.changes?.appointments}
        />
      </div>

      {/* Charts row 1: Conversations + Leads by stage */}
      <div className="analytics-charts-row">
        <div className="analytics-chart-card">
          <h3>Conversations Over Time</h3>
          {convoTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={convoTrend}>
                <defs>
                  <linearGradient id="convoGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={chartTheme.accent} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={chartTheme.accent} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                <XAxis
                  dataKey="date"
                  stroke={chartTheme.text}
                  fontSize={11}
                  tickFormatter={d => d.slice(5)}
                />
                <YAxis stroke={chartTheme.text} fontSize={11} allowDecimals={false} />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="count"
                  name="Conversations"
                  stroke={chartTheme.accent}
                  fill="url(#convoGrad)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="analytics-empty">No conversation data yet</div>
          )}
        </div>

        <div className="analytics-chart-card">
          <h3>Leads by Stage</h3>
          {stageData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={stageData}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                <XAxis dataKey="stage" stroke={chartTheme.text} fontSize={11} />
                <YAxis stroke={chartTheme.text} fontSize={11} allowDecimals={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar
                  dataKey="count"
                  name="Leads"
                  radius={[4, 4, 0, 0]}
                  fill={chartTheme.accent}
                >
                  {stageData.map((entry, i) => (
                    <Cell key={i} fill={stageColors[entry.stage] || chartTheme.accent} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="analytics-empty">No lead data yet</div>
          )}
        </div>
      </div>

      {/* Charts row 2: Response time + Peak hours */}
      <div className="analytics-charts-row">
        <div className="analytics-chart-card">
          <h3>Response Time Trend</h3>
          <div className="analytics-chart-subtitle">
            Avg: {responseTimes?.avg_response_seconds ?? 0}s | First response: {responseTimes?.avg_first_response_seconds ?? 0}s
          </div>
          {responseTimeTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={responseTimeTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                <XAxis
                  dataKey="date"
                  stroke={chartTheme.text}
                  fontSize={11}
                  tickFormatter={d => d.slice(5)}
                />
                <YAxis stroke={chartTheme.text} fontSize={11} unit="s" />
                <Tooltip content={<CustomTooltip valueSuffix="s" />} />
                <Line
                  type="monotone"
                  dataKey="avg_seconds"
                  name="Avg Response"
                  stroke={chartTheme.green}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="analytics-empty">No response time data yet</div>
          )}
        </div>

        <div className="analytics-chart-card">
          <h3>Peak Hours</h3>
          <div className="analytics-chart-subtitle">
            When conversations happen (UTC)
          </div>
          {widgetData?.peak_hours ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={widgetData.peak_hours}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                <XAxis
                  dataKey="hour"
                  stroke={chartTheme.text}
                  fontSize={11}
                  tickFormatter={h => `${h}:00`}
                />
                <YAxis stroke={chartTheme.text} fontSize={11} allowDecimals={false} />
                <Tooltip
                  content={<CustomTooltip />}
                  labelFormatter={h => `${h}:00 - ${h}:59`}
                />
                <Bar
                  dataKey="count"
                  name="Conversations"
                  fill={chartTheme.purple}
                  radius={[2, 2, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="analytics-empty">No widget data yet</div>
          )}
        </div>
      </div>

      {/* Bottom section */}
      <div className="analytics-bottom-row">
        <div className="analytics-chart-card">
          <h3>Top Performing Days</h3>
          {topDays.length > 0 ? (
            <div className="analytics-top-days">
              {topDays.map((d, i) => (
                <div key={d.date} className="analytics-top-day-item">
                  <span className="analytics-top-day-rank">#{i + 1}</span>
                  <span className="analytics-top-day-date">{d.date}</span>
                  <span className="analytics-top-day-count">{d.count} conversations</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="analytics-empty">No data yet</div>
          )}
        </div>

        <div className="analytics-chart-card">
          <h3>Quick Insights</h3>
          <div className="analytics-insights">
            <div className="analytics-insight-item">
              <span className="analytics-insight-icon" style={{ color: chartTheme.accent }}>&#9679;</span>
              <span>Avg {overview?.avg_messages_per_conversation ?? 0} messages per conversation</span>
            </div>
            <div className="analytics-insight-item">
              <span className="analytics-insight-icon" style={{ color: chartTheme.green }}>&#9679;</span>
              <span>Avg lead score: {leadsData?.avg_lead_score ?? 0}</span>
            </div>
            <div className="analytics-insight-item">
              <span className="analytics-insight-icon" style={{ color: chartTheme.yellow }}>&#9679;</span>
              <span>{highScoreStale} leads in early stages need attention</span>
            </div>
            <div className="analytics-insight-item">
              <span className="analytics-insight-icon" style={{ color: chartTheme.purple }}>&#9679;</span>
              <span>Avg conversation duration: {widgetData ? Math.round(widgetData.avg_duration_seconds / 60) : 0} min</span>
            </div>
            <div className="analytics-insight-item">
              <span className="analytics-insight-icon" style={{ color: chartTheme.red }}>&#9679;</span>
              <span>{overview?.total_emails_sent ?? 0} emails sent this period</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
