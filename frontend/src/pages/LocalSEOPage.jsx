import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import { analyzeSeoProfile, fetchSeoProfile, fetchSeoKeywords } from "../utils/api";

const DIFFICULTY_COLORS = {
  low: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  medium: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  high: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
};

function ScoreGauge({ score }) {
  const radius = 70;
  const stroke = 10;
  const normalizedRadius = radius - stroke / 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const safeScore = Math.max(0, Math.min(100, score || 0));
  const offset = circumference - (safeScore / 100) * circumference;

  let strokeColor = "#ef4444";
  if (safeScore >= 70) strokeColor = "#22c55e";
  else if (safeScore >= 40) strokeColor = "#f59e0b";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      <svg height={radius * 2} width={radius * 2} style={{ transform: "rotate(-90deg)" }}>
        <circle
          stroke="var(--border-color)"
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        <circle
          stroke={strokeColor}
          fill="transparent"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={offset}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
      </svg>
      <div
        style={{
          position: "relative",
          marginTop: -radius - 20,
          fontSize: "2rem",
          fontWeight: 700,
          color: strokeColor,
          height: radius * 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {safeScore}
      </div>
      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4 }}>
        Completeness Score
      </div>
    </div>
  );
}

function getDifficultyLevel(difficulty) {
  if (difficulty <= 33) return "low";
  if (difficulty <= 66) return "medium";
  return "high";
}

