import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { apiFetch, cardStyle } from "./utils";

export default function ResultsPanel({ test, onClose }) {
  const { user, token } = useAuth();
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user?.tenantId || !token || !test?.id) return;
    setLoading(true);
    apiFetch(`/ab-tests/${user.tenantId}/${test.id}/results`, token)
      .then(setResults)
      .catch(() => setResults(null))
      .finally(() => setLoading(false));
  }, [user?.tenantId, token, test?.id]);

  const chartData =
    results?.variants?.map((v) => ({
      name: v.variant?.name || v.name || "Unknown",
      open_rate: v.metrics?.open_rate ?? v.open_rate ?? 0,
      click_rate: v.metrics?.click_rate ?? v.click_rate ?? 0,
      sent: v.metrics?.sent ?? v.sent ?? 0,
    })) || [];

  return (
    <div style={{ ...cardStyle, marginTop: 24 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 20,
        }}
      >
        <div>
          <h2
            style={{
              margin: 0,
              fontSize: "1.2rem",
              color: "var(--text-primary)",
            }}
          >
            Results: {test.name}
          </h2>
          <p
            style={{
              fontSize: "0.85rem",
              color: "var(--text-secondary)",
              margin: "4px 0 0",
            }}
          >
            {test.test_type?.replace("_", " ")} Test
          </p>
        </div>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "var(--text-muted)",
            cursor: "pointer",
            fontSize: "1.2rem",
          }}
        >
          &#x2715;
        </button>
      </div>

      {loading ? (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "var(--text-secondary)",
          }}
        >
          Loading results...
        </div>
      ) : results ? (
        <>
          {results.winner && (
            <div
              style={{
                background: "var(--green-dim)",
                border: "1px solid var(--green)",
                borderRadius: 8,
                padding: "12px 16px",
                marginBottom: 20,
                color: "var(--green)",
                fontWeight: 600,
              }}
            >
              Winner: {results.winner.name} (confidence:{" "}
              {results.winner.confidence
                ? `${(results.winner.confidence * 100).toFixed(1)}%`
                : "N/A"}
              )
            </div>
          )}

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: 12,
              marginBottom: 20,
            }}
          >
            {(results.variants || []).map((v) => {
              const metrics = v.metrics || {};
              const variant = v.variant || {};
              const isWinner = v.is_winner || variant.is_winner || false;
              return (
                <div
                  key={v.variant?.id || v.id}
                  style={{
                    background: isWinner
                      ? "var(--green-dim)"
                      : "var(--bg-primary)",
                    border: `1px solid ${isWinner ? "var(--green)" : "var(--border)"}`,
                    borderRadius: 8,
                    padding: "16px 20px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 8,
                    }}
                  >
                    <span
                      style={{ fontWeight: 700, color: "var(--text-primary)" }}
                    >
                      {variant.name || v.name || "Unknown"}
                    </span>
                    {isWinner && (
                      <span
                        style={{
                          color: "var(--green)",
                          fontSize: "0.75rem",
                          fontWeight: 600,
                        }}
                      >
                        WINNER
                      </span>
                    )}
                  </div>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr 1fr",
                      gap: 8,
                      fontSize: "0.85rem",
                    }}
                  >
                    <div>
                      <div
                        style={{ color: "var(--text-muted)", marginBottom: 2 }}
                      >
                        Sent
                      </div>
                      <div
                        style={{
                          fontWeight: 600,
                          color: "var(--text-primary)",
                        }}
                      >
                        {metrics.sent ?? 0}
                      </div>
                    </div>
                    <div>
                      <div
                        style={{ color: "var(--text-muted)", marginBottom: 2 }}
                      >
                        Open Rate
                      </div>
                      <div style={{ fontWeight: 600, color: "var(--accent)" }}>
                        {metrics.open_rate != null
                          ? `${metrics.open_rate.toFixed(1)}%`
                          : "--"}
                      </div>
                    </div>
                    <div>
                      <div
                        style={{ color: "var(--text-muted)", marginBottom: 2 }}
                      >
                        Click Rate
                      </div>
                      <div style={{ fontWeight: 600, color: "var(--green)" }}>
                        {metrics.click_rate != null
                          ? `${metrics.click_rate.toFixed(1)}%`
                          : "--"}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {chartData.length > 0 && (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData}>
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
                <Bar
                  dataKey="open_rate"
                  fill="var(--accent)"
                  radius={[4, 4, 0, 0]}
                  name="Open Rate"
                />
                <Bar
                  dataKey="click_rate"
                  fill="var(--green)"
                  radius={[4, 4, 0, 0]}
                  name="Click Rate"
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </>
      ) : (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "var(--text-secondary)",
          }}
        >
          No results data available yet
        </div>
      )}
    </div>
  );
}
