/* Refer-a-business card (rubric 9.4 surface).
 * Every tenant has a referral_code (minted at signup, backfilled by
 * migration 135). Sharing the link attributes the new signup via
 * backend/services/referral.py.
 */
import { useState } from "react";
import { useAuth } from "../../context/AuthContext";

export default function ReferralCard() {
  const { user } = useAuth();
  const [copied, setCopied] = useState(false);
  const code = user?.referralCode;

  if (!code) return null;

  const link = `${window.location.origin}/signup?ref=${encodeURIComponent(code)}`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable - link is still selectable below */
    }
  };

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
          {link}
        </code>
        <button className="btn-secondary" onClick={copy} style={{ padding: "10px 20px" }}>
          {copied ? "Copied" : "Copy link"}
        </button>
      </div>
    </div>
  );
}
