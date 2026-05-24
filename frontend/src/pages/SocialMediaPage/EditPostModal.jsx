import { useState } from "react";
import { updateSocialPost } from "../../utils/api/social";
import { PLATFORM_MAP, CHAR_LIMITS } from "./constants";
import PlatformIcon from "./PlatformIcon";
import StatusBadge from "./StatusBadge";
import {
  inputStyle,
  btnPrimary,
  btnSecondary,
  overlayStyle,
  modalStyle,
  labelStyle,
} from "./styles";

export default function EditPostModal({
  tenantId,
  token,
  post,
  onClose,
  onSaved,
  onDelete,
}) {
  const [content, setContent] = useState(post.content || "");
  const [hashtags, setHashtags] = useState(
    Array.isArray(post.hashtags)
      ? post.hashtags.join(", ")
      : post.hashtags || "",
  );
  const [scheduleDate, setScheduleDate] = useState(
    post.scheduled_for ? post.scheduled_for.split("T")[0] : "",
  );
  const [scheduleTime, setScheduleTime] = useState(
    post.scheduled_for && post.scheduled_for.includes("T")
      ? post.scheduled_for.split("T")[1]?.slice(0, 5)
      : "",
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const charLimit = CHAR_LIMITS[post.platform] || 2200;

  const handleSave = async () => {
    if (!content.trim()) {
      setError("Content is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const data = {
        content: content.trim(),
        hashtags: hashtags.trim()
          ? hashtags
              .split(",")
              .map((h) => h.trim())
              .filter(Boolean)
          : [],
        scheduled_for:
          scheduleDate && scheduleTime
            ? `${scheduleDate}T${scheduleTime}:00`
            : scheduleDate
              ? `${scheduleDate}T09:00:00`
              : null,
        status: scheduleDate ? "scheduled" : post.status,
      };
      await updateSocialPost(tenantId, token, post.id, data);
      onSaved();
    } catch (e) {
      setError(e.message || "Failed to update post");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={modalStyle}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <PlatformIcon platform={post.platform} size={28} />
            <h2
              style={{
                margin: 0,
                color: "var(--text-primary)",
                fontSize: "1.2rem",
              }}
            >
              Edit {PLATFORM_MAP[post.platform]?.label} Post
            </h2>
          </div>
          <StatusBadge status={post.status} />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Content</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={6}
            maxLength={charLimit}
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
                content.length > charLimit * 0.9
                  ? "#f87171"
                  : "var(--text-muted)",
              marginTop: 4,
              textAlign: "right",
            }}
          >
            {content.length} / {charLimit}
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Hashtags</label>
          <input
            type="text"
            value={hashtags}
            onChange={(e) => setHashtags(e.target.value)}
            placeholder="#hashtag1 #hashtag2"
            style={inputStyle}
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Schedule</label>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
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
            {scheduleDate && (
              <button
                onClick={() => {
                  setScheduleDate("");
                  setScheduleTime("");
                }}
                style={{
                  ...btnSecondary,
                  fontSize: "0.8rem",
                  padding: "6px 12px",
                }}
              >
                Clear
              </button>
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

        <div
          style={{
            display: "flex",
            gap: 12,
            justifyContent: "space-between",
          }}
        >
          <button
            onClick={onDelete}
            style={{
              ...btnSecondary,
              color: "#f87171",
              borderColor: "#f8717130",
            }}
          >
            Delete Post
          </button>
          <div style={{ display: "flex", gap: 12 }}>
            <button onClick={onClose} style={btnSecondary}>
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{ ...btnPrimary, opacity: saving ? 0.6 : 1 }}
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
