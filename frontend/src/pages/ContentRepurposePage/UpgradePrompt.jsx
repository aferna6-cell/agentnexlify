export default function UpgradePrompt() {
  return (
    <div style={{ padding: 40, textAlign: "center" }}>
      <div style={{ fontSize: "2rem", marginBottom: 12 }}>
        Content Repurposer
      </div>
      <p
        style={{
          color: "var(--text-secondary)",
          marginBottom: 24,
          maxWidth: 500,
          margin: "0 auto 24px",
        }}
      >
        Turn any blog post, YouTube video, or podcast into X threads, LinkedIn
        carousels, email sequences, TikTok scripts, and social posts - all in
        one click.
      </p>
      <div
        style={{
          padding: 24,
          background: "var(--card-bg)",
          borderRadius: 12,
          border: "1px solid var(--border)",
          maxWidth: 400,
          margin: "0 auto",
        }}
      >
        <div style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: 8 }}>
          Professional Plan Required
        </div>
        <p
          style={{
            color: "var(--text-secondary)",
            fontSize: "0.9rem",
            marginBottom: 16,
          }}
        >
          Content Repurposer is available on Professional ($150/mo) and
          Enterprise ($250/mo) plans.
        </p>
        <button
          className="btn-primary"
          onClick={() =>
            window.dispatchEvent(
              new CustomEvent("navigate", { detail: "billing" }),
            )
          }
        >
          Upgrade Now
        </button>
      </div>
    </div>
  );
}
