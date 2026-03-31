import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  fetchSnippets, createSnippet, updateSnippet, deleteSnippet,
} from "../utils/api/snippets";

const CATEGORIES = ["All", "General", "Pricing", "Hours", "Services", "Custom"];

const CATEGORY_COLORS = {
  general: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  pricing: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  hours: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  services: { color: "#8b5cf6", bg: "rgba(139,92,246,0.1)" },
  custom: { color: "#ec4899", bg: "rgba(236,72,153,0.1)" },
};

const emptyForm = {
  title: "",
  content: "",
  category: "general",
  shortcut: "",
};

function truncate(str, max = 100) {
  if (!str) return "";
  return str.length > max ? str.slice(0, max) + "..." : str;
}

export default function SnippetsPage() {
  const { user, token } = useAuth();
  const [snippets, setSnippets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [activeCategory, setActiveCategory] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");

  // Modal
  const [showModal, setShowModal] = useState(false);
  const [editSnippet, setEditSnippet] = useState(null);
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);

  // Track deleting IDs
  const [deletingIds, setDeletingIds] = useState(new Set());

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const params = {};
      if (activeCategory !== "All") params.category = activeCategory.toLowerCase();
      if (searchQuery.trim()) params.search = searchQuery.trim();
      const data = await fetchSnippets(user.tenantId, token, params);
      setSnippets(data.snippets || data || []);
      setError(null);
    } catch (err) {
      console.warn("Failed to load snippets:", err.message);
      setError(err.message || "Failed to load snippets");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, activeCategory, searchQuery]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  const openCreate = () => {
    setEditSnippet(null);
    setForm({ ...emptyForm });
    setShowModal(true);
  };

  const openEdit = (snippet) => {
    setEditSnippet(snippet);
    setForm({
      title: snippet.title || "",
      content: snippet.content || "",
      category: snippet.category || "general",
      shortcut: snippet.shortcut || "",
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.title.trim() || !form.content.trim()) return;
    setSaving(true);
    const body = {
      title: form.title.trim(),
      content: form.content.trim(),
      category: form.category,
    };
    if (form.shortcut.trim()) {
      body.shortcut = form.shortcut.trim();
    }
    try {
      if (editSnippet) {
        await updateSnippet(user.tenantId, token, editSnippet.id, body);
      } else {
        await createSnippet(user.tenantId, token, body);
      }
      setShowModal(false);
      setForm({ ...emptyForm });
      setEditSnippet(null);
      loadData();
    } catch (err) {
      console.warn("Save snippet failed:", err.message);
      setError(err.message || "Failed to save snippet");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (snippetId) => {
    if (!window.confirm("Delete this snippet? This cannot be undone.")) return;
    setDeletingIds((prev) => new Set(prev).add(snippetId));
    try {
      await deleteSnippet(user.tenantId, token, snippetId);
      setSnippets((prev) => prev.filter((s) => s.id !== snippetId));
      setError(null);
    } catch (err) {
      console.warn("Delete snippet failed:", err.message);
      setError(err.message || "Failed to delete snippet");
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(snippetId);
        return next;
      });
    }
  };

  if (loading) return <SkeletonLoader />;

  // Client-side filtering for search (API may also filter, but ensure local consistency)
  const filteredSnippets = snippets;

  const totalCount = snippets.length;
  const categoryBreakdown = {};
  snippets.forEach((s) => {
    const cat = (s.category || "general").toLowerCase();
    categoryBreakdown[cat] = (categoryBreakdown[cat] || 0) + 1;
  });

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Snippets / Quick Replies</h1>
          <p>Reusable response templates for fast, consistent messaging</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            className="btn-primary"
            onClick={() => {
              setLoading(true);
              loadData();
            }}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
            }}
          >
            Refresh
          </button>
          <button className="btn-primary" onClick={openCreate}>
            + New Snippet
          </button>
        </div>
      </div>

      {/* Category Tabs */}
      <div
        style={{
          display: "flex",
          gap: 6,
          marginBottom: 16,
          flexWrap: "wrap",
        }}
      >
        {CATEGORIES.map((cat) => {
          const isActive = activeCategory === cat;
          const count =
            cat === "All"
              ? totalCount
              : categoryBreakdown[cat.toLowerCase()] || 0;
          return (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border: isActive
                  ? "1px solid var(--accent)"
                  : "1px solid var(--border)",
                background: isActive ? "var(--accent-dim)" : "var(--bg-secondary)",
                color: isActive ? "var(--accent)" : "var(--text-secondary)",
                cursor: "pointer",
                fontSize: "0.85rem",
                fontWeight: isActive ? 600 : 400,
                transition: "all 0.15s ease",
              }}
            >
              {cat}
              <span
                style={{
                  marginLeft: 6,
                  fontSize: "0.75rem",
                  opacity: 0.7,
                }}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Search Bar */}
      <div style={{ marginBottom: 20 }}>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search snippets by title or content..."
          style={{
            width: "100%",
            maxWidth: 400,
            padding: "10px 14px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: "var(--bg-secondary)",
            color: "var(--text-primary)",
            fontSize: "0.9rem",
          }}
        />
      </div>

      {error && (
        <div
          style={{
            marginBottom: 16,
            padding: "10px 16px",
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 8,
            color: "#ef4444",
            fontSize: "0.85rem",
          }}
        >
          {error}
          <button
            onClick={() => setError(null)}
            style={{
              marginLeft: 12,
              background: "none",
              border: "none",
              color: "#ef4444",
              cursor: "pointer",
              fontSize: "0.8rem",
              textDecoration: "underline",
            }}
          >
            dismiss
          </button>
        </div>
      )}

      {/* Snippets Grid */}
      {filteredSnippets.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>
            {activeCategory !== "All" || searchQuery.trim()
              ? "No snippets match your search"
              : "No snippets yet"}
          </div>
          <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
            {activeCategory !== "All" || searchQuery.trim()
              ? "Try adjusting your filters or search query. You can also clear filters to see all snippets."
              : "Create your first quick reply template. Team members can use these for fast, consistent responses in conversations and follow-ups."}
          </p>
          {activeCategory !== "All" || searchQuery.trim() ? (
            <button
              className="btn-primary"
              onClick={() => {
                setActiveCategory("All");
                setSearchQuery("");
              }}
              style={{
                background: "transparent",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
              }}
            >
              Clear Filters
            </button>
          ) : (
            <button className="btn-primary" onClick={openCreate}>
              Create Your First Snippet
            </button>
          )}
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
            gap: 14,
          }}
        >
          {filteredSnippets.map((snippet) => {
            const catKey = (snippet.category || "general").toLowerCase();
            const catColor = CATEGORY_COLORS[catKey] || CATEGORY_COLORS.general;
            const isDeleting = deletingIds.has(snippet.id);

            return (
              <div
                key={snippet.id}
                style={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  padding: 16,
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                  opacity: isDeleting ? 0.5 : 1,
                  transition: "opacity 0.2s ease",
                }}
              >
                {/* Header: title + category badge */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    gap: 8,
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: "1rem", flex: 1, minWidth: 0 }}>
                    {snippet.title}
                  </div>
                  <span
                    style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: 4,
                      fontSize: "0.7rem",
                      fontWeight: 600,
                      color: catColor.color,
                      background: catColor.bg,
                      textTransform: "capitalize",
                      whiteSpace: "nowrap",
                      flexShrink: 0,
                    }}
                  >
                    {snippet.category || "general"}
                  </span>
                </div>

                {/* Content preview */}
                <div
                  style={{
                    fontSize: "0.85rem",
                    color: "var(--text-secondary)",
                    lineHeight: 1.5,
                    flex: 1,
                  }}
                >
                  {truncate(snippet.content, 120)}
                </div>

                {/* Meta row: shortcut + usage count */}
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 8,
                    alignItems: "center",
                  }}
                >
                  {snippet.shortcut && (
                    <span
                      style={{
                        display: "inline-block",
                        padding: "3px 8px",
                        borderRadius: 4,
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        fontFamily: "monospace",
                        color: "var(--accent)",
                        background: "var(--accent-dim)",
                        border: "1px solid rgba(59,130,246,0.2)",
                      }}
                    >
                      /{snippet.shortcut}
                    </span>
                  )}
                  {snippet.usage_count !== undefined && snippet.usage_count !== null && (
                    <span
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--text-muted)",
                      }}
                    >
                      Used {snippet.usage_count} time{snippet.usage_count !== 1 ? "s" : ""}
                    </span>
                  )}
                </div>

                {/* Action buttons */}
                <div
                  style={{
                    display: "flex",
                    gap: 6,
                    justifyContent: "flex-end",
                    borderTop: "1px solid var(--border)",
                    paddingTop: 10,
                    marginTop: 2,
                  }}
                >
                  <button
                    onClick={() => openEdit(snippet)}
                    disabled={isDeleting}
                    style={{
                      background: "none",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      padding: "6px 12px",
                      color: "var(--text-secondary)",
                      cursor: "pointer",
                      fontSize: "0.8rem",
                    }}
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(snippet.id)}
                    disabled={isDeleting}
                    style={{
                      background: "none",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      padding: "6px 12px",
                      color: "var(--red, #ef4444)",
                      cursor: "pointer",
                      fontSize: "0.8rem",
                    }}
                  >
                    {isDeleting ? "..." : "Delete"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setShowModal(false)}
        >
          <div
            style={{
              background: "var(--bg-primary)",
              borderRadius: 12,
              padding: 24,
              width: "90%",
              maxWidth: 520,
              maxHeight: "80vh",
              overflowY: "auto",
              border: "1px solid var(--border)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 16 }}>
              {editSnippet ? "Edit Snippet" : "Create New Snippet"}
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.8rem",
                    marginBottom: 4,
                    color: "var(--text-secondary)",
                  }}
                >
                  Title *
                </label>
                <input
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  placeholder="e.g. Business Hours, Pricing Info, Thank You"
                  style={{ width: "100%" }}
                />
              </div>

              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.8rem",
                    marginBottom: 4,
                    color: "var(--text-secondary)",
                  }}
                >
                  Content *
                </label>
                <textarea
                  value={form.content}
                  onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))}
                  placeholder="Type the full response template here. You can include links, formatting, and placeholders..."
                  rows={5}
                  style={{ width: "100%", resize: "vertical" }}
                />
              </div>

              <div style={{ display: "flex", gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "0.8rem",
                      marginBottom: 4,
                      color: "var(--text-secondary)",
                    }}
                  >
                    Category
                  </label>
                  <select
                    value={form.category}
                    onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontSize: "0.85rem",
                      cursor: "pointer",
                    }}
                  >
                    <option value="general">General</option>
                    <option value="pricing">Pricing</option>
                    <option value="hours">Hours</option>
                    <option value="services">Services</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "0.8rem",
                      marginBottom: 4,
                      color: "var(--text-secondary)",
                    }}
                  >
                    Shortcut (optional)
                  </label>
                  <div style={{ position: "relative" }}>
                    <span
                      style={{
                        position: "absolute",
                        left: 10,
                        top: "50%",
                        transform: "translateY(-50%)",
                        color: "var(--text-muted)",
                        fontSize: "0.9rem",
                        fontFamily: "monospace",
                        pointerEvents: "none",
                      }}
                    >
                      /
                    </span>
                    <input
                      value={form.shortcut}
                      onChange={(e) =>
                        setForm((f) => ({
                          ...f,
                          shortcut: e.target.value.replace(/[^a-zA-Z0-9_-]/g, ""),
                        }))
                      }
                      placeholder="e.g. hours, pricing"
                      style={{
                        width: "100%",
                        paddingLeft: 22,
                      }}
                    />
                  </div>
                  <div
                    style={{
                      fontSize: "0.7rem",
                      color: "var(--text-muted)",
                      marginTop: 4,
                    }}
                  >
                    Team members can type /{form.shortcut || "shortcut"} to insert this reply
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
              <button
                onClick={() => {
                  setShowModal(false);
                  setEditSnippet(null);
                }}
                style={{
                  background: "transparent",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: "8px 16px",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleSave}
                disabled={!form.title.trim() || !form.content.trim() || saving}
              >
                {saving
                  ? "Saving..."
                  : editSnippet
                  ? "Save Changes"
                  : "Create Snippet"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
