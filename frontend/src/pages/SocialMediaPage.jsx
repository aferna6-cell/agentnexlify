import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { notify } from "../utils/notify";
import {
  fetchSocialPosts,
  createSocialPost,
  updateSocialPost,
  deleteSocialPost,
  generateSocialContent,
  generateSocialCampaign,
  fetchSocialAnalytics,
} from "../utils/api/social";
import SkeletonLoader from "../components/SkeletonLoader";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

/* ---- Constants ---- */

const PLATFORMS = [
  { key: "facebook", label: "Facebook", color: "#1877f2", icon: "f" },
  { key: "instagram", label: "Instagram", color: "#e4405f", icon: "Ig" },
  { key: "twitter", label: "Twitter/X", color: "#000000", icon: "X" },
  { key: "linkedin", label: "LinkedIn", color: "#0a66c2", icon: "in" },
  { key: "google_business", label: "Google Business", color: "#4285f4", icon: "G" },
];

const PLATFORM_MAP = Object.fromEntries(PLATFORMS.map((p) => [p.key, p]));

const CHAR_LIMITS = {
  twitter: 280,
  linkedin: 3000,
  facebook: 2200,
  instagram: 2200,
  google: 2200,
};

const STATUS_STYLES = {
  draft: { label: "Draft", color: "var(--text-secondary)", bg: "var(--hover-overlay)" },
  scheduled: { label: "Scheduled", color: "var(--purple, #8b5cf6)", bg: "rgba(139, 92, 246, 0.15)" },
  published: { label: "Published", color: "var(--green)", bg: "var(--green-dim)" },
  failed: { label: "Failed", color: "#f87171", bg: "rgba(248, 113, 113, 0.15)" },
};

const TONES = ["professional", "casual", "friendly", "promotional"];

const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

/* ---- Helpers ---- */

function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.draft;
  return (
    <span style={{
      padding: "2px 10px", borderRadius: 12, fontSize: "0.75rem", fontWeight: 600,
      color: s.color, background: s.bg,
    }}>
      {s.label}
    </span>
  );
}

function PlatformIcon({ platform, size = 22 }) {
  const p = PLATFORM_MAP[platform];
  if (!p) return null;
  return (
    <span
      title={p.label}
      style={{
        display: "inline-flex", alignItems: "center", justifyContent: "center",
        width: size, height: size, borderRadius: "50%", fontSize: size * 0.45,
        fontWeight: 700, color: "#fff", background: p.color, flexShrink: 0,
      }}
    >
      {p.icon}
    </span>
  );
}

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

/* ---- Card style ---- */
const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

const inputStyle = {
  width: "100%", padding: "10px 14px", borderRadius: 8,
  border: "1px solid var(--border)", background: "var(--bg-primary)",
  color: "var(--text-primary)", fontSize: "0.9rem", boxSizing: "border-box",
};

const btnPrimary = {
  background: "var(--accent)", color: "#fff", border: "none",
  padding: "10px 20px", borderRadius: 8, fontWeight: 600, cursor: "pointer", fontSize: "0.9rem",
};

const btnSecondary = {
  background: "var(--bg-primary)", color: "var(--text-secondary)",
  border: "1px solid var(--border)", padding: "8px 16px",
  borderRadius: 8, cursor: "pointer", fontSize: "0.85rem",
};

/* ==== Main Component ==== */