export default function LocalSEOPage() {
  const { user, token } = useAuth();
  const [profile, setProfile] = useState(null);
  const [keywords, setKeywords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const [profileData, keywordsData] = await Promise.all([
        fetchSeoProfile(user.tenantId, token).catch(() => null),
        fetchSeoKeywords(user.tenantId, token).catch(() => null),
      ]);
      if (profileData) setProfile(profileData);
      if (keywordsData) setKeywords(keywordsData.keywords || keywordsData || []);
      setError(null);
    } catch (err) {
      console.warn("Failed to load SEO data:", err.message);
      // Not an error state -- profile may not exist yet
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  const handleAnalyze = async () => {
    if (!user?.tenantId) return;
    setAnalyzing(true);
    setError(null);
    try {
      const result = await analyzeSeoProfile(user.tenantId, token);
      setProfile(result);
      // Reload keywords after analysis since backend may have updated them
      const keywordsData = await fetchSeoKeywords(user.tenantId, token).catch(() => null);
      if (keywordsData) setKeywords(keywordsData.keywords || keywordsData || []);
    } catch (err) {
      console.warn("SEO analysis failed:", err.message);
      setError(err.body?.detail || err.message || "Analysis failed. Make sure your business profile is set up.");
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) return <SkeletonLoader />;

  const score = profile?.completeness_score ?? 0;
  const missingFields = profile?.missing_fields || [];
  const recommendations = profile?.recommendations || [];

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Local SEO</h1>
          <p>Optimize your local search presence and attract nearby customers</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            className="btn-primary"
            onClick={() => {
              setLoading(true);
              loadData();
            }}
            style={{
              background: "transparent",
              border: "1px solid var(--border-color)",
              color: "var(--text-primary)",
            }}
          >
            Refresh
          </button>
          <button
            className="btn-primary"
            onClick={handleAnalyze}
            disabled={analyzing}
            style={{ opacity: analyzing ? 0.6 : 1 }}
          >
            {analyzing ? "Analyzing..." : "Analyze My Profile"}
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            marginBottom: 16,
            padding: "10px 16px",
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 8,
            color: "#ef4444",
            fontSize: "0.85rem",
          }}
        >
          {error}
          <button
            onClick={() => setError(null)}
            style={{
              marginLeft: 12,
              background: "none",
              border: "none",
              color: "#ef4444",
              cursor: "pointer",
              fontSize: "0.8rem",
              textDecoration: "underline",
            }}
          >
            dismiss
          </button>
        </div>
      )}

      {/* No profile yet -- empty state */}
      {!profile ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--text-muted)" }}>
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
          </div>
          <h3 style={{ color: "var(--text-primary)", margin: "0 0 8px" }}>No SEO analysis yet</h3>
          <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
            Run an analysis to check your business profile completeness, get keyword suggestions,
            and receive actionable recommendations to improve your local search ranking.
          </p>
          <button
            className="btn-primary"
            onClick={handleAnalyze}
            disabled={analyzing}
            style={{ opacity: analyzing ? 0.6 : 1 }}
          >
            {analyzing ? "Analyzing..." : "Run Your First Analysis"}
          </button>
        </div>
      ) : (
        <>
          {/* Score + Missing Fields Row */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "280px 1fr",
              gap: 16,
              marginBottom: 24,
            }}
          >
            {/* Score Card */}
            <div
              style={{
                background: "var(--bg-secondary)",
                border: "1px solid var(--border-color)",
                borderRadius: 12,
                padding: "24px 20px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <ScoreGauge score={score} />
              <div
                style={{
                  marginTop: 12,
                  fontSize: "0.85rem",
                  color: "var(--text-secondary)",
                  textAlign: "center",
                }}
              >
                {score >= 80
                  ? "Great! Your profile is well optimized."
                  : score >= 50
                  ? "Good start. A few improvements can boost your ranking."
                  : "Your profile needs attention to rank well locally."}
              </div>
            </div>

            {/* Missing Fields */}
            <div
              style={{
                background: "var(--bg-secondary)",
                border: "1px solid var(--border-color)",
                borderRadius: 12,
                padding: "20px 24px",
              }}
            >
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "var(--text-muted)",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  marginBottom: 12,
                }}
              >
                Missing or Incomplete Fields
              </div>
              {missingFields.length === 0 ? (
                <div
                  style={{
                    color: "#22c55e",
                    fontSize: "0.9rem",
                    padding: "20px 0",
                    textAlign: "center",
                  }}
                >
                  All fields are complete -- nice work!
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {missingFields.map((field, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 10,
                        padding: "8px 12px",
                        background: "rgba(239,68,68,0.05)",
                        border: "1px solid rgba(239,68,68,0.15)",
                        borderRadius: 8,
                      }}
                    >
                      <span
                        style={{
                          color: "#ef4444",
                          fontSize: "0.8rem",
                          fontWeight: 700,
                          flexShrink: 0,
                          marginTop: 1,
                        }}
                      >
                        !
                      </span>
                      <div>
                        <div
                          style={{
                            fontWeight: 600,
                            fontSize: "0.85rem",
                            color: "var(--text-primary)",
                          }}
                        >
                          {field.name || field.field || field}
                        </div>
                        {(field.suggestion || field.fix) && (
                          <div
                            style={{
                              fontSize: "0.8rem",
                              color: "var(--text-muted)",
                              marginTop: 2,
                            }}
                          >
                            {field.suggestion || field.fix}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Keyword Suggestions */}
          <div
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-color)",
              borderRadius: 12,
              padding: "20px 24px",
              marginBottom: 24,
            }}
          >
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: 12,
              }}
            >
              Keyword Suggestions
            </div>
            {keywords.length === 0 ? (
              <div
                style={{
                  textAlign: "center",
                  padding: "30px 20px",
                  color: "var(--text-muted)",
                }}
              >
                <p style={{ margin: "0 0 8px", fontSize: "0.9rem" }}>
                  No keyword suggestions yet
                </p>
                <p style={{ margin: 0, fontSize: "0.8rem" }}>
                  Run an analysis to get keyword recommendations tailored to your business and location.
                </p>
              </div>
            ) : (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
                  gap: 10,
                }}
              >
                {keywords.map((kw, idx) => {
                  const diffLevel = getDifficultyLevel(kw.difficulty ?? 50);
                  const diffStyle = DIFFICULTY_COLORS[diffLevel];
                  return (
                    <div
                      key={idx}
                      style={{
                        background: "var(--bg-primary)",
                        border: "1px solid var(--border-color)",
                        borderRadius: 8,
                        padding: "12px 14px",
                      }}
                    >
                      <div
                        style={{
                          fontWeight: 600,
                          fontSize: "0.9rem",
                          color: "var(--text-primary)",
                          marginBottom: 6,
                        }}
                      >
                        {kw.keyword}
                      </div>
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <span
                          style={{
                            fontSize: "0.75rem",
                            color: "var(--text-muted)",
                          }}
                        >
                          Vol: {kw.search_volume ?? "N/A"}
                        </span>
                        <span
                          style={{
                            display: "inline-block",
                            padding: "1px 8px",
                            borderRadius: 4,
                            fontSize: "0.7rem",
                            fontWeight: 600,
                            color: diffStyle.color,
                            background: diffStyle.bg,
                            textTransform: "capitalize",
                          }}
                        >
                          {diffLevel}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recommendations */}
          <div
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-color)",
              borderRadius: 12,
              padding: "20px 24px",
            }}
          >
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: 12,
              }}
            >
              Recommendations
            </div>
            {recommendations.length === 0 ? (
              <div
                style={{
                  textAlign: "center",
                  padding: "20px",
                  color: "var(--text-muted)",
                  fontSize: "0.85rem",
                }}
              >
                No recommendations at this time. Your profile looks good!
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {recommendations.map((rec, idx) => {
                  const priorityColor =
                    rec.priority === "high"
                      ? "#ef4444"
                      : rec.priority === "medium"
                      ? "#f59e0b"
                      : "#3b82f6";
                  return (
                    <div
                      key={idx}
                      style={{
                        background: "var(--bg-primary)",
                        border: "1px solid var(--border-color)",
                        borderRadius: 10,
                        borderLeft: `4px solid ${priorityColor}`,
                        padding: "14px 16px",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "flex-start",
                          marginBottom: 4,
                        }}
                      >
                        <div
                          style={{
                            fontWeight: 600,
                            fontSize: "0.9rem",
                            color: "var(--text-primary)",
                          }}
                        >
                          {rec.title || rec.name || `Recommendation ${idx + 1}`}
                        </div>
                        {rec.priority && (
                          <span
                            style={{
                              padding: "2px 8px",
                              borderRadius: 4,
                              fontSize: "0.7rem",
                              fontWeight: 600,
                              color: priorityColor,
                              background:
                                rec.priority === "high"
                                  ? "rgba(239,68,68,0.1)"
                                  : rec.priority === "medium"
                                  ? "rgba(245,158,11,0.1)"
                                  : "rgba(59,130,246,0.1)",
                              textTransform: "capitalize",
                            }}
                          >
                            {rec.priority}
                          </span>
                        )}
                      </div>
                      <div
                        style={{
                          fontSize: "0.85rem",
                          color: "var(--text-secondary)",
                          lineHeight: 1.5,
                        }}
                      >
                        {rec.description || rec.text || rec}
                      </div>
                      {rec.action && (
                        <div
                          style={{
                            marginTop: 6,
                            fontSize: "0.8rem",
                            color: "var(--accent)",
                            fontWeight: 500,
                          }}
                        >
                          Action: {rec.action}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
