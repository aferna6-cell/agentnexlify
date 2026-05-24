import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { PLATFORMS } from "./constants";
import { cardStyle } from "./styles";

export default function AnalyticsView({ posts }) {
  const totalPosts = posts.length;

  const platformCounts = PLATFORMS.map((p) => ({
    name: p.label,
    count: posts.filter((post) => post.platform === p.key).length,
    color: p.color,
  }));

  const thisWeekCount = posts.filter((p) => {
    const d = new Date(p.published_at || p.created_at);
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return d >= weekAgo;
  }).length;

  const thisMonthCount = posts.filter((p) => {
    const d = new Date(p.published_at || p.created_at);
    const monthAgo = new Date();
    monthAgo.setDate(monthAgo.getDate() - 30);
    return d >= monthAgo;
  }).length;

  const oldestPost = posts[posts.length - 1];
  const avgPostsPerWeek =
    totalPosts > 0
      ? Math.round(
          (totalPosts /
            Math.max(
              1,
              Math.ceil(
                (Date.now() -
                  new Date(oldestPost?.created_at || Date.now()).getTime()) /
                  (7 * 86400000),
              ),
            )) *
            10,
        ) / 10
      : 0;

  const summaryRows = [
    { label: "This Week", value: thisWeekCount, color: "var(--accent)" },
    { label: "This Month", value: thisMonthCount, color: "var(--green)" },
    {
      label: "Avg. Posts/Week",
      value: avgPostsPerWeek,
      color: "var(--purple, #8b5cf6)",
    },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
      <div style={cardStyle}>
        <h3
          style={{
            margin: "0 0 16px",
            fontSize: "1rem",
            color: "var(--text-primary)",
          }}
        >
          Posts by Platform
        </h3>
        {totalPosts === 0 ? (
          <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>
            Create posts to see platform distribution here.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={platformCounts}>
              <XAxis
                dataKey="name"
                tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--bg-primary)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  color: "var(--text-primary)",
                }}
              />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {platformCounts.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div style={cardStyle}>
        <h3
          style={{
            margin: "0 0 16px",
            fontSize: "1rem",
            color: "var(--text-primary)",
          }}
        >
          Publishing Summary
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {summaryRows.map((row) => (
            <div
              key={row.label}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span
                style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}
              >
                {row.label}
              </span>
              <span
                style={{
                  fontSize: "1.25rem",
                  fontWeight: 700,
                  color: row.color,
                }}
              >
                {row.value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
