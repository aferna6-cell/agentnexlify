import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchReferralStats } from "../utils/api/referral";
import SkeletonLoader from "../components/SkeletonLoader";

function StatCard({ label, value }) {
  return (
    <div
      className="settings-card"
      style={{ textAlign: "center", minWidth: 140 }}
    >
      <div
        style={{
          fontSize: "2rem",
          fontWeight: 700,
          color: "var(--text-primary)",
          lineHeight: 1,
          marginBottom: "0.4rem",
        }}
      >
        {value}
      </div>
      <div
        style={{
          fontSize: "0.8rem",
          fontWeight: 600,
          color: "var(--text-secondary)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        {label}
      </div>
    </div>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable – link is still selectable */
    }
  };

  return (
    <button
      className="btn-secondary"
      onClick={handleCopy}
      style={{ whiteSpace: "nowrap", padding: "10px 20px" }}
    >
      {copied ? "Copied" : "Copy link"}
    </button>
  );
}

export default function ReferralPage() {
  const { token } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    fetchReferralStats(token)
      .then((data) => {
        setStats(data);
      })
      .catch((err) => {
        setError(err.message || "Failed to load referral data.");
      })
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <SkeletonLoader />;

  if (error) {
    return (
      <div className="fade-in">
        <div className="page-header">
          <h1>Referral</h1>
        </div>
        <div
          className="settings-card"
          style={{ textAlign: "center", padding: "2.5rem 1.5rem" }}
        >
          <div
            style={{
              fontSize: "1rem",
              color: "var(--red)",
              marginBottom: "1rem",
            }}
          >
            {error}
          </div>
          <button className="btn-secondary" onClick={load}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  const hasClicks = stats && stats.total_clicks > 0;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Referral</h1>
        <p>
          Share AgentNexLiFy with other business owners. Every visit to your
          signup link through your unique badge is tracked here.
        </p>
      </div>

      {/* Share link */}
      <div className="settings-card" style={{ marginBottom: "1.5rem" }}>
        <div
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "var(--accent)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            marginBottom: "0.5rem",
          }}
        >
          Your referral link
        </div>
        <div
          style={{
            fontSize: "0.95rem",
            color: "var(--text-secondary)",
            marginBottom: "1rem",
          }}
        >
          When someone signs up through this link, their account is attributed
          to you. Share it anywhere — email, social media, or your website.
        </div>
        <div
          style={{
            display: "flex",
            gap: "0.75rem",
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <input
            type="text"
            readOnly
            value={stats?.share_link || ""}
            style={{
              flex: 1,
              minWidth: 0,
              padding: "10px 14px",
              background: "var(--bg-primary)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              fontSize: "0.875rem",
              color: "var(--text-primary)",
              fontFamily: "monospace",
            }}
            onFocus={(e) => e.target.select()}
          />
          {stats?.share_link && <CopyButton text={stats.share_link} />}
        </div>
        {stats?.ref_code && (
          <div
            style={{
              marginTop: "0.75rem",
              fontSize: "0.8rem",
              color: "var(--text-secondary)",
            }}
          >
            Referral code:{" "}
            <span
              style={{
                fontFamily: "monospace",
                color: "var(--text-primary)",
                fontWeight: 600,
              }}
            >
              {stats.ref_code}
            </span>
          </div>
        )}
      </div>

      {/* Click stats */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: "1rem",
          marginBottom: "1.5rem",
        }}
      >
        <StatCard label="Total clicks" value={stats?.total_clicks ?? 0} />
        <StatCard label="Last 7 days" value={stats?.clicks_last_7d ?? 0} />
        <StatCard label="Last 30 days" value={stats?.clicks_last_30d ?? 0} />
        <StatCard label="Signups referred" value={stats?.referred_signups ?? 0} />
      </div>

      {/* Empty / encouraging state */}
      {!hasClicks && (
        <div
          className="settings-card"
          style={{ textAlign: "center", padding: "2.5rem 1.5rem" }}
        >
          <div
            style={{
              fontSize: "1rem",
              fontWeight: 600,
              color: "var(--text-primary)",
              marginBottom: "0.5rem",
            }}
          >
            No clicks yet
          </div>
          <div
            style={{
              fontSize: "0.875rem",
              color: "var(--text-secondary)",
              maxWidth: 400,
              margin: "0 auto 1.25rem",
            }}
          >
            Copy your referral link above and share it with business owners who
            could benefit from an AI front desk. Every click and signup will
            appear here.
          </div>
          <CopyButton text={stats?.share_link || ""} />
        </div>
      )}
    </div>
  );
}
