import { useState } from "react";
import {
  createSocialPost,
  generateSocialContent,
} from "../../utils/api/social";
import { PLATFORMS, TONES } from "./constants";
import {
  cardStyle,
  inputStyle,
  btnPrimary,
  btnSecondary,
  overlayStyle,
  modalStyle,
  labelStyle,
} from "./styles";

export default function AiGenerateModal({
  tenantId,
  token,
  onClose,
  onGenerated,
}) {
  const [topic, setTopic] = useState("");
  const [platform, setPlatform] = useState("facebook");
  const [tone, setTone] = useState("professional");
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleGenerate = async () => {
    if (!topic.trim()) {
      setError("Please enter a topic.");
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const res = await generateSocialContent(tenantId, token, {
        topic: topic.trim(),
        platform,
        tone,
      });
      setResult(res);
    } catch (e) {
      setError(e.message || "AI generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const handleUse = async () => {
    if (!result?.content) return;
    try {
      await createSocialPost(tenantId, token, {
        platform,
        content: result.content,
        hashtags: result.hashtags || null,
        status: "draft",
      });
      onGenerated(result.content);
    } catch (e) {
      setError(e.message || "Failed to save post");
    }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={modalStyle}>
        <h2
          style={{
            margin: "0 0 20px",
            color: "var(--text-primary)",
            fontSize: "1.2rem",
          }}
        >
          Generate Post with AI
        </h2>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Topic</label>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., Spring cleaning tips for homeowners"
            style={inputStyle}
          />
        </div>

        <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Platform</label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              style={{ ...inputStyle, width: "100%" }}
            >
              {PLATFORMS.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Tone</label>
            <select
              value={tone}
              onChange={(e) => setTone(e.target.value)}
              style={{
                ...inputStyle,
                width: "100%",
                textTransform: "capitalize",
              }}
            >
              {TONES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
        </div>

        {result && (
          <div
            style={{
              ...cardStyle,
              marginBottom: 16,
              background: "var(--bg-primary)",
            }}
          >
            <div
              style={{
                fontSize: "0.75rem",
                fontWeight: 600,
                textTransform: "uppercase",
                color: "var(--accent)",
                marginBottom: 8,
              }}
            >
              Generated Content
            </div>
            <div
              style={{
                fontSize: "0.9rem",
                color: "var(--text-primary)",
                whiteSpace: "pre-wrap",
                lineHeight: 1.6,
              }}
            >
              {result.content}
            </div>
            {result.hashtags && (
              <div
                style={{
                  marginTop: 8,
                  fontSize: "0.85rem",
                  color: "var(--accent)",
                }}
              >
                {result.hashtags}
              </div>
            )}
          </div>
        )}

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

        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={btnSecondary}>
            Cancel
          </button>
          {result ? (
            <button onClick={handleUse} style={btnPrimary}>
              Save as Draft
            </button>
          ) : (
            <button
              onClick={handleGenerate}
              disabled={generating}
              style={{ ...btnPrimary, opacity: generating ? 0.6 : 1 }}
            >
              {generating ? "Generating..." : "Generate"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
