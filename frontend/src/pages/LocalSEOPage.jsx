import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import UpgradePrompt, { planBelowRequired } from "../components/UpgradePrompt";
import {
  analyzeSeoProfile,
  fetchSeoProfile,
  fetchSeoKeywords,
  runSeoAudit,
  fetchSeoAudit,
  fetchSeoAuditHistory,
  runGeoScore,
  fetchGeoScore,
  trackKeywords,
  fetchKeywordRankings,
} from "../utils/api/seo";

/* ──────────────────────────────────────────────────────────
   Constants
   ────────────────────────────────────────────────────────── */

const TABS = [
  { key: "audit", label: "SEO Audit" },
  { key: "geo", label: "GEO Score" },
  { key: "keywords", label: "Keywords" },
  { key: "profile", label: "Profile" },
];

const DIFFICULTY_COLORS = {
  low: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  medium: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  high: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
};

const CATEGORY_ICONS = {
  technical: "\u2699",
  content: "\u270E",
  on_page: "\u2611",
  link_analysis: "\u2197",
};

const CATEGORY_LABELS = {
  technical: "Technical SEO",
  content: "Content Quality",
  on_page: "On-Page SEO",
  link_analysis: "Link Analysis",
};

const PLATFORM_CONFIG = {
  chatgpt: { label: "ChatGPT", color: "#10a37f" },
  claude: { label: "Claude", color: "#d4a574" },
  perplexity: { label: "Perplexity", color: "#20b2aa" },
  gemini: { label: "Gemini", color: "#4285f4" },
};

/* ──────────────────────────────────────────────────────────
   Shared Components
   ────────────────────────────────────────────────────────── */

function ScoreGauge({ score, label = "Score", size = 70 }) {
  const radius = size;
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
        {label}
      </div>
    </div>
  );
}

function SectionHeader({ children }) {
  return (
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
      {children}
    </div>
  );
}

