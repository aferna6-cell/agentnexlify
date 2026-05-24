import { useState } from "react";
import { runCompetitorAnalysis } from "../../utils/api/seo";

const THREAT_COLORS = {
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#22c55e",
};

export default function CompetitorTab({ tenantId, token }) {
  const [competitors, setCompetitors] = useState(["", "", ""]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleCompetitorChange = (idx, value) => {
    const updated = [...competitors];
    updated[idx] = value;
    setCompetitors(updated);
  };

  const addSlot = () => {
    if (competitors.length < 5) setCompetitors([...competitors, ""]);
  };

  const handleAnalyze = async () => {
    const names = competitors.filter((c) => c.trim());
    if (!names.length) return;
    setLoading(true);
    setError(null);
    try {
      const data = await runCompetitorAnalysis(tenantId, token, names);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h3 style={{ margin: "0 0 8px", fontSize: 16 }}>Competitor Analysis</h3>
      <p
        style={{
          color: "var(--text-secondary)",
          fontSize: 13,
          marginBottom: 20,
        }}
      >
        Enter competitor business names to get an AI-powered comparison of your
        online presence.
      </p>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 8,
          marginBottom: 16,
        }}
      >
        {competitors.map((c, i) => (
          <input
            key={i}
            type="text"
            value={c}
            onChange={(e) => handleCompetitorChange(i, e.target.value)}
            placeholder={`Competitor ${i + 1} name`}
            className="settings-input"
            style={{ maxWidth: 400 }}
          />
        ))}
        {competitors.length < 5 && (
          <button
            onClick={addSlot}
            style={{
              alignSelf: "flex-start",
              background: "none",
              border: "none",
              color: "var(--accent)",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            + Add competitor
          </button>
        )}
      </div>

      <button
        className="btn-primary"
        onClick={handleAnalyze}
        disabled={loading || !competitors.some((c) => c.trim())}
        style={{ marginBottom: 24 }}
      >
        {loading ? "Analyzing..." : "Analyze Competitors"}
      </button>

      {error && (
        <div
          style={{
            padding: 12,
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: 8,
            color: "#fca5a5",
            fontSize: 13,
            marginBottom: 16,
          }}
        >
          {error}
        </div>
      )}

      {result && (
        <div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 12,
              marginBottom: 24,
            }}
          >
            {result.your_business && (
              <div
                style={{
                  padding: 16,
                  background: "rgba(99,102,241,0.08)",
                  border: "1px solid rgba(99,102,241,0.2)",
                  borderRadius: 10,
                }}
              >
                <div
                  style={{
                    fontSize: 13,
                    color: "var(--text-secondary)",
                    marginBottom: 4,
                  }}
                >
                  Your Business
                </div>
                <div
                  style={{
                    fontSize: 28,
                    fontWeight: 700,
                    color: "var(--accent)",
                  }}
                >
                  {result.your_business.estimated_score}
                </div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  {result.your_business.name}
                </div>
              </div>
            )}
            {(result.competitors || []).map((comp, i) => (
              <div
                key={i}
                style={{
                  padding: 16,
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                  borderRadius: 10,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 4,
                  }}
                >
                  <span
                    style={{ fontSize: 13, color: "var(--text-secondary)" }}
                  >
                    Competitor
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: THREAT_COLORS[comp.threat_level] || "#888",
                      textTransform: "uppercase",
                    }}
                  >
                    {comp.threat_level}
                  </span>
                </div>
                <div
                  style={{
                    fontSize: 28,
                    fontWeight: 700,
                    color: "var(--text-primary)",
                  }}
                >
                  {comp.estimated_score}
                </div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  {comp.name}
                </div>
              </div>
            ))}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              marginBottom: 24,
            }}
          >
            {result.gaps?.length > 0 && (
              <div
                style={{
                  padding: 16,
                  background: "rgba(239,68,68,0.05)",
                  border: "1px solid rgba(239,68,68,0.15)",
                  borderRadius: 10,
                }}
              >
                <h4
                  style={{ margin: "0 0 10px", fontSize: 14, color: "#fca5a5" }}
                >
                  Gaps to Close
                </h4>
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: 16,
                    fontSize: 13,
                    color: "var(--text-secondary)",
                    lineHeight: 1.6,
                  }}
                >
                  {result.gaps.map((g, i) => (
                    <li key={i}>{g}</li>
                  ))}
                </ul>
              </div>
            )}
            {result.advantages?.length > 0 && (
              <div
                style={{
                  padding: 16,
                  background: "rgba(34,197,94,0.05)",
                  border: "1px solid rgba(34,197,94,0.15)",
                  borderRadius: 10,
                }}
              >
                <h4
                  style={{ margin: "0 0 10px", fontSize: 14, color: "#86efac" }}
                >
                  Your Advantages
                </h4>
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: 16,
                    fontSize: 13,
                    color: "var(--text-secondary)",
                    lineHeight: 1.6,
                  }}
                >
                  {result.advantages.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {result.recommendations?.length > 0 && (
            <div
              style={{
                padding: 16,
                background: "var(--bg-secondary)",
                border: "1px solid var(--border)",
                borderRadius: 10,
              }}
            >
              <h4 style={{ margin: "0 0 10px", fontSize: 14 }}>
                Recommended Actions
              </h4>
              <ol
                style={{
                  margin: 0,
                  paddingLeft: 20,
                  fontSize: 13,
                  color: "var(--text-secondary)",
                  lineHeight: 1.8,
                }}
              >
                {result.recommendations.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
