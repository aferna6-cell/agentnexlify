import { useState, useEffect, useCallback } from "react";
import SkeletonLoader from "../../components/SkeletonLoader";
import {
  fetchSeoKeywords,
  fetchKeywordRankings,
  trackKeywords,
} from "../../utils/api/seo";
import { DIFFICULTY_COLORS, getDifficultyLevel } from "./constants";
import { SectionHeader, Card, ErrorBanner } from "./components";

export default function KeywordsTab({ tenantId, token }) {
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

      <Card style={{ marginBottom: 24 }}>
        <SectionHeader>Track Keywords</SectionHeader>
        <p
          style={{
            fontSize: "0.85rem",
            color: "var(--text-secondary)",
            marginBottom: 12,
            marginTop: 0,
          }}
        >
          Add keywords you want to track. Separate multiple keywords with
          commas.
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
              border: "1px solid var(--border)",
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
            style={{
              opacity: tracking || !newKeywords.trim() ? 0.6 : 1,
              whiteSpace: "nowrap",
            }}
          >
            {tracking ? "Adding..." : "Add Keywords"}
          </button>
        </div>
      </Card>

      <Card>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 12,
          }}
        >
          <SectionHeader>Keyword Rankings</SectionHeader>
          <button
            className="btn-primary"
            onClick={() => {
              setLoading(true);
              loadKeywords();
            }}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
              padding: "6px 14px",
              fontSize: "0.8rem",
            }}
          >
            Refresh Rankings
          </button>
        </div>
        {allKeywords.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "40px 20px",
              color: "var(--text-muted)",
            }}
          >
            <svg
              width="40"
              height="40"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ color: "var(--text-muted)", marginBottom: 8 }}
            >
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            <h3
              style={{
                color: "var(--text-primary)",
                margin: "0 0 8px",
                fontSize: "1rem",
              }}
            >
              No keywords tracked yet
            </h3>
            <p
              style={{
                maxWidth: 420,
                margin: "0 auto",
                lineHeight: 1.6,
                fontSize: "0.85rem",
              }}
            >
              Add keywords above to start tracking your search rankings. You can
              also run an SEO Audit to get AI-suggested keywords for your
              business.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {[
                    "Keyword",
                    "Difficulty",
                    "Search Volume",
                    "Est. Position",
                    "Recommendation",
                  ].map((header) => (
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
                        borderBottom: "1px solid var(--border)",
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
                        borderBottom: "1px solid var(--border)",
                        transition: "background 0.15s",
                      }}
                      onMouseEnter={(e) =>
                        (e.currentTarget.style.background =
                          "rgba(255,255,255,0.02)")
                      }
                      onMouseLeave={(e) =>
                        (e.currentTarget.style.background = "transparent")
                      }
                    >
                      <td
                        style={{
                          padding: "12px",
                          fontSize: "0.9rem",
                          fontWeight: 600,
                          color: "var(--text-primary)",
                        }}
                      >
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
                      <td
                        style={{
                          padding: "12px",
                          fontSize: "0.85rem",
                          color: "var(--text-secondary)",
                        }}
                      >
                        {kw.search_volume != null
                          ? kw.search_volume.toLocaleString()
                          : "N/A"}
                      </td>
                      <td
                        style={{
                          padding: "12px",
                          fontSize: "0.85rem",
                          color: "var(--text-secondary)",
                        }}
                      >
                        {kw.position != null
                          ? `#${kw.position}`
                          : kw.estimated_position != null
                            ? `~#${kw.estimated_position}`
                            : "--"}
                      </td>
                      <td
                        style={{
                          padding: "12px",
                          fontSize: "0.8rem",
                          color: "var(--text-muted)",
                          maxWidth: 200,
                        }}
                      >
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
