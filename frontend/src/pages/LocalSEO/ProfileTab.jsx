import { useState, useEffect, useCallback } from "react";
import SkeletonLoader from "../../components/SkeletonLoader";
import { fetchSeoProfile, analyzeSeoProfile } from "../../utils/api/seo";
import {
  ScoreGauge,
  SectionHeader,
  Card,
  PriorityBadge,
  ErrorBanner,
} from "./components";

export default function ProfileTab({ tenantId, token }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState(null);

  const loadProfile = useCallback(async () => {
    if (!tenantId) return;
    try {
      const data = await fetchSeoProfile(tenantId, token);
      if (data) setProfile(data);
    } catch (err) {
      console.warn("No SEO profile data yet:", err.message);
    } finally {
      setLoading(false);
    }
  }, [tenantId, token]);

  useEffect(() => {
    setLoading(true);
    loadProfile();
  }, [loadProfile]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const result = await analyzeSeoProfile(tenantId, token);
      setProfile(result);
    } catch (err) {
      setError(err.body?.detail || err.message || "Analysis failed.");
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) return <SkeletonLoader />;

  if (!profile) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "60px 20px",
          color: "var(--text-muted)",
        }}
      >
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ color: "var(--text-muted)", marginBottom: 12 }}
        >
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
        <h3 style={{ color: "var(--text-primary)", margin: "0 0 8px" }}>
          No profile analysis yet
        </h3>
        <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
          Analyze your business profile to check completeness and get
          suggestions for improving your local search presence.
        </p>
        <ErrorBanner error={error} onDismiss={() => setError(null)} />
        <button
          className="btn-primary"
          onClick={handleAnalyze}
          disabled={analyzing}
          style={{ opacity: analyzing ? 0.6 : 1 }}
        >
          {analyzing ? "Analyzing..." : "Analyze My Profile"}
        </button>
      </div>
    );
  }

  const score = profile.completeness_score ?? 0;
  const missingFields = profile.missing_fields || [];
  const recommendations = profile.recommendations || [];

  return (
    <div>
      <ErrorBanner error={error} onDismiss={() => setError(null)} />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "280px 1fr",
          gap: 16,
          marginBottom: 24,
        }}
      >
        <Card
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <ScoreGauge score={score} label="Completeness Score" />
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
          <button
            className="btn-primary"
            onClick={handleAnalyze}
            disabled={analyzing}
            style={{
              marginTop: 16,
              opacity: analyzing ? 0.6 : 1,
              width: "100%",
            }}
          >
            {analyzing ? "Analyzing..." : "Re-analyze Profile"}
          </button>
        </Card>

        <Card>
          <SectionHeader>Missing or Incomplete Fields</SectionHeader>
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
        </Card>
      </div>

      {recommendations.length > 0 && (
        <Card>
          <SectionHeader>Recommendations</SectionHeader>
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
                    border: "1px solid var(--border)",
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
                    {rec.priority && <PriorityBadge priority={rec.priority} />}
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
        </Card>
      )}
    </div>
  );
}
