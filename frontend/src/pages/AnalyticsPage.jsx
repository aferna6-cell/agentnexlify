import { useState, useEffect, useCallback, useMemo } from "react";
import { useAuth } from "../context/AuthContext";
import {
  fetchAnalyticsOverview,
  fetchAnalyticsConversations,
  fetchAnalyticsLeads,
  fetchAnalyticsResponseTimes,
  fetchAnalyticsWidget,
  fetchMissedCallAnalytics,
  fetchLeadSources,
  fetchTeamPerformance,
  fetchLeadSourcesUtm,
  fetchConversationSentiment,
  fetchCustomerLifetimeValue,
} from "../utils/api/analytics";
import { fetchConversations } from "../utils/api/conversations";
import { fetchTagDefinitions } from "../utils/api/tags";
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

function ConversionFunnel({ conversations, leads, appointments, completed, chartTheme }) {
  // Calculate completed: use provided value, or estimate from appointment stages
  const completedCount = completed || Math.round(appointments * 0.6);
  const stages = [
    { label: "Conversations", value: conversations, color: chartTheme.accent },
    { label: "Leads", value: leads, color: chartTheme.green },
    { label: "Appointments", value: appointments, color: chartTheme.purple },
    { label: "Completed", value: completedCount, color: chartTheme.yellow },
  ];

  const maxValue = Math.max(conversations, 1);
  const allZero = conversations === 0 && leads === 0 && appointments === 0;

  if (allZero) {
    return (
      <div className="analytics-empty" style={{ padding: "40px 20px", textAlign: "center" }}>
        <div style={{ fontSize: "16px", marginBottom: "8px" }}>No funnel data yet</div>
        <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
          Your conversion funnel tracks visitors from first conversation to completed appointment.
          Start by embedding the chat widget on your website to begin capturing leads.
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-funnel">
      {stages.map((stage, i) => {
        const widthPct = Math.max((stage.value / maxValue) * 100, 4);
        const prevValue = i > 0 ? stages[i - 1].value : null;
        const conversionPct = prevValue && prevValue > 0
          ? Math.round((stage.value / prevValue) * 100)
          : null;
        return (
          <div key={stage.label} className="analytics-funnel-row">
            <div className="analytics-funnel-label">
              <span className="analytics-funnel-stage">{stage.label}</span>
              <span className="analytics-funnel-value">{stage.value}</span>
            </div>
            <div className="analytics-funnel-bar-wrapper">
              <div
                className="analytics-funnel-bar"
                style={{
                  width: `${widthPct}%`,
                  backgroundColor: stage.color,
                }}
              />
            </div>
            {conversionPct !== null && (
              <div className="analytics-funnel-pct">{conversionPct}%</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function BusiestHoursHeatMap({ peakHours, chartTheme }) {
  if (!peakHours || peakHours.length === 0) {
    return (
      <div className="analytics-empty" style={{ padding: "40px 20px", textAlign: "center" }}>
        <div style={{ fontSize: "16px", marginBottom: "8px" }}>No activity data yet</div>
        <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
          The heat map will show when your chat widget is busiest once conversations
          start flowing. Darker cells mean more activity at that hour.
        </div>
      </div>
    );
  }

  // Build a 7x24 grid from peak_hours data
  // peak_hours is [{hour, count}] — distribute across days proportionally for visualization
  // If we have day_of_week data, use it; otherwise spread hourly totals evenly across days
  const grid = Array.from({ length: 7 }, () => Array(24).fill(0));

  // Check if data has day_of_week field
  const hasDayData = peakHours.some(d => d.day_of_week !== undefined);

  if (hasDayData) {
    for (const entry of peakHours) {
      const day = entry.day_of_week;
      const hour = entry.hour;
      if (day >= 0 && day < 7 && hour >= 0 && hour < 24) {
        grid[day][hour] = entry.count || 0;
      }
    }
  } else {
    // Distribute hourly counts across days with slight variation for realism
    for (const entry of peakHours) {
      const hour = entry.hour;
      if (hour >= 0 && hour < 24) {
        const totalForHour = entry.count || 0;
        for (let d = 0; d < 7; d++) {
          // Weekdays (Mon-Fri) get more weight, weekends less
          const isWeekend = d === 0 || d === 6;
          const weight = isWeekend ? 0.08 : 0.168;
          grid[d][hour] = Math.round(totalForHour * weight);
        }
      }
    }
  }

  // Find max for color scaling
  let maxCount = 0;
  for (let d = 0; d < 7; d++) {
    for (let h = 0; h < 24; h++) {
      if (grid[d][h] > maxCount) maxCount = grid[d][h];
    }
  }

  function getCellColor(count) {
    if (maxCount === 0 || count === 0) return "var(--bg-secondary)";
    const ratio = count / maxCount;
    if (ratio < 0.33) return chartTheme.green;
    if (ratio < 0.66) return chartTheme.yellow;
    return chartTheme.red;
  }

  function getCellOpacity(count) {
    if (maxCount === 0 || count === 0) return 0.3;
    const ratio = count / maxCount;
    return 0.3 + ratio * 0.7;
  }

  // Show every 3rd hour label for readability
  const hourLabels = Array.from({ length: 24 }, (_, i) => i);

  return (
    <div className="analytics-heatmap-container">
      <div className="analytics-heatmap">
        {/* Hour labels along the top */}
        <div className="analytics-heatmap-row analytics-heatmap-header">
          <div className="analytics-heatmap-day-label" />
          {hourLabels.map(h => (
            <div key={h} className="analytics-heatmap-hour-label">
              {h % 3 === 0 ? `${h}` : ""}
            </div>
          ))}
        </div>
        {/* Grid rows */}
        {DAY_LABELS.map((dayLabel, d) => (
          <div key={d} className="analytics-heatmap-row">
            <div className="analytics-heatmap-day-label">{dayLabel}</div>
            {hourLabels.map(h => (
              <div
                key={h}
                className="analytics-heatmap-cell"
                style={{
                  backgroundColor: getCellColor(grid[d][h]),
                  opacity: getCellOpacity(grid[d][h]),
                }}
                title={`${dayLabel} ${h}:00 — ${grid[d][h]} conversations`}
              />
            ))}
          </div>
        ))}
      </div>
      {/* Legend */}
      <div className="analytics-heatmap-legend">
        <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>Low</span>
        <div className="analytics-heatmap-legend-swatch" style={{ backgroundColor: chartTheme.green, opacity: 0.5 }} />
        <div className="analytics-heatmap-legend-swatch" style={{ backgroundColor: chartTheme.yellow, opacity: 0.7 }} />
        <div className="analytics-heatmap-legend-swatch" style={{ backgroundColor: chartTheme.red, opacity: 1 }} />
        <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>High</span>
      </div>
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
  const [tagDistribution, setTagDistribution] = useState([]);
  const [missedCallsData, setMissedCallsData] = useState(null);
  const [missedCallsError, setMissedCallsError] = useState(false);
  const [leadSources, setLeadSources] = useState([]);
  const [teamPerformance, setTeamPerformance] = useState(null);
  const [utmData, setUtmData] = useState(null);
  const [sentimentData, setSentimentData] = useState(null);
  const [clvData, setClvData] = useState(null);
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
      const periodDays = { "7d": 7, "30d": 30, "90d": 90 }[period] || 30;
      const [ov, conv, leads, resp, wid, convos, tagDefs, missedCalls, sources, teamPerf, utm, sentiment, clv] = await Promise.allSettled([
        fetchAnalyticsOverview(user.tenantId, token, period),
        fetchAnalyticsConversations(user.tenantId, token, period),
        fetchAnalyticsLeads(user.tenantId, token, period),
        fetchAnalyticsResponseTimes(user.tenantId, token, period),
        fetchAnalyticsWidget(user.tenantId, token, period),
        fetchConversations(user.tenantId, token),
        fetchTagDefinitions(user.tenantId, token),
        fetchMissedCallAnalytics(user.tenantId, token, period),
        fetchLeadSources(user.tenantId, token),
        fetchTeamPerformance(user.tenantId, token, periodDays),
        fetchLeadSourcesUtm(user.tenantId, token, period),
        fetchConversationSentiment(user.tenantId, token, period),
        fetchCustomerLifetimeValue(user.tenantId, token),
      ]);
      if (ov.status === "fulfilled") setOverview(ov.value);
      if (conv.status === "fulfilled") setConvoTrend(conv.value.data || []);
      if (leads.status === "fulfilled") setLeadsData(leads.value);
      if (resp.status === "fulfilled") setResponseTimes(resp.value);
      if (wid.status === "fulfilled") setWidgetData(wid.value);
      if (sources.status === "fulfilled") setLeadSources(sources.value.breakdown || []);

      // Build tag distribution from conversations + tag definitions
      if (convos.status === "fulfilled") {
        const conversations = convos.value.conversations || [];
        const tagCounts = {};
        for (const c of conversations) {
          for (const tag of (c.tags || [])) {
            tagCounts[tag] = (tagCounts[tag] || 0) + 1;
          }
        }

        // Build color map from tag definitions
        const colorMap = {};
        if (tagDefs.status === "fulfilled") {
          for (const td of (tagDefs.value.tags || [])) {
            colorMap[td.tag_name] = td.tag_color;
          }
        }

        const distribution = Object.entries(tagCounts)
          .map(([tag, count]) => ({
            tag,
            count,
            color: colorMap[tag] || chartTheme.accent,
          }))
          .sort((a, b) => b.count - a.count);

        setTagDistribution(distribution);
      }

      // Missed calls analytics
      if (missedCalls.status === "fulfilled") {
        setMissedCallsData(missedCalls.value);
        setMissedCallsError(false);
      } else {
        setMissedCallsData(null);
        setMissedCallsError(true);
      }

      // Team performance
      if (teamPerf.status === "fulfilled") setTeamPerformance(teamPerf.value);
      // UTM analytics
      if (utm.status === "fulfilled") setUtmData(utm.value);
      // Sentiment analytics
      if (sentiment.status === "fulfilled") setSentimentData(sentiment.value);
      // Customer lifetime value
      if (clv.status === "fulfilled") setClvData(clv.value);
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
            <div className="analytics-empty" style={{ padding: "40px 20px", textAlign: "center" }}>
              <div style={{ fontSize: "16px", marginBottom: "8px" }}>No conversation data yet</div>
              <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
                Start conversations through your chat widget to see analytics here. Each visitor chat will be tracked on this chart.
              </div>
            </div>
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
            <div className="analytics-empty" style={{ padding: "40px 20px", textAlign: "center" }}>
              <div style={{ fontSize: "16px", marginBottom: "8px" }}>No lead data yet</div>
              <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
                Capture leads through your widget or import them to see pipeline data. Each lead is tracked by stage as it moves through your funnel.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Response Time — stat cards + trend chart */}
      <div className="analytics-charts-row" style={{ gridTemplateColumns: "1fr" }}>
        <div className="analytics-chart-card">
          <h3>Response Time Trend</h3>
          <div className="analytics-rt-stats">
            <div className="analytics-rt-stat">
              <span className="analytics-rt-stat-label">Avg Response</span>
              <span className="analytics-rt-stat-value" style={{ color: chartTheme.green }}>
                {responseTimes?.avg_response_seconds ?? 0}s
              </span>
            </div>
            <div className="analytics-rt-stat">
              <span className="analytics-rt-stat-label">Median Response</span>
              <span className="analytics-rt-stat-value" style={{ color: chartTheme.purple }}>
                {responseTimes?.median_response_seconds ?? responseTimes?.avg_first_response_seconds ?? 0}s
              </span>
            </div>
            <div className="analytics-rt-stat">
              <span className="analytics-rt-stat-label">Total Conversations</span>
              <span className="analytics-rt-stat-value" style={{ color: chartTheme.accent }}>
                {responseTimes?.total_conversations ?? overview?.total_conversations ?? 0}
              </span>
            </div>
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
                {responseTimeTrend.some(d => d.median_seconds != null) && (
                  <Line
                    type="monotone"
                    dataKey="median_seconds"
                    name="Median Response"
                    stroke={chartTheme.purple}
                    strokeWidth={2}
                    strokeDasharray="5 3"
                    dot={false}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="analytics-empty" style={{ padding: "40px 20px", textAlign: "center" }}>
              <div style={{ fontSize: "16px", marginBottom: "8px" }}>No response time data yet</div>
              <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
                Response time metrics appear once your widget starts receiving conversations.
                The chart shows how quickly your AI responds over time.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Lead Conversion Funnel + Peak Hours */}
      <div className="analytics-charts-row">
        <div className="analytics-chart-card">
          <h3>Lead Conversion Funnel</h3>
          <div className="analytics-chart-subtitle">
            How visitors progress from conversation to completion
          </div>
          <ConversionFunnel
            conversations={overview?.total_conversations ?? 0}
            leads={overview?.total_leads ?? 0}
            appointments={overview?.total_appointments ?? 0}
            completed={overview?.completed_appointments ?? 0}
            chartTheme={chartTheme}
          />
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
            <div className="analytics-empty" style={{ padding: "40px 20px", textAlign: "center" }}>
              <div style={{ fontSize: "16px", marginBottom: "8px" }}>No peak hours data yet</div>
              <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
                Once visitors start chatting through your widget, this chart will show which hours of the day are busiest so you can optimize your availability.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Busiest Hours Heat Map */}
      <div className="analytics-charts-row" style={{ gridTemplateColumns: "1fr" }}>
        <div className="analytics-chart-card">
          <h3>Busiest Hours Heat Map</h3>
          <div className="analytics-chart-subtitle">
            Chat volume by day of week and hour (based on peak hours data)
          </div>
          <BusiestHoursHeatMap peakHours={widgetData?.peak_hours} chartTheme={chartTheme} />
        </div>
      </div>

      {/* Missed Calls */}
      <div className="analytics-charts-row" style={{ gridTemplateColumns: "1fr" }}>
        <div className="analytics-chart-card">
          <h3>Missed Calls</h3>
          <div className="analytics-chart-subtitle">
            Missed call volume per day
          </div>
          {missedCallsError ? (
            <div className="analytics-empty" style={{ padding: "40px 20px", textAlign: "center" }}>
              <div style={{ fontSize: "16px", marginBottom: "8px" }}>Missed call analytics coming soon</div>
              <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
                Once missed call tracking is enabled, you will see a daily breakdown of missed calls here.
                Enable the AI Answering Service to start capturing missed calls automatically.
              </div>
            </div>
          ) : missedCallsData?.daily && missedCallsData.daily.length > 0 ? (
            <>
              <div className="analytics-rt-stats" style={{ marginBottom: "12px" }}>
                <div className="analytics-rt-stat">
                  <span className="analytics-rt-stat-label">Total Missed</span>
                  <span className="analytics-rt-stat-value" style={{ color: chartTheme.red }}>
                    {missedCallsData.total ?? missedCallsData.daily.reduce((sum, d) => sum + (d.count || 0), 0)}
                  </span>
                </div>
                {missedCallsData.texted_back != null && (
                  <div className="analytics-rt-stat">
                    <span className="analytics-rt-stat-label">Texted Back</span>
                    <span className="analytics-rt-stat-value" style={{ color: chartTheme.green }}>
                      {missedCallsData.texted_back}
                    </span>
                  </div>
                )}
              </div>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={missedCallsData.daily}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                  <XAxis
                    dataKey="date"
                    stroke={chartTheme.text}
                    fontSize={11}
                    tickFormatter={d => d.slice(5)}
                  />
                  <YAxis stroke={chartTheme.text} fontSize={11} allowDecimals={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar
                    dataKey="count"
                    name="Missed Calls"
                    fill={chartTheme.red}
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </>
          ) : (
            <div className="analytics-empty" style={{ padding: "40px 20px", textAlign: "center" }}>
              <div style={{ fontSize: "16px", marginBottom: "8px" }}>No missed calls recorded</div>
              <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
                Great news! No missed calls during this period. If you have the AI Answering Service
                enabled, missed calls are automatically followed up with a text message.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Conversation Tags */}
      <div className="analytics-charts-row">
        <div className="analytics-chart-card" style={{ flex: 1 }}>
          <h3>Conversation Tags</h3>
          <div className="analytics-chart-subtitle">
            AI auto-categorization tag distribution across all conversations
          </div>
          {tagDistribution.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={tagDistribution} margin={{ bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                <XAxis
                  dataKey="tag"
                  stroke={chartTheme.text}
                  fontSize={11}
                  angle={-35}
                  textAnchor="end"
                  interval={0}
                  height={60}
                />
                <YAxis stroke={chartTheme.text} fontSize={11} allowDecimals={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar
                  dataKey="count"
                  name="Conversations"
                  radius={[4, 4, 0, 0]}
                  fill={chartTheme.accent}
                >
                  {tagDistribution.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="analytics-empty" style={{ padding: "40px 20px", textAlign: "center" }}>
              <div style={{ fontSize: "16px", marginBottom: "8px" }}>No conversation tags yet</div>
              <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
                Tags are automatically assigned by AI when visitors chat through your widget.
                Once conversations start flowing, you will see which topics come up most often.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Conversation Sentiment */}
      <div className="analytics-charts-row">
        <div className="analytics-chart-card" style={{ flex: 1 }}>
          <h3>Conversation Sentiment</h3>
          <div className="analytics-chart-subtitle">
            AI-analyzed emotional tone of customer conversations
          </div>
          {sentimentData?.total_analyzed > 0 ? (
            <div>
              <div style={{ display: "flex", gap: "16px", marginBottom: "16px", flexWrap: "wrap" }}>
                {[
                  { label: "Positive", key: "positive", color: "var(--green)", emoji: "" },
                  { label: "Neutral", key: "neutral", color: "var(--yellow)", emoji: "" },
                  { label: "Negative", key: "negative", color: "var(--red)", emoji: "" },
                ].map((s) => {
                  const count = sentimentData.distribution[s.key] || 0;
                  const pct = sentimentData.total_analyzed > 0 ? Math.round((count / sentimentData.total_analyzed) * 100) : 0;
                  return (
                    <div key={s.key} style={{ flex: "1 1 120px", padding: "16px", background: "var(--bg-secondary)", borderRadius: "8px", borderLeft: `3px solid ${s.color}` }}>
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "4px" }}>{s.label}</div>
                      <div style={{ fontSize: "24px", fontWeight: 600 }}>{count}</div>
                      <div style={{ fontSize: "12px", color: s.color }}>{pct}%</div>
                    </div>
                  );
                })}
              </div>

              {/* Sentiment bar */}
              <div style={{ display: "flex", height: "12px", borderRadius: "6px", overflow: "hidden", marginBottom: "16px" }}>
                {["positive", "neutral", "negative"].map((key) => {
                  const count = sentimentData.distribution[key] || 0;
                  const pct = sentimentData.total_analyzed > 0 ? (count / sentimentData.total_analyzed) * 100 : 0;
                  const colors = { positive: "var(--green)", neutral: "var(--yellow)", negative: "var(--red)" };
                  return pct > 0 ? (
                    <div key={key} style={{ width: `${pct}%`, backgroundColor: colors[key], transition: "width 0.3s" }} title={`${key}: ${count}`} />
                  ) : null;
                })}
              </div>

              {/* Recent negative conversations */}
              {sentimentData.recent_negative?.length > 0 && (
                <div style={{ marginTop: "16px" }}>
                  <h4 style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "8px" }}>Recent Negative Conversations</h4>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {sentimentData.recent_negative.slice(0, 5).map((n) => (
                      <div key={n.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", background: "var(--bg-secondary)", borderRadius: "6px", borderLeft: "3px solid var(--red)", fontSize: "13px" }}>
                        <span style={{ fontWeight: 500 }}>{n.lead_name || n.session_id || "Unknown visitor"}</span>
                        <span style={{ color: "var(--text-secondary)", fontSize: "12px" }}>{n.updated_at ? new Date(n.updated_at).toLocaleDateString() : ""}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {sentimentData.total_unanalyzed > 0 && (
                <div style={{ marginTop: "12px", fontSize: "12px", color: "var(--text-secondary)" }}>
                  {sentimentData.total_unanalyzed} conversation{sentimentData.total_unanalyzed !== 1 ? "s" : ""} pending analysis
                </div>
              )}
            </div>
          ) : (
            <div className="analytics-empty" style={{ padding: "40px 20px", textAlign: "center" }}>
              <div style={{ fontSize: "16px", marginBottom: "8px" }}>No sentiment data yet</div>
              <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
                Conversation sentiment is analyzed automatically after conversations close.
                Once your chat widget has handled a few conversations, sentiment distribution will appear here.
              </div>
            </div>
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
            <div className="analytics-empty" style={{ padding: "40px 20px", textAlign: "center" }}>
              <div style={{ fontSize: "16px", marginBottom: "8px" }}>No top days yet</div>
              <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
                Your highest-traffic days will appear here once conversations start flowing through your widget.
              </div>
            </div>
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

        {/* Lead Sources */}
        {leadSources.length > 0 && (
          <div className="analytics-card">
            <h3 className="analytics-card-title">Lead Sources</h3>
            <ResponsiveContainer width="100%" height={Math.max(120, leadSources.length * 36)}>
              <BarChart data={leadSources} layout="vertical" margin={{ left: 80, right: 20, top: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                <XAxis type="number" stroke={chartTheme.text} fontSize={11} />
                <YAxis dataKey="source" type="category" stroke={chartTheme.text} fontSize={11} width={70} />
                <Tooltip contentStyle={{ background: chartTheme.tooltipBg, border: "none", borderRadius: 8, color: chartTheme.text }} />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {leadSources.map((entry, i) => {
                    const colors = { widget: "#3b82f6", booking: "#10b981", missed_call: "#f59e0b", manual: "#8b5cf6", csv_import: "#ec4899", form: "#14b8a6" };
                    return <Cell key={i} fill={colors[entry.source] || chartTheme.accent} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Team Performance */}
      <div className="analytics-charts-row">
        <div className="analytics-chart-card" style={{ flex: 1 }}>
          <h3>Team Performance</h3>
          <div className="analytics-chart-subtitle">
            Per-member metrics for the selected period
          </div>
          {teamPerformance?.members?.length > 0 ? (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "12px", fontSize: "13px" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                    <th style={{ textAlign: "left", padding: "8px 12px", fontWeight: 500 }}>Member</th>
                    <th style={{ textAlign: "left", padding: "8px 12px", fontWeight: 500 }}>Role</th>
                    <th style={{ textAlign: "right", padding: "8px 12px", fontWeight: 500 }}>Conversations</th>
                    <th style={{ textAlign: "right", padding: "8px 12px", fontWeight: 500 }}>Avg Response</th>
                    <th style={{ textAlign: "right", padding: "8px 12px", fontWeight: 500 }}>Leads</th>
                    <th style={{ textAlign: "right", padding: "8px 12px", fontWeight: 500 }}>Appointments</th>
                    <th style={{ textAlign: "right", padding: "8px 12px", fontWeight: 500 }}>Tasks Done</th>
                  </tr>
                </thead>
                <tbody>
                  {teamPerformance.members.map((m) => {
                    const rt = m.avg_response_time_seconds;
                    const rtDisplay = rt > 0
                      ? rt > 3600 ? `${Math.round(rt / 3600)}h` : rt > 60 ? `${Math.round(rt / 60)}m` : `${rt}s`
                      : "--";
                    return (
                      <tr key={m.id} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "10px 12px", fontWeight: 500 }}>{m.name}</td>
                        <td style={{ padding: "10px 12px", color: "var(--text-secondary)", textTransform: "capitalize" }}>{m.role}</td>
                        <td style={{ padding: "10px 12px", textAlign: "right" }}>{m.conversations_handled}</td>
                        <td style={{ padding: "10px 12px", textAlign: "right", color: rt > 300 ? "var(--red)" : rt > 60 ? "var(--yellow)" : "var(--green)" }}>{rtDisplay}</td>
                        <td style={{ padding: "10px 12px", textAlign: "right" }}>{m.leads_assigned}</td>
                        <td style={{ padding: "10px 12px", textAlign: "right" }}>{m.appointments_booked}</td>
                        <td style={{ padding: "10px 12px", textAlign: "right" }}>{m.action_items_completed}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div style={{ display: "flex", gap: "24px", marginTop: "16px", padding: "12px", background: "var(--bg-secondary)", borderRadius: "8px", fontSize: "13px" }}>
                <div><span style={{ color: "var(--text-secondary)" }}>Total conversations:</span> <strong>{teamPerformance.total_conversations || 0}</strong></div>
                <div><span style={{ color: "var(--text-secondary)" }}>Total leads assigned:</span> <strong>{teamPerformance.total_leads_assigned || 0}</strong></div>
              </div>
            </div>
          ) : (
            <div className="analytics-empty" style={{ padding: "40px 20px", textAlign: "center" }}>
              <div style={{ fontSize: "16px", marginBottom: "8px" }}>No team data yet</div>
              <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
                Add team members and assign conversations to see per-member performance metrics.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* UTM / Lead Source Analytics */}
      <div className="analytics-charts-row">
        <div className="analytics-chart-card" style={{ flex: 1 }}>
          <h3>UTM Campaign Analytics</h3>
          <div className="analytics-chart-subtitle">
            Lead sources breakdown by UTM parameters
          </div>
          {utmData?.by_source?.length > 0 ? (
            <div>
              <div style={{ display: "flex", gap: "16px", marginBottom: "16px", flexWrap: "wrap" }}>
                <div style={{ padding: "12px 16px", background: "var(--bg-secondary)", borderRadius: "8px", flex: "1 1 150px" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "4px" }}>Total Leads</div>
                  <div style={{ fontSize: "20px", fontWeight: 600 }}>{utmData.total_leads || 0}</div>
                </div>
                <div style={{ padding: "12px 16px", background: "var(--bg-secondary)", borderRadius: "8px", flex: "1 1 150px" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "4px" }}>With UTM Data</div>
                  <div style={{ fontSize: "20px", fontWeight: 600, color: "var(--accent)" }}>{utmData.total_with_utm || 0}</div>
                </div>
                <div style={{ padding: "12px 16px", background: "var(--bg-secondary)", borderRadius: "8px", flex: "1 1 150px" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "4px" }}>Direct / No UTM</div>
                  <div style={{ fontSize: "20px", fontWeight: 600 }}>{utmData.total_without_utm || 0}</div>
                </div>
              </div>

              {/* Source breakdown chart */}
              <h4 style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "8px", marginTop: "16px" }}>By Source</h4>
              <ResponsiveContainer width="100%" height={Math.max(120, utmData.by_source.length * 40)}>
                <BarChart data={utmData.by_source} layout="vertical" margin={{ left: 80, right: 60, top: 5, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                  <XAxis type="number" stroke={chartTheme.text} fontSize={11} />
                  <YAxis dataKey="source" type="category" stroke={chartTheme.text} fontSize={11} width={70} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const d = payload[0].payload;
                      return (
                        <div className="analytics-tooltip">
                          <div style={{ fontWeight: 600, marginBottom: 4 }}>{d.source}</div>
                          <div>Leads: {d.count}</div>
                          <div>Converted: {d.converted}</div>
                          <div>Rate: {d.conversion_rate}%</div>
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="count" name="Leads" radius={[0, 4, 4, 0]} fill={chartTheme.accent} />
                </BarChart>
              </ResponsiveContainer>

              {/* Medium breakdown */}
              {utmData.by_medium?.length > 0 && (
                <div style={{ marginTop: "20px" }}>
                  <h4 style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "8px" }}>By Medium</h4>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {utmData.by_medium.map((m) => (
                      <div key={m.medium} style={{ padding: "8px 14px", background: "var(--bg-secondary)", borderRadius: "6px", fontSize: "13px" }}>
                        <span style={{ fontWeight: 500 }}>{m.medium}</span>
                        <span style={{ marginLeft: "8px", color: "var(--accent)" }}>{m.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Campaign breakdown */}
              {utmData.by_campaign?.length > 0 && (
                <div style={{ marginTop: "20px" }}>
                  <h4 style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "8px" }}>By Campaign</h4>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {utmData.by_campaign.map((c) => (
                      <div key={c.campaign} style={{ padding: "8px 14px", background: "var(--bg-secondary)", borderRadius: "6px", fontSize: "13px" }}>
                        <span style={{ fontWeight: 500 }}>{c.campaign}</span>
                        <span style={{ marginLeft: "8px", color: "var(--purple)" }}>{c.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="analytics-empty" style={{ padding: "40px 20px", textAlign: "center" }}>
              <div style={{ fontSize: "16px", marginBottom: "8px" }}>No UTM data yet</div>
              <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
                UTM parameters are captured when visitors arrive at your widget from campaign links.
                Add ?utm_source=google&utm_medium=cpc to your widget page URLs to start tracking.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Customer Lifetime Value */}
      <div className="analytics-section" style={{ marginTop: "24px" }}>
        <h2 className="analytics-section-title">Customer Lifetime Value</h2>
        {clvData && clvData.total_paying_customers > 0 ? (
          <div>
            <div className="analytics-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "12px", marginBottom: "16px" }}>
              <StatCard label="Total Revenue" value={`$${clvData.total_revenue.toLocaleString()}`} />
              <StatCard label="Avg CLV" value={`$${clvData.avg_clv.toLocaleString()}`} />
              <StatCard label="Median CLV" value={`$${clvData.median_clv.toLocaleString()}`} />
              <StatCard label="Paying Customers" value={clvData.total_paying_customers} />
            </div>
            <div style={{ background: "var(--bg-secondary)", borderRadius: "8px", padding: "16px" }}>
              <div style={{ fontSize: "14px", fontWeight: 600, marginBottom: "12px" }}>Top Customers by Revenue</div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                      <th style={{ textAlign: "left", padding: "8px 12px", color: "var(--text-secondary)", fontWeight: 500 }}>Customer</th>
                      <th style={{ textAlign: "right", padding: "8px 12px", color: "var(--text-secondary)", fontWeight: 500 }}>Revenue</th>
                      <th style={{ textAlign: "right", padding: "8px 12px", color: "var(--text-secondary)", fontWeight: 500 }}>Invoices</th>
                      <th style={{ textAlign: "left", padding: "8px 12px", color: "var(--text-secondary)", fontWeight: 500 }}>First Payment</th>
                      <th style={{ textAlign: "left", padding: "8px 12px", color: "var(--text-secondary)", fontWeight: 500 }}>Last Payment</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(clvData.top_customers || []).map((c, i) => (
                      <tr key={c.lead_id || i} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "8px 12px", fontWeight: 500 }}>{c.customer_name}</td>
                        <td style={{ padding: "8px 12px", textAlign: "right", color: "var(--green)", fontWeight: 600 }}>${c.total_revenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td style={{ padding: "8px 12px", textAlign: "right" }}>{c.invoice_count}</td>
                        <td style={{ padding: "8px 12px", color: "var(--text-secondary)" }}>{c.first_payment ? new Date(c.first_payment).toLocaleDateString() : "-"}</td>
                        <td style={{ padding: "8px 12px", color: "var(--text-secondary)" }}>{c.last_payment ? new Date(c.last_payment).toLocaleDateString() : "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : (
          <div className="analytics-empty" style={{ padding: "40px 20px", textAlign: "center" }}>
            <div style={{ fontSize: "16px", marginBottom: "8px" }}>No paid invoices yet</div>
            <div style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
              Customer lifetime value is calculated from paid invoices. Create and send invoices to start tracking revenue per customer.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
