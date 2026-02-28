import { useMemo } from 'react';
import { leads, activityFeed, weeklyData, pipelineStages, formatTimeAgo, getScoreEmoji } from '../data/mockData';
import demoConfig from '../config/demoConfig';

function StatCard({ label, value, trend, trendDir, color }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color }}>{value}</div>
      <div className={`stat-trend ${trendDir}`}>{trend}</div>
    </div>
  );
}

function LeadCard({ lead }) {
  return (
    <div className="lead-card">
      <div className="lead-name">{getScoreEmoji(lead.score)} {lead.name}</div>
      <div className="lead-desc">{lead.description}</div>
      <div className="lead-meta">
        <span className="lead-tag source">{lead.source}</span>
        <span className={`lead-tag score-${lead.score}`}>{lead.score.charAt(0).toUpperCase() + lead.score.slice(1)}</span>
        <span className="lead-time">{formatTimeAgo(lead.minutesAgo)}</span>
      </div>
      <div className="lead-automation">{lead.automationNote}</div>
    </div>
  );
}

function WeeklyChart() {
  const maxVal = Math.max(...weeklyData.map((d) => d.value));
  const barWidth = 40;
  const gap = 20;
  const chartHeight = 160;
  const svgWidth = weeklyData.length * (barWidth + gap) - gap + 40;

  return (
    <div className="chart-container">
      <div className="chart-title">Weekly Performance — Leads Captured</div>
      <svg className="chart-svg" viewBox={`0 0 ${svgWidth} ${chartHeight + 40}`} preserveAspectRatio="xMidYMid meet">
        {weeklyData.map((d, i) => {
          const barH = (d.value / maxVal) * chartHeight;
          const x = i * (barWidth + gap) + 20;
          const y = chartHeight - barH;
          return (
            <g key={d.day}>
              <rect className="chart-bar" x={x} y={y} width={barWidth} height={barH} rx="4" />
              <text className="chart-value" x={x + barWidth / 2} y={y - 6}>{d.value}</text>
              <text className="chart-label" x={x + barWidth / 2} y={chartHeight + 20}>{d.day}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function Dashboard() {
  const grouped = useMemo(() => {
    const g = {};
    pipelineStages.forEach((s) => { g[s.key] = []; });
    leads.forEach((l) => { if (g[l.stage]) g[l.stage].push(l); });
    return g;
  }, []);

  return (
    <>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Your business at a glance — updated live</p>
      </div>

      <div className="stats-row">
        <StatCard label={demoConfig.dashboardLabels.leads} value="7" trend="↑ 23% vs last week" trendDir="up" color="var(--accent)" />
        <StatCard label={demoConfig.dashboardLabels.booked} value="3" trend="↑ 15% vs last week" trendDir="up" color="var(--green)" />
        <StatCard label="Automations Running" value="12" trend="All systems active" trendDir="neutral" color="var(--accent)" />
        <StatCard label="Response Time" value="47s" trend="Avg — under target" trendDir="up" color="var(--green)" />
      </div>

      <div className="pipeline">
        <div className="pipeline-header">Leads Pipeline</div>
        <div className="pipeline-columns">
          {pipelineStages.map((stage) => (
            <div className="pipeline-column" key={stage.key}>
              <div className="pipeline-col-header">
                <span className="pipeline-col-title">{stage.label}</span>
                <span className="pipeline-col-count">{grouped[stage.key].length}</span>
              </div>
              <div className="pipeline-cards">
                {grouped[stage.key].map((lead) => (
                  <LeadCard key={lead.id} lead={lead} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="dashboard-grid">
        <WeeklyChart />
        <div className="activity-feed">
          <div className="activity-feed-title">Recent Activity</div>
          {activityFeed.map((item) => (
            <div className="activity-item" key={item.id}>
              <span className="activity-icon">{item.icon}</span>
              <span className="activity-text">{item.message}</span>
              <span className="activity-time">{formatTimeAgo(item.minutesAgo)}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
