import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import { notify } from "../../utils/notify";
import {
  fetchSocialPosts,
  deleteSocialPost,
  fetchSocialAnalytics,
} from "../../utils/api/social";
import SkeletonLoader from "../../components/SkeletonLoader";
import { PLATFORMS } from "./constants";
import { cardStyle, inputStyle, btnPrimary, btnSecondary } from "./styles";
import ListView from "./ListView";
import CalendarView from "./CalendarView";
import AnalyticsView from "./AnalyticsView";
import CreatePostModal from "./CreatePostModal";
import AiGenerateModal from "./AiGenerateModal";
import CampaignGeneratorModal from "./CampaignGeneratorModal";
import EditPostModal from "./EditPostModal";

export default function SocialMediaPage() {
  const { user, token } = useAuth();

  const [posts, setPosts] = useState([]);
  const [, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  const [platformFilter, setPlatformFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [viewMode, setViewMode] = useState("list");
  const [calendarMonth, setCalendarMonth] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });

  const [showCreatePost, setShowCreatePost] = useState(false);
  const [showAiGenerate, setShowAiGenerate] = useState(false);
  const [showCampaignGen, setShowCampaignGen] = useState(false);
  const [editingPost, setEditingPost] = useState(null);

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

  useEffect(() => {
    loadPosts();
  }, [loadPosts]);
  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  const handleDeletePost = async (postId) => {
    if (!confirm("Delete this post?")) return;
    try {
      await deleteSocialPost(user.tenantId, token, postId);
      loadPosts();
    } catch (e) {
      notify.error("Failed to delete: " + (e.message || "Unknown error"));
    }
  };

  const postsArray = Array.isArray(posts) ? posts : [];
  const totalPosts = postsArray.length;
  const scheduledCount = postsArray.filter(
    (p) => p.status === "scheduled",
  ).length;
  const publishedCount = postsArray.filter(
    (p) => p.status === "published",
  ).length;
  const draftCount = postsArray.filter((p) => p.status === "draft").length;

  if (loading && postsArray.length === 0) return <SkeletonLoader />;

  const statCards = [
    { label: "Total Posts", value: totalPosts, color: "var(--accent)" },
    { label: "Published", value: publishedCount, color: "var(--green)" },
    {
      label: "Scheduled",
      value: scheduledCount,
      color: "var(--purple, #8b5cf6)",
    },
    { label: "Drafts", value: draftCount, color: "var(--text-secondary)" },
  ];

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1200 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 24,
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              margin: 0,
              color: "var(--text-primary)",
            }}
          >
            Social Media
          </h1>
          <p
            style={{
              color: "var(--text-secondary)",
              margin: "4px 0 0",
              fontSize: "0.9rem",
            }}
          >
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

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 16,
          marginBottom: 24,
        }}
      >
        {statCards.map((s) => (
          <div key={s.label} style={cardStyle}>
            <div
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                marginBottom: 4,
              }}
            >
              {s.label}
            </div>
            <div
              style={{ fontSize: "1.5rem", fontWeight: 700, color: s.color }}
            >
              {s.value}
            </div>
          </div>
        ))}
      </div>

      <div
        style={{
          display: "flex",
          gap: 12,
          marginBottom: 20,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <select
          value={platformFilter}
          onChange={(e) => setPlatformFilter(e.target.value)}
          style={{ ...inputStyle, width: "auto", maxWidth: 180 }}
        >
          <option value="">All platforms</option>
          {PLATFORMS.map((p) => (
            <option key={p.key} value={p.key}>
              {p.label}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ ...inputStyle, width: "auto", maxWidth: 160 }}
        >
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="scheduled">Scheduled</option>
          <option value="published">Published</option>
        </select>
        <button
          onClick={() => setShowAiGenerate(true)}
          style={{
            ...btnSecondary,
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <span style={{ fontSize: "1rem" }}>&#x2728;</span> Generate with AI
        </button>
        <div style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
          {["list", "calendar", "analytics"].map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              style={{
                padding: "7px 14px",
                borderRadius: 8,
                textTransform: "capitalize",
                fontSize: "0.8rem",
                border:
                  viewMode === mode
                    ? "2px solid var(--accent)"
                    : "1px solid var(--border)",
                background:
                  viewMode === mode
                    ? "var(--accent-dim)"
                    : "var(--bg-secondary, var(--card-bg))",
                color:
                  viewMode === mode ? "var(--accent)" : "var(--text-secondary)",
                cursor: "pointer",
                fontWeight: viewMode === mode ? 600 : 400,
              }}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {viewMode === "list" && (
        <ListView
          posts={postsArray}
          onEdit={setEditingPost}
          onDelete={handleDeletePost}
          onShowCreatePost={() => setShowCreatePost(true)}
          onShowCampaignGen={() => setShowCampaignGen(true)}
        />
      )}

      {viewMode === "calendar" && (
        <CalendarView
          posts={postsArray}
          calendarMonth={calendarMonth}
          setCalendarMonth={setCalendarMonth}
          onEdit={setEditingPost}
        />
      )}

      {viewMode === "analytics" && <AnalyticsView posts={postsArray} />}

      {showCreatePost && (
        <CreatePostModal
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setShowCreatePost(false)}
          onCreated={() => {
            setShowCreatePost(false);
            loadPosts();
          }}
        />
      )}

      {showAiGenerate && (
        <AiGenerateModal
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setShowAiGenerate(false)}
          onGenerated={() => {
            setShowAiGenerate(false);
            setShowCreatePost(true);
          }}
        />
      )}

      {showCampaignGen && (
        <CampaignGeneratorModal
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setShowCampaignGen(false)}
          onGenerated={() => {
            setShowCampaignGen(false);
            loadPosts();
          }}
        />
      )}

      {editingPost && (
        <EditPostModal
          tenantId={user?.tenantId}
          token={token}
          post={editingPost}
          onClose={() => setEditingPost(null)}
          onSaved={() => {
            setEditingPost(null);
            loadPosts();
          }}
          onDelete={() => {
            handleDeletePost(editingPost.id);
            setEditingPost(null);
          }}
        />
      )}
    </div>
  );
}
