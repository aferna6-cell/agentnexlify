/* Refer-a-business card (rubric 9.4 surface).
 * Every tenant has a referral_code (minted at signup, backfilled by
 * migration 135). Sharing the link attributes the new signup via
 * backend/services/referral.py.
 *
 * Data comes from GET /api/v1/referral/my-stats (live) — never from
 * stale JWT claims. Architecture decision: JWT is auth identity only.
 */
import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { fetchReferralStats } from "../../utils/api/referral";

export default function ReferralCard() {
  const { token } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchReferralStats(token)
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Failed to load referral info");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [token]);

  const copy = async () => {
    if (!stats?.share_link) return;
    try {
      await navigator.clipboard.writeText(stats.share_link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable - link is still selectable below */
    }
  };

  if (loading) {
    return (
      <div
        style={{
          marginTop: 32,
          padding: 24,
          background: "var(--bg-secondary)",
          border: "1px solid var(--border)",
          borderRadius: 12,
        }}
      >
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--accent)", letterSpacing: 1.2 }}>
          REFER A BUSINESS
        </div>
        <div style={{ marginTop: 12, color: "var(--text-muted)", fontSize: 13 }}>
          Loading referral link...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          marginTop: 32,
          padding: 24,
          background: "var(--bg-secondary)",
          border: "1px solid var(--border)",
          borderRadius: 12,
        }}
      >
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--accent)", letterSpacing: 1.2 }}>
          REFER A BUSINESS
        </div>
        <div style={{ marginTop: 12, color: "var(--text-muted)", fontSize: 13 }}>
          Could not load referral link. Refresh to try again.
        </div>
      </div>
    );
  }

  if (!stats?.ref_code) return null;

  return (
    <div
      style={{
        marginTop: 32,
        padding: 24,
        background: "var(--bg-secondary)",
        border: "1px solid var(--border)",
        borderRadius: 12,
      }}
    >
      <div style={{ fontSize: 12, fontWeight: 600, color: "var(--accent)", letterSpacing: 1.2 }}>
        REFER A BUSINESS
      </div>
      <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)", margin: "6px 0" }}>
        Know another business owner who could use an AI staff?
      </div>
      <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 14 }}>
        Share your link - signups through it are credited to your account.
      </div>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <code
          style={{
            padding: "10px 14px",
            background: "var(--bg-primary)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 13,
            color: "var(--text-primary)",
            userSelect: "all",
            overflowWrap: "anywhere",
          }}
        >
          {stats.share_link}
        </code>
        <button className="btn-secondary" onClick={copy} style={{ padding: "10px 20px" }}>
          {copied ? "Copied" : "Copy link"}
        </button>
      </div>
    </div>
  );
}
