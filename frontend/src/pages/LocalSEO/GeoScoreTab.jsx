import { useState, useEffect, useCallback } from "react";
import SkeletonLoader from "../../components/SkeletonLoader";
import { runGeoScore, fetchGeoScore } from "../../utils/api/seo";
import { PLATFORM_CONFIG } from "./constants";
import { ScoreGauge, SectionHeader, Card, ErrorBanner } from "./components";

const DEFAULT_TIPS = [
  {
    title: "Claim your Google Business Profile",
    desc: "A verified GBP is the foundation for AI recommendations. Keep it updated with hours, photos, and services.",
  },
  {
    title: "Build authoritative content",
    desc: "Publish helpful, original content on your website. AI systems prioritize businesses with detailed, trustworthy information.",
  },
  {
    title: "Encourage customer reviews",
    desc: "High-quality reviews on Google, Yelp, and industry sites signal trust to AI models that curate recommendations.",
  },
  {
    title: "Use structured data markup",
    desc: "Add Schema.org markup (LocalBusiness, FAQ, Review) so AI systems can reliably parse your business information.",
  },
  {
    title: "Get mentioned on authoritative sites",
    desc: "Citations on directories, industry publications, and local news help AI models discover and trust your business.",
  },
];

export default function GeoScoreTab({ tenantId, token }) {
  const [geoData, setGeoData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  const loadGeo = useCallback(async () => {
    if (!tenantId) return;
    try {
      const data = await fetchGeoScore(tenantId, token);
      if (data) setGeoData(data);
    } catch (err) {
      console.warn("No GEO score data yet:", err.message);
    } finally {
      setLoading(false);
    }
  }, [tenantId, token]);

  useEffect(() => {
    setLoading(true);
    loadGeo();
  }, [loadGeo]);

  const handleCheck = async () => {
    setRunning(true);
    setError(null);
    try {
      const result = await runGeoScore(tenantId, token);
      setGeoData(result);
    } catch (err) {
      setError(
        err.body?.detail ||
          err.message ||
          "GEO score check failed. Make sure your business is set up.",
      );
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <SkeletonLoader />;

  if (!geoData) {
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
          <path d="M12 2a10 10 0 1 0 10 10" />
          <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
          <path d="M2 12h10" />
          <path d="M16 6l5-3v8l-5 3V6z" />
        </svg>
        <h3 style={{ color: "var(--text-primary)", margin: "0 0 8px" }}>
          Check Your AI Visibility
        </h3>
        <p style={{ maxWidth: 520, margin: "0 auto 20px", lineHeight: 1.6 }}>
          GEO (Generative Engine Optimization) measures how visible your
          business is to AI assistants like ChatGPT, Claude, Perplexity, and
          Gemini. Find out if AI recommends your business when potential
          customers ask for services you provide.
        </p>
        <ErrorBanner error={error} onDismiss={() => setError(null)} />
        <button
          className="btn-primary"
          onClick={handleCheck}
          disabled={running}
          style={{ opacity: running ? 0.6 : 1 }}
        >
          {running ? "Checking AI Visibility..." : "Check AI Visibility"}
        </button>
      </div>
    );
  }

  const overallGeo = geoData.overall_score ?? geoData.score ?? 0;
  const platforms = geoData.platforms || {};
  const factors = geoData.visibility_factors || geoData.factors || [];
  const tips = geoData.tips || geoData.recommendations || [];

  return (
    <div>
      <ErrorBanner error={error} onDismiss={() => setError(null)} />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "260px 1fr",
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
          <ScoreGauge score={overallGeo} label="GEO Score" />
          <div
            style={{
              marginTop: 12,
              fontSize: "0.85rem",
              color: "var(--text-secondary)",
              textAlign: "center",
            }}
          >
            {overallGeo >= 70
              ? "Strong AI visibility! AI assistants are likely recommending your business."
              : overallGeo >= 40
                ? "Moderate visibility. There are opportunities to increase AI recommendations."
                : "Low AI visibility. AI assistants may not be aware of your business yet."}
          </div>
          <button
            className="btn-primary"
            onClick={handleCheck}
            disabled={running}
            style={{ marginTop: 16, opacity: running ? 0.6 : 1, width: "100%" }}
          >
            {running ? "Checking..." : "Re-check Visibility"}
          </button>
        </Card>

        <Card>
          <SectionHeader>Platform Breakdown</SectionHeader>
          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}
          >
            {Object.entries(PLATFORM_CONFIG).map(([key, config]) => {
              const platformData = platforms[key] || {};
              const platformScore =
                platformData.score ?? platformData.visibility ?? null;

              let barColor = "var(--border)";
              if (platformScore !== null) {
                if (platformScore >= 70) barColor = "#22c55e";
                else if (platformScore >= 40) barColor = "#f59e0b";
                else barColor = "#ef4444";
              }

              return (
                <div
                  key={key}
                  style={{
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border)",
                    borderRadius: 10,
                    padding: "16px",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: "50%",
                      background: `${config.color}20`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "1.2rem",
                      fontWeight: 700,
                      color: config.color,
                    }}
                  >
                    {config.label.charAt(0)}
                  </div>
                  <div
                    style={{
                      fontWeight: 600,
                      fontSize: "0.85rem",
                      color: "var(--text-primary)",
                    }}
                  >
                    {config.label}
                  </div>
                  {platformScore !== null ? (
                    <>
                      <div
                        style={{
                          fontWeight: 700,
                          fontSize: "1.5rem",
                          color: barColor,
                        }}
                      >
                        {platformScore}
                      </div>
                      <div
                        style={{
                          width: "100%",
                          height: 4,
                          background: "var(--border)",
                          borderRadius: 2,
                        }}
                      >
                        <div
                          style={{
                            height: "100%",
                            width: `${platformScore}%`,
                            background: barColor,
                            borderRadius: 2,
                            transition: "width 0.6s ease",
                          }}
                        />
                      </div>
                    </>
                  ) : (
                    <div
                      style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}
                    >
                      Not scored
                    </div>
                  )}
                  {platformData.status && (
                    <div
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--text-muted)",
                        textAlign: "center",
                      }}
                    >
                      {platformData.status}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {factors.length > 0 && (
        <Card style={{ marginBottom: 24 }}>
          <SectionHeader>Visibility Factors</SectionHeader>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {factors.map((factor, idx) => {
              const status = factor.status || "neutral";
              const color =
                status === "good" || status === "positive"
                  ? "#22c55e"
                  : status === "bad" || status === "negative"
                    ? "#ef4444"
                    : "#f59e0b";
              return (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10,
                    padding: "10px 14px",
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    borderLeft: `3px solid ${color}`,
                  }}
                >
                  <span
                    style={{
                      color,
                      fontWeight: 700,
                      fontSize: "0.9rem",
                      flexShrink: 0,
                    }}
                  >
                    {status === "good" || status === "positive"
                      ? "✓"
                      : status === "bad" || status === "negative"
                        ? "✗"
                        : "●"}
                  </span>
                  <div>
                    <div
                      style={{
                        fontWeight: 600,
                        fontSize: "0.85rem",
                        color: "var(--text-primary)",
                      }}
                    >
                      {factor.name || factor.factor || `Factor ${idx + 1}`}
                    </div>
                    {factor.description && (
                      <div
                        style={{
                          fontSize: "0.8rem",
                          color: "var(--text-muted)",
                          marginTop: 2,
                        }}
                      >
                        {factor.description}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      <Card>
        <SectionHeader>Tips for Improving AI Visibility</SectionHeader>
        {tips.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {tips.map((tip, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 12,
                  padding: "12px 14px",
                  background: "var(--bg-primary)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                }}
              >
                <span
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: 24,
                    height: 24,
                    borderRadius: "50%",
                    background: "rgba(139,92,246,0.15)",
                    color: "var(--purple, #8b5cf6)",
                    fontSize: "0.75rem",
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {idx + 1}
                </span>
                <div>
                  <div
                    style={{
                      fontWeight: 600,
                      fontSize: "0.85rem",
                      color: "var(--text-primary)",
                    }}
                  >
                    {tip.title || tip.name || `Tip ${idx + 1}`}
                  </div>
                  <div
                    style={{
                      fontSize: "0.8rem",
                      color: "var(--text-secondary)",
                      marginTop: 2,
                      lineHeight: 1.5,
                    }}
                  >
                    {tip.description || tip.text || tip}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {DEFAULT_TIPS.map((tip, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 12,
                  padding: "12px 14px",
                  background: "var(--bg-primary)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                }}
              >
                <span
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: 24,
                    height: 24,
                    borderRadius: "50%",
                    background: "rgba(139,92,246,0.15)",
                    color: "var(--purple, #8b5cf6)",
                    fontSize: "0.75rem",
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {idx + 1}
                </span>
                <div>
                  <div
                    style={{
                      fontWeight: 600,
                      fontSize: "0.85rem",
                      color: "var(--text-primary)",
                    }}
                  >
                    {tip.title}
                  </div>
                  <div
                    style={{
                      fontSize: "0.8rem",
                      color: "var(--text-secondary)",
                      marginTop: 2,
                      lineHeight: 1.5,
                    }}
                  >
                    {tip.desc}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
