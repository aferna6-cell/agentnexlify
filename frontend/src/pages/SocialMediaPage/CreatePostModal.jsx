import { useState } from "react";
import { createSocialPost } from "../../utils/api/social";
import { PLATFORMS, CHAR_LIMITS } from "./constants";
import PlatformIcon from "./PlatformIcon";
import {
  inputStyle,
  btnPrimary,
  btnSecondary,
  overlayStyle,
  modalStyle,
  labelStyle,
} from "./styles";

export default function CreatePostModal({
  tenantId,
  token,
  onClose,
  onCreated,
}) {
  const [selectedPlatforms, setSelectedPlatforms] = useState(["facebook"]);
  const [content, setContent] = useState("");
  const [hashtags, setHashtags] = useState("");
  const [scheduleDate, setScheduleDate] = useState("");
  const [scheduleTime, setScheduleTime] = useState("");
  const [postNow, setPostNow] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const togglePlatform = (key) => {
    setSelectedPlatforms((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    );
  };

  const activePlatformLimit = Math.min(
    ...selectedPlatforms.map((p) => CHAR_LIMITS[p] || 2200),
  );

  const handleSubmit = async () => {
    if (!content.trim() || selectedPlatforms.length === 0) {
      setError("Please select at least one platform and enter content.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      for (const platform of selectedPlatforms) {
        const data = {
          platform,
          content: content.trim(),
          hashtags: hashtags.trim()
            ? hashtags
                .split(",")
                .map((h) => h.trim())
                .filter(Boolean)
            : [],
          status: postNow ? "published" : scheduleDate ? "scheduled" : "draft",
          scheduled_for:
            scheduleDate && scheduleTime
              ? `${scheduleDate}T${scheduleTime}:00`
              : scheduleDate
                ? `${scheduleDate}T09:00:00`
                : null,
        };
        await createSocialPost(tenantId, token, data);
      }
      onCreated();
    } catch (e) {
      setError(e.message || "Failed to create post");
    } finally {
      setSubmitting(false);
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
          Create Post
        </h2>

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
          <label style={labelStyle}>Content</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Write your post content..."
            rows={6}
            maxLength={activePlatformLimit}
            style={{
              ...inputStyle,
              resize: "vertical",
              fontFamily: "inherit",
              lineHeight: 1.6,
            }}
          />
          <div
            style={{
              fontSize: "0.75rem",
              color:
                content.length > activePlatformLimit * 0.9
                  ? "#f87171"
                  : "var(--text-muted)",
              marginTop: 4,
              textAlign: "right",
            }}
          >
            {content.length} / {activePlatformLimit}
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Hashtags</label>
          <input
            type="text"
            value={hashtags}
            onChange={(e) => setHashtags(e.target.value)}
            placeholder="#marketing #business #tips"
            style={inputStyle}
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Schedule</label>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                cursor: "pointer",
                color: "var(--text-secondary)",
                fontSize: "0.85rem",
              }}
            >
              <input
                type="checkbox"
                checked={postNow}
                onChange={(e) => {
                  setPostNow(e.target.checked);
                  if (e.target.checked) {
                    setScheduleDate("");
                    setScheduleTime("");
                  }
                }}
              />
              Post Now
            </label>
            {!postNow && (
              <>
                <input
                  type="date"
                  value={scheduleDate}
                  onChange={(e) => setScheduleDate(e.target.value)}
                  style={{ ...inputStyle, width: "auto" }}
                />
                <input
                  type="time"
                  value={scheduleTime}
                  onChange={(e) => setScheduleTime(e.target.value)}
                  style={{ ...inputStyle, width: "auto" }}
                />
              </>
            )}
          </div>
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

        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={btnSecondary}>
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            style={{
              ...btnPrimary,
              opacity: submitting ? 0.6 : 1,
              cursor: submitting ? "default" : "pointer",
            }}
          >
            {submitting
              ? "Creating..."
              : postNow
                ? "Publish Now"
                : scheduleDate
                  ? "Schedule Post"
                  : "Save as Draft"}
          </button>
        </div>
      </div>
    </div>
  );
}
