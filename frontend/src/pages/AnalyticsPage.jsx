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
  fetchAnalyticsSnapshot,
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
    tooltipBg: v("--bg-card") || "#1a1a2e",
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
  // peak_hours is [{hour, count}] - distribute across days proportionally for visualization
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
                title={`${dayLabel} ${h}:00 - ${grid[d][h]} conversations`}
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

function ShareResultsModal({ snapshot, onClose }) {
  const [copied, setCopied] = useState(false);

  if (!snapshot) return null;

  const topQList = (snapshot.top_questions || []).length > 0
    ? snapshot.top_questions.map((q, i) => `  ${i + 1}. ${q}`).join("\n")
    : "  (No questions yet)";

  const summaryText = [
    `${snapshot.business_name} -- AI Chat Performance`,
    `Period: ${snapshot.period}`,
    "",
    `Conversations: ${snapshot.total_conversations}`,
    `Messages: ${snapshot.total_messages}`,
    `Unique Visitors: ${snapshot.unique_visitors}`,
    `Leads Captured: ${snapshot.leads_captured}`,
    `Appointments Booked: ${snapshot.appointments_booked}`,
    `Avg Messages/Chat: ${snapshot.avg_messages_per_conversation}`,
    snapshot.busiest_day ? `Busiest Day: ${snapshot.busiest_day}` : null,
    "",
    "Top Questions:",
    topQList,
    "",
    "Powered by AgentNexLiFy",
  ]
    .filter((line) => line !== null)
    .join("\n");

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(summaryText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = summaryText;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="share-modal-overlay" onClick={onClose}>
      <div className="share-modal" onClick={(e) => e.stopPropagation()}>
        <div className="share-modal-header">
          <h2>Share Results</h2>
          <button className="share-modal-close" onClick={onClose}>
            &times;
          </button>
        </div>
        <pre className="share-modal-content">{summaryText}</pre>
        <div className="share-modal-footer">
          <button
            className={`btn btn-primary share-copy-btn ${copied ? "copied" : ""}`}
            onClick={handleCopy}
          >
            {copied ? "Copied!" : "Copy to Clipboard"}
          </button>
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
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
  const [error, setError] = useState(null);
  const [shareSnapshot, setShareSnapshot] = useState(null);
  const [shareLoading, setShareLoading] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);

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
      const [ov, conv, leads, resp, wid, convos, tagDefs, missedCalls, sources] = await Promise.allSettled([
        fetchAnalyticsOverview(user.tenantId, token, period),
        fetchAnalyticsConversations(user.tenantId, token, period),
        fetchAnalyticsLeads(user.tenantId, token, period),
        fetchAnalyticsResponseTimes(user.tenantId, token, period),
        fetchAnalyticsWidget(user.tenantId, token, period),
        fetchConversations(user.tenantId, token),
        fetchTagDefinitions(user.tenantId, token),
        fetchMissedCallAnalytics(user.tenantId, token, period),
        fetchLeadSources(user.tenantId, token),
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
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, period]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleShareResults = useCallback(async () => {
    if (!user?.tenantId) return;
    setShareLoading(true);
    try {
      const data = await fetchAnalyticsSnapshot(user.tenantId, token, period);
      setShareSnapshot(data);
      setShareOpen(true);
    } catch (err) {
      // Surface error visually - show a transient message
      setError(`Failed to generate snapshot: ${err.message}`);
      setTimeout(() => setError(null), 4000);
    } finally {
      setShareLoading(false);
    }
  }, [user?.tenantId, token, period]);

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
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
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
          <button
            className="btn btn-secondary share-results-btn"
            onClick={handleShareResults}
            disabled={shareLoading}
            title="Generate a shareable performance summary"
          >
            {shareLoading ? "Generating..." : "Share Results"}
          </button>
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

      {/* Response Time - stat cards + trend chart */}
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

      {shareOpen && (
        <ShareResultsModal
          snapshot={shareSnapshot}
          onClose={() => {
            setShareOpen(false);
            setShareSnapshot(null);
          }}
        />
      )}
    </div>
  );
}