function Card({ children, style = {} }) {
  return (
    <div
      style={{
        background: "var(--bg-secondary)",
        border: "1px solid var(--border-color)",
        borderRadius: 12,
        padding: 24,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

function PriorityBadge({ priority }) {
  const colors = {
    critical: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
    high: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
    medium: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
    low: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  };
  const c = colors[priority] || colors.medium;
  return (
    <span
      style={{
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: "0.7rem",
        fontWeight: 600,
        color: c.color,
        background: c.bg,
        textTransform: "capitalize",
      }}
    >
      {priority}
    </span>
  );
}

function ErrorBanner({ error, onDismiss }) {
  if (!error) return null;
  return (
    <div
      style={{
        marginBottom: 16,
        padding: "10px 16px",
        background: "rgba(239,68,68,0.1)",
        border: "1px solid rgba(239,68,68,0.3)",
        borderRadius: 8,
        color: "#ef4444",
        fontSize: "0.85rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <span>{error}</span>
      <button
        onClick={onDismiss}
        style={{
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
  );
}

function getDifficultyLevel(difficulty) {
  if (difficulty <= 33) return "low";
  if (difficulty <= 66) return "medium";
  return "high";
}

/* ──────────────────────────────────────────────────────────
   Tab 1: SEO Audit
   ────────────────────────────────────────────────────────── */

function SeoAuditTab({ tenantId, token }) {
  const [audit, setAudit] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  const loadAudit = useCallback(async () => {
    if (!tenantId) return;
    try {
      const [auditData, historyData] = await Promise.allSettled([
        fetchSeoAudit(tenantId, token),
        fetchSeoAuditHistory(tenantId, token),
      ]);
      if (auditData.status === "fulfilled") setAudit(auditData.value);
      if (historyData.status === "fulfilled") {
        setHistory(historyData.value?.audits || historyData.value || []);
      }
    } catch (err) {
      // No audit yet is not an error
      console.warn("No SEO audit data yet:", err.message);
    } finally {
      setLoading(false);
    }
  }, [tenantId, token]);

  useEffect(() => {
    setLoading(true);
    loadAudit();
  }, [loadAudit]);

  const handleRunAudit = async () => {
    setRunning(true);
    setError(null);
    try {
      const result = await runSeoAudit(tenantId, token);
      setAudit(result);
      // Reload history
      const historyData = await fetchSeoAuditHistory(tenantId, token).catch(() => null);
      if (historyData) setHistory(historyData.audits || historyData || []);
    } catch (err) {
      setError(err.body?.detail || err.message || "Audit failed. Make sure your website URL is configured.");
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <SkeletonLoader />;

  if (!audit) {
    return (
      <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--text-muted)", marginBottom: 12 }}>
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
          <path d="M8 11h6" />
          <path d="M11 8v6" />
        </svg>
        <h3 style={{ color: "var(--text-primary)", margin: "0 0 8px" }}>No SEO audit yet</h3>
        <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
          Run a comprehensive SEO audit to check your website's technical health, content quality,
          on-page optimization, and link structure. Get actionable recommendations to improve your search rankings.
        </p>
        <ErrorBanner error={error} onDismiss={() => setError(null)} />
        <button
          className="btn-primary"
          onClick={handleRunAudit}
          disabled={running}
          style={{ opacity: running ? 0.6 : 1 }}
        >
          {running ? "Running Audit..." : "Run Your First SEO Audit"}
        </button>
      </div>
    );
  }

  const overallScore = audit.overall_score ?? audit.score ?? 0;
  const categories = audit.categories || {};
  const recommendations = audit.recommendations || [];
  const categoryKeys = Object.keys(categories).length > 0
    ? Object.keys(categories)
    : ["technical", "content", "on_page", "link_analysis"];

  return (
    <div>
      <ErrorBanner error={error} onDismiss={() => setError(null)} />

      {/* Score + Summary Row */}
      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 16, marginBottom: 24 }}>
        <Card style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <ScoreGauge score={overallScore} label="Overall SEO Score" />
          <div style={{ marginTop: 12, fontSize: "0.85rem", color: "var(--text-secondary)", textAlign: "center" }}>
            {overallScore >= 80
              ? "Excellent! Your site is well optimized for search engines."
              : overallScore >= 60
              ? "Good foundation. Some improvements can boost your rankings."
              : overallScore >= 40
              ? "Needs work. Several issues are holding back your SEO."
              : "Critical attention needed. Major SEO issues detected."}
          </div>
          <button
            className="btn-primary"
            onClick={handleRunAudit}
            disabled={running}
            style={{ marginTop: 16, opacity: running ? 0.6 : 1, width: "100%" }}
          >
            {running ? "Running..." : "Re-run Audit"}
          </button>
        </Card>

        {/* Category Scores */}
        <Card>
          <SectionHeader>Category Breakdown</SectionHeader>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {categoryKeys.map((key) => {
              const cat = categories[key] || {};
              const catScore = cat.score ?? 0;
              const issues = cat.issues || [];
              const critical = issues.filter((i) => i.severity === "critical" || i.severity === "error").length;
              const warnings = issues.filter((i) => i.severity === "warning").length;
              const passed = issues.filter((i) => i.severity === "pass" || i.severity === "good").length;

              let barColor = "#ef4444";
              if (catScore >= 70) barColor = "#22c55e";
              else if (catScore >= 40) barColor = "#f59e0b";

              return (
                <div
                  key={key}
                  style={{
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border-color)",
                    borderRadius: 10,
                    padding: "14px 16px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: "1.1rem" }}>{CATEGORY_ICONS[key] || "\u2022"}</span>
                      <span style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                        {CATEGORY_LABELS[key] || key.replace(/_/g, " ")}
                      </span>
                    </div>
                    <span style={{ fontWeight: 700, fontSize: "1rem", color: barColor }}>{catScore}</span>
                  </div>
                  {/* Progress bar */}
                  <div style={{ height: 6, background: "var(--border-color)", borderRadius: 3, marginBottom: 8 }}>
                    <div
                      style={{
                        height: "100%",
                        width: `${catScore}%`,
                        background: barColor,
                        borderRadius: 3,
                        transition: "width 0.6s ease",
                      }}
                    />
                  </div>
                  {/* Issue counts */}
                  <div style={{ display: "flex", gap: 12, fontSize: "0.75rem" }}>
                    {critical > 0 && (
                      <span style={{ color: "#ef4444" }}>{critical} critical</span>
                    )}
                    {warnings > 0 && (
                      <span style={{ color: "#f59e0b" }}>{warnings} warning{warnings !== 1 ? "s" : ""}</span>
                    )}
                    {passed > 0 && (
                      <span style={{ color: "#22c55e" }}>{passed} passed</span>
                    )}
                    {critical === 0 && warnings === 0 && passed === 0 && (
                      <span style={{ color: "var(--text-muted)" }}>No data</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Detailed Issues */}
      {categoryKeys.some((key) => (categories[key]?.issues || []).length > 0) && (
        <Card style={{ marginBottom: 24 }}>
          <SectionHeader>Detailed Issues</SectionHeader>
          {categoryKeys.map((key) => {
            const cat = categories[key] || {};
            const issues = cat.issues || [];
            if (issues.length === 0) return null;
            return (
              <div key={key} style={{ marginBottom: 16 }}>
                <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)", marginBottom: 8 }}>
                  {CATEGORY_LABELS[key] || key.replace(/_/g, " ")}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {issues.map((issue, idx) => {
                    const severity = issue.severity || "warning";
                    const color =
                      severity === "critical" || severity === "error"
                        ? "#ef4444"
                        : severity === "warning"
                        ? "#f59e0b"
                        : "#22c55e";
                    return (
                      <div
                        key={idx}
                        style={{
                          display: "flex",
                          alignItems: "flex-start",
                          gap: 10,
                          padding: "8px 12px",
                          background:
                            severity === "pass" || severity === "good"
                              ? "rgba(34,197,94,0.05)"
                              : severity === "warning"
                              ? "rgba(245,158,11,0.05)"
                              : "rgba(239,68,68,0.05)",
                          border: `1px solid ${color}22`,
                          borderRadius: 8,
                          borderLeft: `3px solid ${color}`,
                        }}
                      >
                        <span style={{ color, fontSize: "0.8rem", fontWeight: 700, flexShrink: 0, marginTop: 1 }}>
                          {severity === "pass" || severity === "good" ? "\u2713" : severity === "warning" ? "!" : "\u2717"}
                        </span>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 500, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                            {issue.title || issue.message || issue.description || "Issue"}
                          </div>
                          {issue.detail && (
                            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 2 }}>
                              {issue.detail}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </Card>
      )}

      {/* Recommendations */}
      <Card style={{ marginBottom: 24 }}>
        <SectionHeader>Actionable Recommendations</SectionHeader>
        {recommendations.length === 0 ? (
          <div style={{ textAlign: "center", padding: "20px", color: "var(--text-muted)", fontSize: "0.85rem" }}>
            No specific recommendations at this time. Your site looks good!
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {recommendations.map((rec, idx) => {
              const priority = rec.priority || "medium";
              const priorityColor =
                priority === "critical" || priority === "high"
                  ? "#ef4444"
                  : priority === "medium"
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
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
                    <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-primary)" }}>
                      {rec.title || rec.name || `Recommendation ${idx + 1}`}
                    </div>
                    <PriorityBadge priority={priority} />
                  </div>
                  <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    {rec.description || rec.text || rec}
                  </div>
                  {rec.action && (
                    <div style={{ marginTop: 6, fontSize: "0.8rem", color: "var(--accent)", fontWeight: 500 }}>
                      Action: {rec.action}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* Audit History */}
      {history.length > 0 && (
        <Card>
          <SectionHeader>Audit History</SectionHeader>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {history.slice(0, 10).map((entry, idx) => {
              const entryScore = entry.overall_score ?? entry.score ?? 0;
              let scoreColor = "#ef4444";
              if (entryScore >= 70) scoreColor = "#22c55e";
              else if (entryScore >= 40) scoreColor = "#f59e0b";
              const dateStr = entry.created_at
                ? new Date(entry.created_at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : `Audit #${idx + 1}`;
              return (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "10px 14px",
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border-color)",
                    borderRadius: 8,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: scoreColor,
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>{dateStr}</span>
                  </div>
                  <span style={{ fontWeight: 700, fontSize: "0.9rem", color: scoreColor }}>{entryScore}/100</span>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────────────────
   Tab 2: GEO Score (AI Visibility)
   ────────────────────────────────────────────────────────── */

function GeoScoreTab({ tenantId, token }) {
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
      // No GEO data yet is not an error
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
      setError(err.body?.detail || err.message || "GEO score check failed. Make sure your business is set up.");
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <SkeletonLoader />;

  if (!geoData) {
    return (
      <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--text-muted)", marginBottom: 12 }}>
          <path d="M12 2a10 10 0 1 0 10 10" />
          <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
          <path d="M2 12h10" />
          <path d="M16 6l5-3v8l-5 3V6z" />
        </svg>
        <h3 style={{ color: "var(--text-primary)", margin: "0 0 8px" }}>Check Your AI Visibility</h3>
        <p style={{ maxWidth: 520, margin: "0 auto 20px", lineHeight: 1.6 }}>
          GEO (Generative Engine Optimization) measures how visible your business is to AI assistants
          like ChatGPT, Claude, Perplexity, and Gemini. Find out if AI recommends your business when
          potential customers ask for services you provide.
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

      {/* Score + Platforms Row */}
      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 16, marginBottom: 24 }}>
        <Card style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <ScoreGauge score={overallGeo} label="GEO Score" />
          <div style={{ marginTop: 12, fontSize: "0.85rem", color: "var(--text-secondary)", textAlign: "center" }}>
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

        {/* Platform Cards */}
        <Card>
          <SectionHeader>Platform Breakdown</SectionHeader>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {Object.entries(PLATFORM_CONFIG).map(([key, config]) => {
              const platformData = platforms[key] || {};
              const platformScore = platformData.score ?? platformData.visibility ?? null;

              let barColor = "var(--border-color)";
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
                    border: "1px solid var(--border-color)",
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
                  <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                    {config.label}
                  </div>
                  {platformScore !== null ? (
                    <>
                      <div style={{ fontWeight: 700, fontSize: "1.5rem", color: barColor }}>
                        {platformScore}
                      </div>
                      <div style={{ width: "100%", height: 4, background: "var(--border-color)", borderRadius: 2 }}>
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
                    <div style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>Not scored</div>
                  )}
                  {platformData.status && (
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textAlign: "center" }}>
                      {platformData.status}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Visibility Factors */}
      {factors.length > 0 && (
        <Card style={{ marginBottom: 24 }}>
          <SectionHeader>Visibility Factors</SectionHeader>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {factors.map((factor, idx) => {
              const status = factor.status || "neutral";
              const color = status === "good" || status === "positive" ? "#22c55e" : status === "bad" || status === "negative" ? "#ef4444" : "#f59e0b";
              return (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10,
                    padding: "10px 14px",
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border-color)",
                    borderRadius: 8,
                    borderLeft: `3px solid ${color}`,
                  }}
                >
                  <span style={{ color, fontWeight: 700, fontSize: "0.9rem", flexShrink: 0 }}>
                    {status === "good" || status === "positive" ? "\u2713" : status === "bad" || status === "negative" ? "\u2717" : "\u25CF"}
                  </span>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                      {factor.name || factor.factor || `Factor ${idx + 1}`}
                    </div>
                    {factor.description && (
                      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 2 }}>
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

      {/* Tips for Improving */}
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
                  border: "1px solid var(--border-color)",
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
                  <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                    {tip.title || tip.name || `Tip ${idx + 1}`}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: 2, lineHeight: 1.5 }}>
                    {tip.description || tip.text || tip}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {[
              { title: "Claim your Google Business Profile", desc: "A verified GBP is the foundation for AI recommendations. Keep it updated with hours, photos, and services." },
              { title: "Build authoritative content", desc: "Publish helpful, original content on your website. AI systems prioritize businesses with detailed, trustworthy information." },
              { title: "Encourage customer reviews", desc: "High-quality reviews on Google, Yelp, and industry sites signal trust to AI models that curate recommendations." },
              { title: "Use structured data markup", desc: "Add Schema.org markup (LocalBusiness, FAQ, Review) so AI systems can reliably parse your business information." },
              { title: "Get mentioned on authoritative sites", desc: "Citations on directories, industry publications, and local news help AI models discover and trust your business." },
            ].map((tip, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 12,
                  padding: "12px 14px",
                  background: "var(--bg-primary)",
                  border: "1px solid var(--border-color)",
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
                  <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                    {tip.title}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: 2, lineHeight: 1.5 }}>
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

/* ──────────────────────────────────────────────────────────
   Tab 3: Keywords
   ────────────────────────────────────────────────────────── */

function KeywordsTab({ tenantId, token }) {
  const [keywords, setKeywords] = useState([]);
  const [rankings, setRankings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tracking, setTracking] = useState(false);
  const [newKeywords, setNewKeywords] = useState("");
  const [error, setError] = useState(null);

  const loadKeywords = useCallback(async () => {
    if (!tenantId) return;
    try {
      const [kwData, rkData] = await Promise.allSettled([
        fetchSeoKeywords(tenantId, token),
        fetchKeywordRankings(tenantId, token),
      ]);
      if (kwData.status === "fulfilled") {
        setKeywords(kwData.value?.keywords || kwData.value || []);
      }
      if (rkData.status === "fulfilled") {
        setRankings(rkData.value?.rankings || rkData.value || []);
      }
    } catch (err) {
      console.warn("Failed to load keyword data:", err.message);
    } finally {
      setLoading(false);
    }
  }, [tenantId, token]);

  useEffect(() => {
    setLoading(true);
    loadKeywords();
  }, [loadKeywords]);

  const handleTrack = async () => {
    if (!newKeywords.trim()) return;
    setTracking(true);
    setError(null);
    try {
      const keywordList = newKeywords
        .split(",")
        .map((k) => k.trim())
        .filter((k) => k.length > 0);
      await trackKeywords(tenantId, token, keywordList);
      setNewKeywords("");
      await loadKeywords();
    } catch (err) {
      setError(err.body?.detail || err.message || "Failed to track keywords.");
    } finally {
      setTracking(false);
    }
  };

  if (loading) return <SkeletonLoader />;

  const allKeywords = [
    ...rankings.map((r) => ({ ...r, source: "tracked" })),
    ...keywords
      .filter((kw) => !rankings.find((r) => r.keyword === kw.keyword))
      .map((kw) => ({ ...kw, source: "suggested" })),
  ];

  return (
    <div>
      <ErrorBanner error={error} onDismiss={() => setError(null)} />

      {/* Add Keywords Form */}
      <Card style={{ marginBottom: 24 }}>
        <SectionHeader>Track Keywords</SectionHeader>
        <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 12, marginTop: 0 }}>
          Add keywords you want to track. Separate multiple keywords with commas.
        </p>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            type="text"
            value={newKeywords}
            onChange={(e) => setNewKeywords(e.target.value)}
            placeholder="e.g., plumber near me, emergency plumbing, drain cleaning"
            style={{
              flex: 1,
              padding: "10px 14px",
              background: "var(--bg-primary)",
              border: "1px solid var(--border-color)",
              borderRadius: 8,
              color: "var(--text-primary)",
              fontSize: "0.85rem",
              outline: "none",
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleTrack();
            }}
          />
          <button
            className="btn-primary"
            onClick={handleTrack}
            disabled={tracking || !newKeywords.trim()}
            style={{ opacity: tracking || !newKeywords.trim() ? 0.6 : 1, whiteSpace: "nowrap" }}
          >
            {tracking ? "Adding..." : "Add Keywords"}
          </button>
        </div>
      </Card>

      {/* Keywords Table */}
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <SectionHeader>Keyword Rankings</SectionHeader>
          <button
            className="btn-primary"
            onClick={() => {
              setLoading(true);
              loadKeywords();
            }}
            style={{
              background: "transparent",
              border: "1px solid var(--border-color)",
              color: "var(--text-primary)",
              padding: "6px 14px",
              fontSize: "0.8rem",
            }}
          >
            Refresh Rankings
          </button>
        </div>
        {allKeywords.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-muted)" }}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--text-muted)", marginBottom: 8 }}>
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            <h3 style={{ color: "var(--text-primary)", margin: "0 0 8px", fontSize: "1rem" }}>No keywords tracked yet</h3>
            <p style={{ maxWidth: 420, margin: "0 auto", lineHeight: 1.6, fontSize: "0.85rem" }}>
              Add keywords above to start tracking your search rankings.
              You can also run an SEO Audit to get AI-suggested keywords for your business.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Keyword", "Difficulty", "Search Volume", "Est. Position", "Recommendation"].map((header) => (
                    <th
                      key={header}
                      style={{
                        textAlign: "left",
                        padding: "10px 12px",
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        color: "var(--text-muted)",
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        borderBottom: "1px solid var(--border-color)",
                      }}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {allKeywords.map((kw, idx) => {
                  const diffLevel = getDifficultyLevel(kw.difficulty ?? 50);
                  const diffStyle = DIFFICULTY_COLORS[diffLevel];
                  return (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: "1px solid var(--border-color)",
                        transition: "background 0.15s",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.02)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                    >
                      <td style={{ padding: "12px", fontSize: "0.9rem", fontWeight: 600, color: "var(--text-primary)" }}>
                        {kw.keyword}
                        {kw.source === "suggested" && (
                          <span
                            style={{
                              marginLeft: 8,
                              padding: "1px 6px",
                              borderRadius: 4,
                              fontSize: "0.65rem",
                              fontWeight: 500,
                              color: "var(--purple, #8b5cf6)",
                              background: "rgba(139,92,246,0.1)",
                            }}
                          >
                            suggested
                          </span>
                        )}
                      </td>
                      <td style={{ padding: "12px" }}>
                        <span
                          style={{
                            display: "inline-block",
                            padding: "2px 10px",
                            borderRadius: 4,
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            color: diffStyle.color,
                            background: diffStyle.bg,
                            textTransform: "capitalize",
                          }}
                        >
                          {diffLevel} ({kw.difficulty ?? "N/A"})
                        </span>
                      </td>
                      <td style={{ padding: "12px", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                        {kw.search_volume != null ? kw.search_volume.toLocaleString() : "N/A"}
                      </td>
                      <td style={{ padding: "12px", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                        {kw.position != null ? `#${kw.position}` : kw.estimated_position != null ? `~#${kw.estimated_position}` : "--"}
                      </td>
                      <td style={{ padding: "12px", fontSize: "0.8rem", color: "var(--text-muted)", maxWidth: 200 }}>
                        {kw.recommendation || kw.tip || "--"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────
   Tab 4: Profile (existing functionality)
   ────────────────────────────────────────────────────────── */

function ProfileTab({ tenantId, token }) {
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
      <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--text-muted)", marginBottom: 12 }}>
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
        <h3 style={{ color: "var(--text-primary)", margin: "0 0 8px" }}>No profile analysis yet</h3>
        <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
          Analyze your business profile to check completeness and get suggestions
          for improving your local search presence.
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

      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 16, marginBottom: 24 }}>
        {/* Score Card */}
        <Card style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <ScoreGauge score={score} label="Completeness Score" />
          <div style={{ marginTop: 12, fontSize: "0.85rem", color: "var(--text-secondary)", textAlign: "center" }}>
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
            style={{ marginTop: 16, opacity: analyzing ? 0.6 : 1, width: "100%" }}
          >
            {analyzing ? "Analyzing..." : "Re-analyze Profile"}
          </button>
        </Card>

        {/* Missing Fields */}
        <Card>
          <SectionHeader>Missing or Incomplete Fields</SectionHeader>
          {missingFields.length === 0 ? (
            <div style={{ color: "#22c55e", fontSize: "0.9rem", padding: "20px 0", textAlign: "center" }}>
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
                  <span style={{ color: "#ef4444", fontSize: "0.8rem", fontWeight: 700, flexShrink: 0, marginTop: 1 }}>!</span>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                      {field.name || field.field || field}
                    </div>
                    {(field.suggestion || field.fix) && (
                      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 2 }}>
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

      {/* Recommendations */}
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
                    border: "1px solid var(--border-color)",
                    borderRadius: 10,
                    borderLeft: `4px solid ${priorityColor}`,
                    padding: "14px 16px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
                    <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-primary)" }}>
                      {rec.title || rec.name || `Recommendation ${idx + 1}`}
                    </div>
                    {rec.priority && <PriorityBadge priority={rec.priority} />}
                  </div>
                  <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    {rec.description || rec.text || rec}
                  </div>
                  {rec.action && (
                    <div style={{ marginTop: 6, fontSize: "0.8rem", color: "var(--accent)", fontWeight: 500 }}>
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

/* ──────────────────────────────────────────────────────────
   Main Page Component
   ────────────────────────────────────────────────────────── */

export default function LocalSEOPage({ onNavigate }) {
  const { user, token } = useAuth();
  const [activeTab, setActiveTab] = useState("audit");
  const [showUpgradePrompt, setShowUpgradePrompt] = useState(false);

  if (!user?.tenantId) {
    return (
      <div className="fade-in">
        <div className="page-header">
          <h1>SEO & Marketing Hub</h1>
        </div>
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <p>Please log in to access SEO tools.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      {/* Upgrade prompt modal */}
      {showUpgradePrompt && (
        <UpgradePrompt
          feature="Local SEO & Marketing Hub"
          requiredPlan="professional"
          onClose={() => setShowUpgradePrompt(false)}
          onNavigate={onNavigate}
        />
      )}

      <div className="page-header">
        <div>
          <h1>SEO & Marketing Hub</h1>
          <p>Audit your site, track AI visibility, and optimize for search engines</p>
        </div>
      </div>

      {/* Plan gate banner for free/growth users */}
      {planBelowRequired(user?.plan, "professional") && (
        <UpgradePrompt
          feature="Local SEO & Marketing Hub"
          requiredPlan="professional"
          onClose={() => {}}
          onNavigate={onNavigate}
          variant="banner"
        />
      )}

      {/* Tabs */}
      <div className="wh-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className={`wh-tab${activeTab === tab.key ? " wh-tab-active" : ""}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "audit" && <SeoAuditTab tenantId={user.tenantId} token={token} />}
      {activeTab === "geo" && <GeoScoreTab tenantId={user.tenantId} token={token} />}
      {activeTab === "keywords" && <KeywordsTab tenantId={user.tenantId} token={token} />}
      {activeTab === "profile" && <ProfileTab tenantId={user.tenantId} token={token} />}
    </div>
  );
}
