import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchCSATStats, fetchCSATResponses } from "../utils/api/misc";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
} from "recharts";

function Stars({ rating, size = 14 }) {
  return (
    <span style={{ fontSize: size, letterSpacing: 1 }}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} style={{ color: i <= rating ? "#FFD700" : "var(--text-muted)" }}>
          &#9733;
        </span>
      ))}
    </span>
  );
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function npsColor(score) {
  if (score >= 50) return "var(--green, #4ade80)";
  if (score >= 0) return "var(--yellow, #facc15)";
  return "var(--red, #ef4444)";
}

function ratingBarColor(star) {
  if (star >= 4) return "#4ade80";
  if (star === 3) return "#facc15";
  return "#f87171";
}

export default function CSATPage() {
  const { user, token } = useAuth();

  const [period, setPeriod] = useState("30d");
  const [stats, setStats] = useState(null);
  const [responses, setResponses] = useState([]);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingResponses, setLoadingResponses] = useState(true);
  const [error, setError] = useState(null);

  const loadStats = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoadingStats(true);
    try {
      const data = await fetchCSATStats(user.tenantId, token, period);
      setStats(data);
    } catch (err) {
      setError(err.message || "Failed to load CSAT stats");
    } finally {
      setLoadingStats(false);
    }
  }, [user?.tenantId, token, period]);

  const loadResponses = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoadingResponses(true);
    try {
      const data = await fetchCSATResponses(user.tenantId, token);
      setResponses(data.responses || []);
    } catch (err) {
      console.error("Failed to load CSAT responses:", err);
      setResponses([]);
    } finally {
      setLoadingResponses(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    loadResponses();
  }, [loadResponses]);

  // Build bar chart data from distribution
  const distributionData = stats
    ? [1, 2, 3, 4, 5].map((star) => ({
        star: `${star} star${star !== 1 ? "s" : ""}`,
        count: stats.distribution?.[star] ?? 0,
        fill: ratingBarColor(star),
      }))
    : [];

  // Build trend line chart data
  const trendData = stats?.trend || [];

  const loading = loadingStats || loadingResponses;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Customer Satisfaction</h1>
          <p>CSAT and NPS scores from post-conversation surveys</p>
        </div>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          style={{
            padding: "6px 10px",
            borderRadius: 6,
            border: "1px solid var(--border-color)",
            background: "var(--bg-secondary)",
            color: "var(--text-primary)",
            fontSize: "0.85rem",
          }}
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
        </select>
      </div>

      {error && (
        <div
          style={{
            marginBottom: 16,
            padding: "10px 14px",
            borderRadius: 8,
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.2)",
            color: "var(--red, #ef4444)",
            fontSize: "0.85rem",
          }}
        >
          {error}
        </div>
      )}

      {/* Stats cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 12,
          marginBottom: 20,
        }}
      >
        {/* Average Rating */}
        <div
          style={{
            background: "var(--bg-card)",
            padding: 16,
            borderRadius: 10,
            border: "1px solid var(--border-color)",
          }}
        >
          {loadingStats ? (
            <div style={{ height: 48, borderRadius: 6, background: "var(--bg-secondary)" }} />
          ) : (
            <>
              <div
                style={{ fontSize: "1.9rem", fontWeight: 700, color: "var(--text-primary)" }}
              >
                {stats?.avg_rating ?? "-"}
              </div>
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: 4 }}>
                Avg Rating
              </div>
              <Stars rating={Math.round(stats?.avg_rating || 0)} />
            </>
          )}
        </div>

        {/* NPS Score */}
        <div
          style={{
            background: "var(--bg-card)",
            padding: 16,
            borderRadius: 10,
            border: "1px solid var(--border-color)",
          }}
        >
          {loadingStats ? (
            <div style={{ height: 48, borderRadius: 6, background: "var(--bg-secondary)" }} />
          ) : (
            <>
              <div
                style={{
                  fontSize: "1.9rem",
                  fontWeight: 700,
                  color: npsColor(stats?.nps ?? 0),
                }}
              >
                {stats?.nps ?? "-"}
              </div>
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                NPS Score
              </div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: 4 }}>
                {stats?.nps >= 50
                  ? "Excellent"
                  : stats?.nps >= 0
                  ? "Good"
                  : "Needs improvement"}
              </div>
            </>
          )}
        </div>

        {/* Total Responses */}
        <div
          style={{
            background: "var(--bg-card)",
            padding: 16,
            borderRadius: 10,
            border: "1px solid var(--border-color)",
          }}
        >
          {loadingStats ? (
            <div style={{ height: 48, borderRadius: 6, background: "var(--bg-secondary)" }} />
          ) : (
            <>
              <div
                style={{ fontSize: "1.9rem", fontWeight: 700, color: "var(--text-primary)" }}
              >
                {stats?.total ?? 0}
              </div>
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                Total Responses
              </div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: 4 }}>
                in selected period
              </div>
            </>
          )}
        </div>
      </div>

      {/* Charts */}
      {!loadingStats && stats && stats.total > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 16,
            marginBottom: 20,
          }}
        >
          {/* Rating Distribution */}
          <div
            style={{
              background: "var(--bg-card)",
              padding: 16,
              borderRadius: 10,
              border: "1px solid var(--border-color)",
            }}
          >
            <h4
              style={{ margin: "0 0 12px", color: "var(--text-primary)", fontSize: "0.9rem" }}
            >
              Rating Distribution
            </h4>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={distributionData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <XAxis
                  dataKey="star"
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border-color)",
                    borderRadius: 6,
                    color: "var(--text-primary)",
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} fill="#4ade80" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Daily Trend */}
          <div
            style={{
              background: "var(--bg-card)",
              padding: 16,
              borderRadius: 10,
              border: "1px solid var(--border-color)",
            }}
          >
            <h4
              style={{ margin: "0 0 12px", color: "var(--text-primary)", fontSize: "0.9rem" }}
            >
              Satisfaction Trend
            </h4>
            {trendData.length > 1 ? (
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={trendData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                    tickLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    domain={[0, 5]}
                    tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "var(--bg-secondary)",
                      border: "1px solid var(--border-color)",
                      borderRadius: 6,
                      color: "var(--text-primary)",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="avg"
                    stroke="#4ade80"
                    strokeWidth={2}
                    name="Avg Rating"
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div
                style={{
                  textAlign: "center",
                  padding: 40,
                  color: "var(--text-muted)",
                  fontSize: "0.85rem",
                }}
              >
                Need responses from 2+ days to show a trend.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Response list */}
      <div
        style={{
          background: "var(--bg-card)",
          borderRadius: 10,
          border: "1px solid var(--border-color)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "14px 16px",
            borderBottom: "1px solid var(--border-color)",
          }}
        >
          <h3 style={{ margin: 0, fontSize: "0.95rem", color: "var(--text-primary)" }}>
            Survey Responses
          </h3>
        </div>

        {loadingResponses ? (
          <div
            style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-muted)" }}
          >
            Loading responses...
          </div>
        ) : responses.length === 0 ? (
          <div style={{ textAlign: "center", padding: "3rem 2rem" }}>
            <div
              style={{ fontSize: "2.5rem", marginBottom: "0.75rem", color: "var(--text-muted)" }}
            >
              &#9734;
            </div>
            <h3 style={{ margin: "0 0 0.5rem", color: "var(--text-primary)" }}>
              No survey responses yet
            </h3>
            <p style={{ color: "var(--text-muted)", maxWidth: 400, margin: "0 auto" }}>
              CSAT surveys are automatically sent to customers after conversations end.
              Once customers submit ratings, they will appear here.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.85rem",
              }}
            >
              <thead>
                <tr
                  style={{
                    background: "var(--bg-secondary)",
                    borderBottom: "1px solid var(--border-color)",
                  }}
                >
                  <th
                    style={{
                      padding: "10px 16px",
                      textAlign: "left",
                      fontWeight: 600,
                      color: "var(--text-secondary)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    Date
                  </th>
                  <th
                    style={{
                      padding: "10px 16px",
                      textAlign: "left",
                      fontWeight: 600,
                      color: "var(--text-secondary)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    Rating
                  </th>
                  <th
                    style={{
                      padding: "10px 16px",
                      textAlign: "left",
                      fontWeight: 600,
                      color: "var(--text-secondary)",
                    }}
                  >
                    Feedback
                  </th>
                  <th
                    style={{
                      padding: "10px 16px",
                      textAlign: "left",
                      fontWeight: 600,
                      color: "var(--text-secondary)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    Channel
                  </th>
                </tr>
              </thead>
              <tbody>
                {responses.map((r) => (
                  <tr
                    key={r.id}
                    style={{
                      borderBottom: "1px solid var(--border-color)",
                      transition: "background 0.1s",
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.background = "var(--hover-overlay)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background = "transparent")
                    }
                  >
                    <td
                      style={{
                        padding: "10px 16px",
                        color: "var(--text-muted)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {formatDate(r.created_at)}
                    </td>
                    <td style={{ padding: "10px 16px", whiteSpace: "nowrap" }}>
                      <Stars rating={r.rating} />
                      <span
                        style={{
                          marginLeft: 6,
                          fontSize: "0.8rem",
                          color: "var(--text-muted)",
                        }}
                      >
                        {r.rating}/5
                      </span>
                    </td>
                    <td style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>
                      {r.feedback ? (
                        r.feedback
                      ) : (
                        <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
                          No comment
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      <span
                        style={{
                          padding: "2px 8px",
                          borderRadius: 10,
                          fontSize: "0.72rem",
                          background: "var(--accent-dim, rgba(0,191,255,0.12))",
                          color: "var(--accent, #00BFFF)",
                          textTransform: "capitalize",
                        }}
                      >
                        {r.channel || "email"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
