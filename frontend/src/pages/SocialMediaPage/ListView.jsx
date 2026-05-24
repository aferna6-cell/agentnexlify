import { PLATFORM_MAP } from "./constants";
import { timeAgo } from "./helpers";
import { cardStyle, btnPrimary, btnSecondary } from "./styles";
import StatusBadge from "./StatusBadge";
import PlatformIcon from "./PlatformIcon";

export default function ListView({
  posts,
  onEdit,
  onDelete,
  onShowCreatePost,
  onShowCampaignGen,
}) {
  if (posts.length === 0) {
    return (
      <div style={{ ...cardStyle, textAlign: "center", padding: "60px 20px" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>&#128225;</div>
        <h3 style={{ margin: "0 0 8px", color: "var(--text-primary)" }}>
          No social posts yet
        </h3>
        <p
          style={{
            color: "var(--text-secondary)",
            margin: "0 0 16px",
            maxWidth: 440,
            marginInline: "auto",
          }}
        >
          Create your first social media post or use AI to generate a full
          content calendar. Posts can be scheduled for automatic publishing
          across Facebook, Instagram, Twitter/X, LinkedIn, and Google Business.
        </p>
        <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
          <button onClick={onShowCampaignGen} style={btnSecondary}>
            AI Content Calendar
          </button>
          <button onClick={onShowCreatePost} style={btnPrimary}>
            + Create Post
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {posts.map((post) => (
        <div
          key={post.id}
          style={{
            ...cardStyle,
            padding: "14px 20px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            transition: "background 0.15s",
          }}
          onClick={() => onEdit(post)}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              flex: 1,
              minWidth: 0,
            }}
          >
            <PlatformIcon platform={post.platform} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  marginBottom: 4,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {(post.content || "").slice(0, 100) || "Untitled post"}
              </div>
              <div
                style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}
              >
                {PLATFORM_MAP[post.platform]?.label || post.platform}
                {" · "}
                {post.scheduled_for
                  ? `Scheduled: ${new Date(post.scheduled_for).toLocaleDateString()}`
                  : timeAgo(post.created_at)}
                {post.hashtags && <span> &middot; {post.hashtags}</span>}
              </div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <StatusBadge status={post.status} />
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(post.id);
              }}
              style={{
                background: "none",
                border: "none",
                color: "var(--text-muted)",
                cursor: "pointer",
                padding: "4px 8px",
                borderRadius: 6,
                fontSize: "0.85rem",
              }}
              title="Delete"
            >
              &#x2715;
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