export default function SocialMediaPage() {
  const { user, token } = useAuth();

  // Data state
  const [posts, setPosts] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  // Filters
  const [platformFilter, setPlatformFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // View modes
  const [viewMode, setViewMode] = useState("list"); // list | calendar | analytics
  const [calendarMonth, setCalendarMonth] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });

  // Modals
  const [showCreatePost, setShowCreatePost] = useState(false);
  const [showAiGenerate, setShowAiGenerate] = useState(false);
  const [showCampaignGen, setShowCampaignGen] = useState(false);
  const [editingPost, setEditingPost] = useState(null);

  /* ---- Load data ---- */

  const loadPosts = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const res = await fetchSocialPosts(user.tenantId, token, {
        platform: platformFilter || undefined,
        status: statusFilter || undefined,
      });
      setPosts(res.posts || res || []);
    } catch {
      setPosts([]);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, platformFilter, statusFilter]);

  const loadAnalytics = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const res = await fetchSocialAnalytics(user.tenantId, token);
      setAnalytics(res);
    } catch {
      setAnalytics(null);
    }
  }, [user?.tenantId, token]);

  useEffect(() => { loadPosts(); }, [loadPosts]);
  useEffect(() => { loadAnalytics(); }, [loadAnalytics]);

  /* ---- Handlers ---- */

  const handleDeletePost = async (postId) => {
    if (!confirm("Delete this post?")) return;
    try {
      await deleteSocialPost(user.tenantId, token, postId);
      loadPosts();
    } catch (e) {
      notify.error("Failed to delete: " + (e.message || "Unknown error"));
    }
  };

  /* ---- Computed ---- */

  const postsArray = Array.isArray(posts) ? posts : [];
  const totalPosts = postsArray.length;
  const scheduledCount = postsArray.filter((p) => p.status === "scheduled").length;
  const publishedCount = postsArray.filter((p) => p.status === "published").length;
  const draftCount = postsArray.filter((p) => p.status === "draft").length;

  // Analytics chart data
  const platformCounts = PLATFORMS.map((p) => ({
    name: p.label,
    count: postsArray.filter((post) => post.platform === p.key).length,
    color: p.color,
  }));

  // Calendar helpers
  const getDaysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();
  const getFirstDayOfWeek = (year, month) => new Date(year, month, 1).getDay();
  const calendarDays = getDaysInMonth(calendarMonth.year, calendarMonth.month);
  const calendarStartDay = getFirstDayOfWeek(calendarMonth.year, calendarMonth.month);

  const getPostsForDate = (day) => {
    const dateStr = `${calendarMonth.year}-${String(calendarMonth.month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    return postsArray.filter((p) => {
      const d = p.scheduled_for || p.published_at || p.created_at;
      return d && d.startsWith(dateStr);
    });
  };

  /* ---- Render ---- */

  if (loading && postsArray.length === 0) return <SkeletonLoader />;

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
            Social Media
          </h1>
          <p style={{ color: "var(--text-secondary)", margin: "4px 0 0", fontSize: "0.9rem" }}>
            Create, schedule, and manage posts across all your social platforms
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={() => setShowCampaignGen(true)} style={btnSecondary}>
            AI Content Calendar
          </button>
          <button onClick={() => setShowCreatePost(true)} style={btnPrimary}>
            + Create Post
          </button>
        </div>
      </div>

      {/* Stat Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
        {[
          { label: "Total Posts", value: totalPosts, color: "var(--accent)" },
          { label: "Published", value: publishedCount, color: "var(--green)" },
          { label: "Scheduled", value: scheduledCount, color: "var(--purple, #8b5cf6)" },
          { label: "Drafts", value: draftCount, color: "var(--text-secondary)" },
        ].map((s) => (
          <div key={s.label} style={cardStyle}>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Filters + View Toggle */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20, alignItems: "center", flexWrap: "wrap" }}>
        <select value={platformFilter} onChange={(e) => setPlatformFilter(e.target.value)}
          style={{ ...inputStyle, width: "auto", maxWidth: 180 }}>
          <option value="">All platforms</option>
          {PLATFORMS.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          style={{ ...inputStyle, width: "auto", maxWidth: 160 }}>
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="scheduled">Scheduled</option>
          <option value="published">Published</option>
        </select>
        <button onClick={() => setShowAiGenerate(true)} style={{
          ...btnSecondary, display: "flex", alignItems: "center", gap: 6,
        }}>
          <span style={{ fontSize: "1rem" }}>&#x2728;</span> Generate with AI
        </button>
        <div style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
          {["list", "calendar", "analytics"].map((mode) => (
            <button key={mode} onClick={() => setViewMode(mode)}
              style={{
                padding: "7px 14px", borderRadius: 8, textTransform: "capitalize", fontSize: "0.8rem",
                border: viewMode === mode ? "2px solid var(--accent)" : "1px solid var(--border)",
                background: viewMode === mode ? "var(--accent-dim)" : "var(--bg-secondary, var(--card-bg))",
                color: viewMode === mode ? "var(--accent)" : "var(--text-secondary)",
                cursor: "pointer", fontWeight: viewMode === mode ? 600 : 400,
              }}>
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* ============ LIST VIEW ============ */}
      {viewMode === "list" && (
        <>
          {postsArray.length === 0 ? (
            <div style={{ ...cardStyle, textAlign: "center", padding: "60px 20px" }}>
              <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>&#128225;</div>
              <h3 style={{ margin: "0 0 8px", color: "var(--text-primary)" }}>No social posts yet</h3>
              <p style={{ color: "var(--text-secondary)", margin: "0 0 16px", maxWidth: 440, marginInline: "auto" }}>
                Create your first social media post or use AI to generate a full content calendar.
                Posts can be scheduled for automatic publishing across Facebook, Instagram, Twitter/X, LinkedIn, and Google Business.
              </p>
              <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
                <button onClick={() => setShowCampaignGen(true)} style={btnSecondary}>
                  AI Content Calendar
                </button>
                <button onClick={() => setShowCreatePost(true)} style={btnPrimary}>
                  + Create Post
                </button>
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {postsArray.map((post) => (
                <div key={post.id} style={{
                  ...cardStyle, padding: "14px 20px", cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  transition: "background 0.15s",
                }} onClick={() => setEditingPost(post)}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1, minWidth: 0 }}>
                    <PlatformIcon platform={post.platform} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontWeight: 600, color: "var(--text-primary)", marginBottom: 4,
                        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                      }}>
                        {(post.content || "").slice(0, 100) || "Untitled post"}
                      </div>
                      <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                        {PLATFORM_MAP[post.platform]?.label || post.platform}
                        {" \u00B7 "}
                        {post.scheduled_for
                          ? `Scheduled: ${new Date(post.scheduled_for).toLocaleDateString()}`
                          : timeAgo(post.created_at)}
                        {post.hashtags && <span> &middot; {post.hashtags}</span>}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <StatusBadge status={post.status} />
                    <button onClick={(e) => { e.stopPropagation(); handleDeletePost(post.id); }}
                      style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "4px 8px", borderRadius: 6, fontSize: "0.85rem" }}
                      title="Delete">
                      &#x2715;
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ============ CALENDAR VIEW ============ */}
      {viewMode === "calendar" && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <button onClick={() => setCalendarMonth((m) => {
              const d = new Date(m.year, m.month - 1, 1);
              return { year: d.getFullYear(), month: d.getMonth() };
            })} style={btnSecondary}>&larr;</button>
            <h3 style={{ margin: 0, color: "var(--text-primary)", fontSize: "1rem" }}>
              {MONTH_NAMES[calendarMonth.month]} {calendarMonth.year}
            </h3>
            <button onClick={() => setCalendarMonth((m) => {
              const d = new Date(m.year, m.month + 1, 1);
              return { year: d.getFullYear(), month: d.getMonth() };
            })} style={btnSecondary}>&rarr;</button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 2 }}>
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
              <div key={d} style={{ textAlign: "center", fontSize: "0.7rem", color: "var(--text-muted)", padding: "6px 0", fontWeight: 600 }}>{d}</div>
            ))}
            {Array.from({ length: calendarStartDay }, (_, i) => (
              <div key={`empty-${i}`} style={{ minHeight: 80 }} />
            ))}
            {Array.from({ length: calendarDays }, (_, i) => {
              const day = i + 1;
              const dayPosts = getPostsForDate(day);
              const isToday = (() => {
                const now = new Date();
                return now.getFullYear() === calendarMonth.year && now.getMonth() === calendarMonth.month && now.getDate() === day;
              })();
              return (
                <div key={day} style={{
                  minHeight: 80, background: isToday ? "var(--accent-dim)" : "var(--bg-secondary, var(--card-bg))",
                  border: isToday ? "2px solid var(--accent)" : "1px solid var(--border)",
                  borderRadius: 6, padding: "4px 6px", overflow: "hidden",
                }}>
                  <div style={{ fontSize: "0.7rem", fontWeight: 600, color: isToday ? "var(--accent)" : "var(--text-secondary)", marginBottom: 2 }}>
                    {day}
                  </div>
                  {dayPosts.map((post) => (
                    <div key={post.id} onClick={() => setEditingPost(post)} style={{
                      fontSize: "0.6rem", padding: "2px 4px", borderRadius: 3,
                      background: PLATFORM_MAP[post.platform]?.color || "var(--accent)",
                      color: post.platform === "twitter" ? "#fff" : "#fff",
                      marginBottom: 2, cursor: "pointer", whiteSpace: "nowrap",
                      overflow: "hidden", textOverflow: "ellipsis", fontWeight: 500,
                    }} title={`${PLATFORM_MAP[post.platform]?.label}: ${(post.content || "").slice(0, 60)}`}>
                      {PLATFORM_MAP[post.platform]?.icon} {(post.content || "").slice(0, 30)}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ============ ANALYTICS VIEW ============ */}
      {viewMode === "analytics" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {/* Posts by Platform */}
          <div style={cardStyle}>
            <h3 style={{ margin: "0 0 16px", fontSize: "1rem", color: "var(--text-primary)" }}>Posts by Platform</h3>
            {totalPosts === 0 ? (
              <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>
                Create posts to see platform distribution here.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={platformCounts}>
                  <XAxis dataKey="name" tick={{ fill: "var(--text-secondary)", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "var(--text-secondary)", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: "var(--bg-primary)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text-primary)" }} />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                    {platformCounts.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Publishing Activity */}
          <div style={cardStyle}>
            <h3 style={{ margin: "0 0 16px", fontSize: "1rem", color: "var(--text-primary)" }}>Publishing Summary</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {[
                { label: "This Week", value: postsArray.filter((p) => {
                  const d = new Date(p.published_at || p.created_at);
                  const weekAgo = new Date(); weekAgo.setDate(weekAgo.getDate() - 7);
                  return d >= weekAgo;
                }).length, color: "var(--accent)" },
                { label: "This Month", value: postsArray.filter((p) => {
                  const d = new Date(p.published_at || p.created_at);
                  const monthAgo = new Date(); monthAgo.setDate(monthAgo.getDate() - 30);
                  return d >= monthAgo;
                }).length, color: "var(--green)" },
                { label: "Avg. Posts/Week", value: totalPosts > 0
                  ? Math.round((totalPosts / Math.max(1, Math.ceil((Date.now() - new Date(postsArray[postsArray.length - 1]?.created_at || Date.now()).getTime()) / (7 * 86400000)))) * 10) / 10
                  : 0, color: "var(--purple, #8b5cf6)" },
              ].map((row) => (
                <div key={row.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>{row.label}</span>
                  <span style={{ fontSize: "1.25rem", fontWeight: 700, color: row.color }}>{row.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ============ CREATE POST MODAL ============ */}
      {showCreatePost && (
        <CreatePostModal
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setShowCreatePost(false)}
          onCreated={() => { setShowCreatePost(false); loadPosts(); }}
        />
      )}

      {/* ============ AI GENERATE SINGLE POST ============ */}
      {showAiGenerate && (
        <AiGenerateModal
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setShowAiGenerate(false)}
          onGenerated={(content) => {
            setShowAiGenerate(false);
            setShowCreatePost(true);
          }}
        />
      )}

      {/* ============ AI CAMPAIGN GENERATOR ============ */}
      {showCampaignGen && (
        <CampaignGeneratorModal
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setShowCampaignGen(false)}
          onGenerated={() => { setShowCampaignGen(false); loadPosts(); }}
        />
      )}

      {/* ============ EDIT POST MODAL ============ */}
      {editingPost && (
        <EditPostModal
          tenantId={user?.tenantId}
          token={token}
          post={editingPost}
          onClose={() => setEditingPost(null)}
          onSaved={() => { setEditingPost(null); loadPosts(); }}
          onDelete={() => { handleDeletePost(editingPost.id); setEditingPost(null); }}
        />
      )}
    </div>
  );
}

/* ==== Create Post Modal ==== */

function CreatePostModal({ tenantId, token, onClose, onCreated }) {
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
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const activePlatformLimit = Math.min(...selectedPlatforms.map((p) => CHAR_LIMITS[p] || 2200));

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
          hashtags: hashtags.trim() ? hashtags.split(",").map((h) => h.trim()).filter(Boolean) : [],
          status: postNow ? "published" : scheduleDate ? "scheduled" : "draft",
          scheduled_for: scheduleDate && scheduleTime
            ? `${scheduleDate}T${scheduleTime}:00`
            : scheduleDate ? `${scheduleDate}T09:00:00` : null,
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
        <h2 style={{ margin: "0 0 20px", color: "var(--text-primary)", fontSize: "1.2rem" }}>Create Post</h2>

        {/* Platform selector */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Platforms</label>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {PLATFORMS.map((p) => (
              <button key={p.key} onClick={() => togglePlatform(p.key)} style={{
                padding: "8px 14px", borderRadius: 8, fontSize: "0.85rem", cursor: "pointer",
                display: "flex", alignItems: "center", gap: 6,
                border: selectedPlatforms.includes(p.key) ? `2px solid ${p.color}` : "1px solid var(--border)",
                background: selectedPlatforms.includes(p.key) ? `${p.color}15` : "var(--bg-primary)",
                color: selectedPlatforms.includes(p.key) ? p.color : "var(--text-secondary)",
                fontWeight: selectedPlatforms.includes(p.key) ? 600 : 400,
              }}>
                <PlatformIcon platform={p.key} size={18} /> {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Content</label>
          <textarea value={content} onChange={(e) => setContent(e.target.value)}
            placeholder="Write your post content..."
            rows={6} maxLength={activePlatformLimit}
            style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit", lineHeight: 1.6 }} />
          <div style={{ fontSize: "0.75rem", color: content.length > activePlatformLimit * 0.9 ? "#f87171" : "var(--text-muted)", marginTop: 4, textAlign: "right" }}>
            {content.length} / {activePlatformLimit}
          </div>
        </div>

        {/* Hashtags */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Hashtags</label>
          <input type="text" value={hashtags} onChange={(e) => setHashtags(e.target.value)}
            placeholder="#marketing #business #tips"
            style={inputStyle} />
        </div>

        {/* Schedule */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Schedule</label>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", color: "var(--text-secondary)", fontSize: "0.85rem" }}>
              <input type="checkbox" checked={postNow} onChange={(e) => { setPostNow(e.target.checked); if (e.target.checked) { setScheduleDate(""); setScheduleTime(""); } }} />
              Post Now
            </label>
            {!postNow && (
              <>
                <input type="date" value={scheduleDate} onChange={(e) => setScheduleDate(e.target.value)}
                  style={{ ...inputStyle, width: "auto" }} />
                <input type="time" value={scheduleTime} onChange={(e) => setScheduleTime(e.target.value)}
                  style={{ ...inputStyle, width: "auto" }} />
              </>
            )}
          </div>
        </div>

        {error && <div style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 12 }}>{error}</div>}

        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={btnSecondary}>Cancel</button>
          <button onClick={handleSubmit} disabled={submitting}
            style={{ ...btnPrimary, opacity: submitting ? 0.6 : 1, cursor: submitting ? "default" : "pointer" }}>
            {submitting ? "Creating..." : postNow ? "Publish Now" : scheduleDate ? "Schedule Post" : "Save as Draft"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ==== AI Generate Single Post Modal ==== */

function AiGenerateModal({ tenantId, token, onClose, onGenerated }) {
  const [topic, setTopic] = useState("");
  const [platform, setPlatform] = useState("facebook");
  const [tone, setTone] = useState("professional");
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleGenerate = async () => {
    if (!topic.trim()) { setError("Please enter a topic."); return; }
    setGenerating(true);
    setError(null);
    try {
      const res = await generateSocialContent(tenantId, token, { topic: topic.trim(), platform, tone });
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
        platform, content: result.content, hashtags: result.hashtags || null, status: "draft",
      });
      onGenerated(result.content);
    } catch (e) {
      setError(e.message || "Failed to save post");
    }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={modalStyle}>
        <h2 style={{ margin: "0 0 20px", color: "var(--text-primary)", fontSize: "1.2rem" }}>
          Generate Post with AI
        </h2>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Topic</label>
          <input type="text" value={topic} onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., Spring cleaning tips for homeowners"
            style={inputStyle} />
        </div>

        <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Platform</label>
            <select value={platform} onChange={(e) => setPlatform(e.target.value)}
              style={{ ...inputStyle, width: "100%" }}>
              {PLATFORMS.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Tone</label>
            <select value={tone} onChange={(e) => setTone(e.target.value)}
              style={{ ...inputStyle, width: "100%", textTransform: "capitalize" }}>
              {TONES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>

        {result && (
          <div style={{ ...cardStyle, marginBottom: 16, background: "var(--bg-primary)" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 600, textTransform: "uppercase", color: "var(--accent)", marginBottom: 8 }}>
              Generated Content
            </div>
            <div style={{ fontSize: "0.9rem", color: "var(--text-primary)", whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
              {result.content}
            </div>
            {result.hashtags && (
              <div style={{ marginTop: 8, fontSize: "0.85rem", color: "var(--accent)" }}>{result.hashtags}</div>
            )}
          </div>
        )}

        {error && <div style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 12 }}>{error}</div>}

        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={btnSecondary}>Cancel</button>
          {result ? (
            <button onClick={handleUse} style={btnPrimary}>Save as Draft</button>
          ) : (
            <button onClick={handleGenerate} disabled={generating}
              style={{ ...btnPrimary, opacity: generating ? 0.6 : 1 }}>
              {generating ? "Generating..." : "Generate"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ==== AI Campaign Generator Modal ==== */

function CampaignGeneratorModal({ tenantId, token, onClose, onGenerated }) {
  const [topic, setTopic] = useState("");
  const [selectedPlatforms, setSelectedPlatforms] = useState(["facebook", "instagram", "linkedin"]);
  const [postsPerWeek, setPostsPerWeek] = useState(3);
  const [generating, setGenerating] = useState(false);
  const [generatedPosts, setGeneratedPosts] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const togglePlatform = (key) => {
    setSelectedPlatforms((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
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
      <div onClick={(e) => e.stopPropagation()} style={{ ...modalStyle, maxWidth: 800 }}>
        <h2 style={{ margin: "0 0 20px", color: "var(--text-primary)", fontSize: "1.2rem" }}>
          AI Content Calendar Generator
        </h2>

        {generatedPosts.length === 0 ? (
          <>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Topic / Theme</label>
              <input type="text" value={topic} onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g., Home renovation tips, spring specials, customer success stories"
                style={inputStyle} />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Platforms</label>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {PLATFORMS.map((p) => (
                  <button key={p.key} onClick={() => togglePlatform(p.key)} style={{
                    padding: "8px 14px", borderRadius: 8, fontSize: "0.85rem", cursor: "pointer",
                    display: "flex", alignItems: "center", gap: 6,
                    border: selectedPlatforms.includes(p.key) ? `2px solid ${p.color}` : "1px solid var(--border)",
                    background: selectedPlatforms.includes(p.key) ? `${p.color}15` : "var(--bg-primary)",
                    color: selectedPlatforms.includes(p.key) ? p.color : "var(--text-secondary)",
                    fontWeight: selectedPlatforms.includes(p.key) ? 600 : 400,
                  }}>
                    <PlatformIcon platform={p.key} size={18} /> {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Posts per week</label>
              <select value={postsPerWeek} onChange={(e) => setPostsPerWeek(Number(e.target.value))}
                style={{ ...inputStyle, width: "auto", maxWidth: 120 }}>
                {[1, 2, 3, 5, 7].map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>

            {error && <div style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 12 }}>{error}</div>}

            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button onClick={onClose} style={btnSecondary}>Cancel</button>
              <button onClick={handleGenerate} disabled={generating}
                style={{ ...btnPrimary, opacity: generating ? 0.6 : 1 }}>
                {generating ? "Generating calendar..." : "Generate Content Calendar"}
              </button>
            </div>
          </>
        ) : (
          <>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", margin: "0 0 16px" }}>
              {generatedPosts.length} posts generated. Review, edit, or remove posts before saving.
            </p>
            <div style={{ maxHeight: 400, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
              {generatedPosts.map((post, idx) => (
                <div key={idx} style={{ ...cardStyle, padding: "12px 16px", background: "var(--bg-primary)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <PlatformIcon platform={post.platform} size={20} />
                      <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-primary)" }}>
                        {PLATFORM_MAP[post.platform]?.label}
                      </span>
                      {post.scheduled_for && (
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                          {new Date(post.scheduled_for).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <button onClick={() => removePost(idx)}
                      style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "0.85rem" }}>
                      &#x2715;
                    </button>
                  </div>
                  <div style={{ fontSize: "0.85rem", color: "var(--text-primary)", whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
                    {post.content}
                  </div>
                  {post.hashtags && (
                    <div style={{ marginTop: 4, fontSize: "0.8rem", color: "var(--accent)" }}>{post.hashtags}</div>
                  )}
                </div>
              ))}
            </div>

            {error && <div style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 12 }}>{error}</div>}

            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button onClick={() => setGeneratedPosts([])} style={btnSecondary}>Back</button>
              <button onClick={onClose} style={btnSecondary}>Cancel</button>
              <button onClick={handleSaveAll} disabled={saving}
                style={{ ...btnPrimary, opacity: saving ? 0.6 : 1 }}>
                {saving ? "Saving..." : `Save All ${generatedPosts.length} Posts as Drafts`}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/* ==== Edit Post Modal ==== */

function EditPostModal({ tenantId, token, post, onClose, onSaved, onDelete }) {
  const [content, setContent] = useState(post.content || "");
  const [hashtags, setHashtags] = useState(Array.isArray(post.hashtags) ? post.hashtags.join(", ") : post.hashtags || "");
  const [scheduleDate, setScheduleDate] = useState(post.scheduled_for ? post.scheduled_for.split("T")[0] : "");
  const [scheduleTime, setScheduleTime] = useState(
    post.scheduled_for && post.scheduled_for.includes("T") ? post.scheduled_for.split("T")[1]?.slice(0, 5) : ""
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const charLimit = CHAR_LIMITS[post.platform] || 2200;

  const handleSave = async () => {
    if (!content.trim()) { setError("Content is required."); return; }
    setSaving(true);
    setError(null);
    try {
      const data = {
        content: content.trim(),
        hashtags: hashtags.trim() ? hashtags.split(",").map((h) => h.trim()).filter(Boolean) : [],
        scheduled_for: scheduleDate && scheduleTime
          ? `${scheduleDate}T${scheduleTime}:00`
          : scheduleDate ? `${scheduleDate}T09:00:00` : null,
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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <PlatformIcon platform={post.platform} size={28} />
            <h2 style={{ margin: 0, color: "var(--text-primary)", fontSize: "1.2rem" }}>
              Edit {PLATFORM_MAP[post.platform]?.label} Post
            </h2>
          </div>
          <StatusBadge status={post.status} />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Content</label>
          <textarea value={content} onChange={(e) => setContent(e.target.value)}
            rows={6} maxLength={charLimit}
            style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit", lineHeight: 1.6 }} />
          <div style={{ fontSize: "0.75rem", color: content.length > charLimit * 0.9 ? "#f87171" : "var(--text-muted)", marginTop: 4, textAlign: "right" }}>
            {content.length} / {charLimit}
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Hashtags</label>
          <input type="text" value={hashtags} onChange={(e) => setHashtags(e.target.value)}
            placeholder="#hashtag1 #hashtag2"
            style={inputStyle} />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Schedule</label>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <input type="date" value={scheduleDate} onChange={(e) => setScheduleDate(e.target.value)}
              style={{ ...inputStyle, width: "auto" }} />
            <input type="time" value={scheduleTime} onChange={(e) => setScheduleTime(e.target.value)}
              style={{ ...inputStyle, width: "auto" }} />
            {scheduleDate && (
              <button onClick={() => { setScheduleDate(""); setScheduleTime(""); }}
                style={{ ...btnSecondary, fontSize: "0.8rem", padding: "6px 12px" }}>
                Clear
              </button>
            )}
          </div>
        </div>

        {error && <div style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 12 }}>{error}</div>}

        <div style={{ display: "flex", gap: 12, justifyContent: "space-between" }}>
          <button onClick={onDelete} style={{ ...btnSecondary, color: "#f87171", borderColor: "#f8717130" }}>
            Delete Post
          </button>
          <div style={{ display: "flex", gap: 12 }}>
            <button onClick={onClose} style={btnSecondary}>Cancel</button>
            <button onClick={handleSave} disabled={saving}
              style={{ ...btnPrimary, opacity: saving ? 0.6 : 1 }}>
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---- Shared modal styles ---- */

const overlayStyle = {
  position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
  display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
};

const modalStyle = {
  background: "var(--bg-secondary, var(--card-bg))", borderRadius: 16,
  padding: "28px 32px", width: "90%", maxWidth: 700, maxHeight: "90vh",
  overflowY: "auto", border: "1px solid var(--border)",
};

const labelStyle = {
  display: "block", fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 6,
};
