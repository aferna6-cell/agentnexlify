import { useState, useEffect, useCallback } from "react";
import SkeletonLoader from "../../components/SkeletonLoader";
import {
  runSeoAudit,
  fetchSeoAudit,
  fetchSeoAuditHistory,
} from "../../utils/api/seo";
import { CATEGORY_ICONS, CATEGORY_LABELS } from "./constants";
import {
  ScoreGauge,
  SectionHeader,
  Card,
  PriorityBadge,
  ErrorBanner,
} from "./components";

export default function SeoAuditTab({ tenantId, token }) {
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
      const historyData = await fetchSeoAuditHistory(tenantId, token).catch(
        (err) => {
          console.warn("LocalSEO: fetchSeoAuditHistory failed:", err);
          return null;
        },
      );
      if (historyData) setHistory(historyData.audits || historyData || []);
    } catch (err) {
      setError(
        err.body?.detail ||
          err.message ||
          "Audit failed. Make sure your website URL is configured.",
      );
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <SkeletonLoader />;

  if (!audit) {
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
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
          <path d="M8 11h6" />
          <path d="M11 8v6" />
        </svg>
        <h3 style={{ color: "var(--text-primary)", margin: "0 0 8px" }}>
          No SEO audit yet
        </h3>
        <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
          Run a comprehensive SEO audit to check your website's technical
          health, content quality, on-page optimization, and link structure. Get
          actionable recommendations to improve your search rankings.
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
  const categoryKeys =
    Object.keys(categories).length > 0
      ? Object.keys(categories)
      : ["technical", "content", "on_page", "link_analysis"];

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
          <ScoreGauge score={overallScore} label="Overall SEO Score" />
          <div
            style={{
              marginTop: 12,
              fontSize: "0.85rem",
              color: "var(--text-secondary)",
              textAlign: "center",
            }}
          >
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

        <Card>
          <SectionHeader>Category Breakdown</SectionHeader>
          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}
          >
            {categoryKeys.map((key) => {
              const cat = categories[key] || {};
              const catScore = cat.score ?? 0;
              const issues = cat.issues || [];
              const critical = issues.filter(
                (i) => i.severity === "critical" || i.severity === "error",
              ).length;
              const warnings = issues.filter(
                (i) => i.severity === "warning",
              ).length;
              const passed = issues.filter(
                (i) => i.severity === "pass" || i.severity === "good",
              ).length;

              let barColor = "#ef4444";
              if (catScore >= 70) barColor = "#22c55e";
              else if (catScore >= 40) barColor = "#f59e0b";

              return (
                <div
                  key={key}
                  style={{
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border)",
                    borderRadius: 10,
                    padding: "14px 16px",
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
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 8 }}
                    >
                      <span style={{ fontSize: "1.1rem" }}>
                        {CATEGORY_ICONS[key] || "•"}
                      </span>
                      <span
                        style={{
                          fontWeight: 600,
                          fontSize: "0.85rem",
                          color: "var(--text-primary)",
                        }}
                      >
                        {CATEGORY_LABELS[key] || key.replace(/_/g, " ")}
                      </span>
                    </div>
                    <span
                      style={{
                        fontWeight: 700,
                        fontSize: "1rem",
                        color: barColor,
                      }}
                    >
                      {catScore}
                    </span>
                  </div>
                  <div
                    style={{
                      height: 6,
                      background: "var(--border)",
                      borderRadius: 3,
                      marginBottom: 8,
                    }}
                  >
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
                  <div
                    style={{ display: "flex", gap: 12, fontSize: "0.75rem" }}
                  >
                    {critical > 0 && (
                      <span style={{ color: "#ef4444" }}>
                        {critical} critical
                      </span>
                    )}
                    {warnings > 0 && (
                      <span style={{ color: "#f59e0b" }}>
                        {warnings} warning{warnings !== 1 ? "s" : ""}
                      </span>
                    )}
                    {passed > 0 && (
                      <span style={{ color: "#22c55e" }}>{passed} passed</span>
                    )}
                    {critical === 0 && warnings === 0 && passed === 0 && (
                      <span style={{ color: "var(--text-muted)" }}>
                        No data
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {categoryKeys.some(
        (key) => (categories[key]?.issues || []).length > 0,
      ) && (
        <Card style={{ marginBottom: 24 }}>
          <SectionHeader>Detailed Issues</SectionHeader>
          {categoryKeys.map((key) => {
            const cat = categories[key] || {};
            const issues = cat.issues || [];
            if (issues.length === 0) return null;
            return (
              <div key={key} style={{ marginBottom: 16 }}>
                <div
                  style={{
                    fontWeight: 600,
                    fontSize: "0.85rem",
                    color: "var(--text-primary)",
                    marginBottom: 8,
                  }}
                >
                  {CATEGORY_LABELS[key] || key.replace(/_/g, " ")}
                </div>
                <div
                  style={{ display: "flex", flexDirection: "column", gap: 6 }}
                >
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
                        <span
                          style={{
                            color,
                            fontSize: "0.8rem",
                            fontWeight: 700,
                            flexShrink: 0,
                            marginTop: 1,
                          }}
                        >
                          {severity === "pass" || severity === "good"
                            ? "✓"
                            : severity === "warning"
                              ? "!"
                              : "✗"}
                        </span>
                        <div style={{ flex: 1 }}>
                          <div
                            style={{
                              fontWeight: 500,
                              fontSize: "0.85rem",
                              color: "var(--text-primary)",
                            }}
                          >
                            {issue.title ||
                              issue.message ||
                              issue.description ||
                              "Issue"}
                          </div>
                          {issue.detail && (
                            <div
                              style={{
                                fontSize: "0.8rem",
                                color: "var(--text-muted)",
                                marginTop: 2,
                              }}
                            >
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

      <Card style={{ marginBottom: 24 }}>
        <SectionHeader>Actionable Recommendations</SectionHeader>
        {recommendations.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "20px",
              color: "var(--text-muted)",
              fontSize: "0.85rem",
            }}
          >
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
                    <PriorityBadge priority={priority} />
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
      </Card>

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
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                  }}
                >
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 10 }}
                  >
                    <div
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: scoreColor,
                        flexShrink: 0,
                      }}
                    />
                    <span
                      style={{
                        fontSize: "0.85rem",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {dateStr}
                    </span>
                  </div>
                  <span
                    style={{
                      fontWeight: 700,
                      fontSize: "0.9rem",
                      color: scoreColor,
                    }}
                  >
                    {entryScore}/100
                  </span>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
