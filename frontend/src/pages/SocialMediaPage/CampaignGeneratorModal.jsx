import { useState } from "react";
import {
  createSocialPost,
  generateSocialCampaign,
} from "../../utils/api/social";
import { PLATFORMS, PLATFORM_MAP } from "./constants";
import PlatformIcon from "./PlatformIcon";
import {
  cardStyle,
  inputStyle,
  btnPrimary,
  btnSecondary,
  overlayStyle,
  modalStyle,
  labelStyle,
} from "./styles";

export default function CampaignGeneratorModal({
  tenantId,
  token,
  onClose,
  onGenerated,
}) {
  const [topic, setTopic] = useState("");
  const [selectedPlatforms, setSelectedPlatforms] = useState([
    "facebook",
    "instagram",
    "linkedin",
  ]);
  const [postsPerWeek, setPostsPerWeek] = useState(3);
  const [generating, setGenerating] = useState(false);
  const [generatedPosts, setGeneratedPosts] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const togglePlatform = (key) => {
    setSelectedPlatforms((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    );
  };

  const handleGenerate = async () => {
    if (!topic.trim() || selectedPlatforms.length === 0) {
      setError("Please enter a topic and select at least one platform.");
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const res = await generateSocialCampaign(tenantId, token, {
        topic: topic.trim(),
        platforms: selectedPlatforms,
        posts_per_week: postsPerWeek,
      });
      setGeneratedPosts(res.posts || []);
    } catch (e) {
      setError(e.message || "AI generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const handleSaveAll = async () => {
    setSaving(true);
    try {
      for (const post of generatedPosts) {
        await createSocialPost(tenantId, token, {
          platform: post.platform,
          content: post.content,
          hashtags: post.hashtags || null,
          status: "draft",
          scheduled_for: post.scheduled_for || null,
        });
      }
      onGenerated();
    } catch (e) {
      setError(e.message || "Failed to save posts");
    } finally {
      setSaving(false);
    }
  };

  const removePost = (idx) => {
    setGeneratedPosts((prev) => prev.filter((_, i) => i !== idx));
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ ...modalStyle, maxWidth: 800 }}
      >
        <h2
          style={{
            margin: "0 0 20px",
            color: "var(--text-primary)",
            fontSize: "1.2rem",
          }}
        >
          AI Content Calendar Generator
        </h2>

        {generatedPosts.length === 0 ? (
          <>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Topic / Theme</label>
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g., Home renovation tips, spring specials, customer success stories"
                style={inputStyle}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Platforms</label>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {PLATFORMS.map((p) => (
                  <button
                    key={p.key}
                    onClick={() => togglePlatform(p.key)}
                    style={{
                      padding: "8px 14px",
                      borderRadius: 8,
                      fontSize: "0.85rem",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      border: selectedPlatforms.includes(p.key)
                        ? `2px solid ${p.color}`
                        : "1px solid var(--border)",
                      background: selectedPlatforms.includes(p.key)
                        ? `${p.color}15`
                        : "var(--bg-primary)",
                      color: selectedPlatforms.includes(p.key)
                        ? p.color
                        : "var(--text-secondary)",
                      fontWeight: selectedPlatforms.includes(p.key) ? 600 : 400,
                    }}
                  >
                    <PlatformIcon platform={p.key} size={18} /> {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Posts per week</label>
              <select
                value={postsPerWeek}
                onChange={(e) => setPostsPerWeek(Number(e.target.value))}
                style={{ ...inputStyle, width: "auto", maxWidth: 120 }}
              >
                {[1, 2, 3, 5, 7].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </div>

            {error && (
              <div
                style={{
                  color: "#f87171",
                  fontSize: "0.85rem",
                  marginBottom: 12,
                }}
              >
                {error}
              </div>
            )}

            <div
              style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}
            >
              <button onClick={onClose} style={btnSecondary}>
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={generating}
                style={{ ...btnPrimary, opacity: generating ? 0.6 : 1 }}
              >
                {generating
                  ? "Generating calendar..."
                  : "Generate Content Calendar"}
              </button>
            </div>
          </>
        ) : (
          <>
            <p
              style={{
                color: "var(--text-secondary)",
                fontSize: "0.9rem",
                margin: "0 0 16px",
              }}
            >
              {generatedPosts.length} posts generated. Review, edit, or remove
              posts before saving.
            </p>
            <div
              style={{
                maxHeight: 400,
                overflowY: "auto",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                marginBottom: 16,
              }}
            >
              {generatedPosts.map((post, idx) => (
                <div
                  key={idx}
                  style={{
                    ...cardStyle,
                    padding: "12px 16px",
                    background: "var(--bg-primary)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 6,
                    }}
                  >
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 8 }}
                    >
                      <PlatformIcon platform={post.platform} size={20} />
                      <span
                        style={{
                          fontSize: "0.8rem",
                          fontWeight: 600,
                          color: "var(--text-primary)",
                        }}
                      >
                        {PLATFORM_MAP[post.platform]?.label}
                      </span>
                      {post.scheduled_for && (
                        <span
                          style={{
                            fontSize: "0.75rem",
                            color: "var(--text-muted)",
                          }}
                        >
                          {new Date(post.scheduled_for).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => removePost(idx)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "var(--text-muted)",
                        cursor: "pointer",
                        fontSize: "0.85rem",
                      }}
                    >
                      &#x2715;
                    </button>
                  </div>
                  <div
                    style={{
                      fontSize: "0.85rem",
                      color: "var(--text-primary)",
                      whiteSpace: "pre-wrap",
                      lineHeight: 1.5,
                    }}
                  >
                    {post.content}
                  </div>
                  {post.hashtags && (
                    <div
                      style={{
                        marginTop: 4,
                        fontSize: "0.8rem",
                        color: "var(--accent)",
                      }}
                    >
                      {post.hashtags}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {error && (
              <div
                style={{
                  color: "#f87171",
                  fontSize: "0.85rem",
                  marginBottom: 12,
                }}
              >
                {error}
              </div>
            )}

            <div
              style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}
            >
              <button
                onClick={() => setGeneratedPosts([])}
                style={btnSecondary}
              >
                Back
              </button>
              <button onClick={onClose} style={btnSecondary}>
                Cancel
              </button>
              <button
                onClick={handleSaveAll}
                disabled={saving}
                style={{ ...btnPrimary, opacity: saving ? 0.6 : 1 }}
              >
                {saving
                  ? "Saving..."
                  : `Save All ${generatedPosts.length} Posts as Drafts`}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
