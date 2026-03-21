import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchContentItems, createContentItem, deleteContentItem, repurposeContent, fetchContentItem, updateContentItem } from "../utils/api/content";

const SOURCE_TYPES = [
  { key: "text", label: "Blog Post / Article", placeholder: "Paste your blog post, article, or any long-form content here..." },
  { key: "description", label: "Job / Project Description", placeholder: "Describe a recent job or project you completed. Include details like what you did, the result, and what made it special..." },
  { key: "file", label: "Upload Text File", placeholder: "" },
];

const STATUS_LABELS = {
  draft: { label: "Draft", color: "var(--text-secondary)", bg: "var(--hover-overlay)" },
  generated: { label: "Generated", color: "var(--accent)", bg: "var(--accent-dim)" },
  scheduled: { label: "Scheduled", color: "var(--purple)", bg: "rgba(139, 92, 246, 0.15)" },
  published: { label: "Published", color: "var(--green)", bg: "var(--green-dim)" },
};

function StatusBadge({ status }) {
  const s = STATUS_LABELS[status] || STATUS_LABELS.draft;
  return (
    <span style={{
      padding: "2px 10px",
      borderRadius: "12px",
      fontSize: "0.75rem",
      fontWeight: 600,
      color: s.color,
      background: s.bg,
    }}>
      {s.label}
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

export default function ContentStudioPage() {
  const { user, token } = useAuth();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [viewMode, setViewMode] = useState("list"); // "list" or "calendar"
  const [calendarMonth, setCalendarMonth] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });

  // Create form state
  const [sourceType, setSourceType] = useState("text");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const res = await fetchContentItems(user.tenantId, token, {
        status: statusFilter || undefined,
      });
      setItems(res.items || []);
      setTotal(res.total || 0);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    if (!title.trim() || !content.trim()) {
      setError("Title and content are required.");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      await createContentItem(user.tenantId, token, {
        title: title.trim(),
        source_type: sourceType,
        source_content: content.trim(),
      });
      setShowCreate(false);
      setTitle("");
      setContent("");
      setSourceType("text");
      load();
    } catch (e) {
      setError(e.message || "Failed to create content");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this content item?")) return;
    try {
      await deleteContentItem(user.tenantId, token, id);
      load();
      if (selectedItem?.id === id) setSelectedItem(null);
    } catch {
      // ignore
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 500000) {
      setError("File too large (max 500KB).");
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      setContent(ev.target.result);
      if (!title.trim()) setTitle(file.name.replace(/\.[^.]+$/, ""));
    };
    reader.readAsText(file);
  };

  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState(null);
  const [copiedPlatform, setCopiedPlatform] = useState(null);
  const [editingPlatform, setEditingPlatform] = useState(null);
  const [editText, setEditText] = useState("");
  const [saving, setSaving] = useState(false);

  const handleRepurpose = async (contentId) => {
    setGenerating(true);
    setGenerateError(null);
    try {
      const res = await repurposeContent(user.tenantId, token, contentId);
      // Refresh the selected item with generated versions
      const updated = await fetchContentItem(user.tenantId, token, contentId);
      setSelectedItem(updated);
      load();
    } catch (e) {
      setGenerateError(e.message || "AI generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = async (platform, text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedPlatform(platform);
      setTimeout(() => setCopiedPlatform(null), 2000);
    } catch {
      // Fallback
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopiedPlatform(platform);
      setTimeout(() => setCopiedPlatform(null), 2000);
    }
  };

  const handleEditSave = async (platform) => {
    if (!selectedItem) return;
    setSaving(true);
    try {
      const updatedVersions = { ...selectedItem.platform_versions, [platform]: editText };
      await updateContentItem(user.tenantId, token, selectedItem.id, {
        platform_versions: updatedVersions,
      });
      setSelectedItem({ ...selectedItem, platform_versions: updatedVersions });
      setEditingPlatform(null);
      setEditText("");
    } catch {
      // keep editing open on failure
    } finally {
      setSaving(false);
    }
  };

  const [searchQuery, setSearchQuery] = useState("");

  const handleSchedule = async (contentId, date) => {
    try {
      await updateContentItem(user.tenantId, token, contentId, {
        scheduled_for: date,
        status: date ? "scheduled" : "generated",
      });
      const updated = await fetchContentItem(user.tenantId, token, contentId);
      setSelectedItem(updated);
      load();
    } catch {
      // keep state
    }
  };

  const currentSourceType = SOURCE_TYPES.find((t) => t.key === sourceType) || SOURCE_TYPES[0];

  const PLATFORM_LABELS = {
    linkedin: "LinkedIn",
    facebook: "Facebook",
    instagram: "Instagram",
    gbp: "Google Business Profile",
    email: "Email Newsletter",
    twitter: "Twitter/X",
  };

  // --- Filtering and stat cards ---
  const filteredItems = searchQuery.trim()
    ? items.filter((i) => i.title.toLowerCase().includes(searchQuery.toLowerCase()))
    : items;
  const draftCount = items.filter((i) => i.status === "draft").length;
  const generatedCount = items.filter((i) => i.status === "generated").length;
  const publishedCount = items.filter((i) => i.status === "published").length;
  const scheduledCount = items.filter((i) => i.status === "scheduled").length;

  // --- Calendar helpers ---
  const getDaysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();
  const getFirstDayOfWeek = (year, month) => new Date(year, month, 1).getDay();
  const calendarDays = getDaysInMonth(calendarMonth.year, calendarMonth.month);
  const calendarStartDay = getFirstDayOfWeek(calendarMonth.year, calendarMonth.month);
  const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  const getItemsForDate = (day) => {
    const dateStr = `${calendarMonth.year}-${String(calendarMonth.month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    return items.filter((i) => i.scheduled_for === dateStr);
  };

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
            Content Studio
          </h1>
          <p style={{ color: "var(--text-secondary)", margin: "4px 0 0", fontSize: "0.9rem" }}>
            Create source content and repurpose it for every platform
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          style={{
            background: "var(--accent)",
            color: "#fff",
            border: "none",
            padding: "10px 20px",
            borderRadius: "8px",
            fontWeight: 600,
            cursor: "pointer",
            fontSize: "0.9rem",
          }}
        >
          + New Content
        </button>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 16, marginBottom: 24 }}>
        {[
          { label: "Total Items", value: total, color: "var(--accent)" },
          { label: "Drafts", value: draftCount, color: "var(--text-secondary)" },
          { label: "Generated", value: generatedCount, color: "var(--purple)" },
          { label: "Scheduled", value: scheduledCount, color: "var(--warning, #f59e0b)" },
          { label: "Published", value: publishedCount, color: "var(--green)" },
        ].map((s) => (
          <div key={s.label} style={{
            background: "var(--card-bg)",
            border: "1px solid var(--border-color)",
            borderRadius: 12,
            padding: "16px 20px",
          }}>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20, alignItems: "center" }}>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{
            padding: "8px 14px",
            borderRadius: 8,
            border: "1px solid var(--border-color)",
            background: "var(--card-bg)",
            color: "var(--text-primary)",
            fontSize: "0.85rem",
          }}
        >
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="generated">Generated</option>
          <option value="scheduled">Scheduled</option>
          <option value="published">Published</option>
        </select>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search content..."
          style={{
            padding: "8px 14px",
            borderRadius: 8,
            border: "1px solid var(--border-color)",
            background: "var(--card-bg)",
            color: "var(--text-primary)",
            fontSize: "0.85rem",
            flex: 1,
            maxWidth: 300,
          }}
        />
        <div style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
          {["list", "calendar"].map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              style={{
                padding: "7px 14px",
                borderRadius: 8,
                border: viewMode === mode ? "2px solid var(--accent)" : "1px solid var(--border-color)",
                background: viewMode === mode ? "var(--accent-dim)" : "var(--card-bg)",
                color: viewMode === mode ? "var(--accent)" : "var(--text-secondary)",
                cursor: "pointer",
                fontWeight: viewMode === mode ? 600 : 400,
                fontSize: "0.8rem",
                textTransform: "capitalize",
              }}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* Calendar view */}
      {viewMode === "calendar" && !loading && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <button
              onClick={() => setCalendarMonth((m) => {
                const d = new Date(m.year, m.month - 1, 1);
                return { year: d.getFullYear(), month: d.getMonth() };
              })}
              style={{ background: "var(--card-bg)", border: "1px solid var(--border-color)", borderRadius: 8, padding: "6px 14px", color: "var(--text-secondary)", cursor: "pointer" }}
            >
              &larr;
            </button>
            <h3 style={{ margin: 0, color: "var(--text-primary)", fontSize: "1rem" }}>
              {monthNames[calendarMonth.month]} {calendarMonth.year}
            </h3>
            <button
              onClick={() => setCalendarMonth((m) => {
                const d = new Date(m.year, m.month + 1, 1);
                return { year: d.getFullYear(), month: d.getMonth() };
              })}
              style={{ background: "var(--card-bg)", border: "1px solid var(--border-color)", borderRadius: 8, padding: "6px 14px", color: "var(--text-secondary)", cursor: "pointer" }}
            >
              &rarr;
            </button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 2 }}>
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
              <div key={d} style={{ textAlign: "center", fontSize: "0.7rem", color: "var(--text-muted)", padding: "6px 0", fontWeight: 600 }}>{d}</div>
            ))}
            {Array.from({ length: calendarStartDay }, (_, i) => (
              <div key={`empty-${i}`} style={{ minHeight: 70 }} />
            ))}
            {Array.from({ length: calendarDays }, (_, i) => {
              const day = i + 1;
              const dayItems = getItemsForDate(day);
              const isToday = (() => {
                const now = new Date();
                return now.getFullYear() === calendarMonth.year && now.getMonth() === calendarMonth.month && now.getDate() === day;
              })();
              return (
                <div
                  key={day}
                  style={{
                    minHeight: 70,
                    background: isToday ? "var(--accent-dim)" : "var(--card-bg)",
                    border: isToday ? "2px solid var(--accent)" : "1px solid var(--border-color)",
                    borderRadius: 6,
                    padding: "4px 6px",
                    overflow: "hidden",
                  }}
                >
                  <div style={{ fontSize: "0.7rem", fontWeight: 600, color: isToday ? "var(--accent)" : "var(--text-secondary)", marginBottom: 2 }}>
                    {day}
                  </div>
                  {dayItems.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => setSelectedItem(item)}
                      style={{
                        fontSize: "0.65rem",
                        padding: "2px 4px",
                        borderRadius: 3,
                        background: "var(--accent)",
                        color: "#fff",
                        marginBottom: 2,
                        cursor: "pointer",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        fontWeight: 500,
                      }}
                      title={item.title}
                    >
                      {item.title}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Content list */}
      {viewMode === "list" && loading ? (
        <div style={{ textAlign: "center", padding: 60, color: "var(--text-secondary)" }}>Loading...</div>
      ) : viewMode === "list" && filteredItems.length === 0 && items.length === 0 ? (
        <div style={{
          textAlign: "center",
          padding: "60px 20px",
          background: "var(--card-bg)",
          border: "1px solid var(--border-color)",
          borderRadius: 12,
        }}>
          <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>&#9997;</div>
          <h3 style={{ margin: "0 0 8px", color: "var(--text-primary)" }}>No content yet</h3>
          <p style={{ color: "var(--text-secondary)", margin: "0 0 16px", maxWidth: 400, marginInline: "auto" }}>
            Add your first piece of content — paste a blog post, describe a recent project, or upload a text file.
            The AI will repurpose it for every platform.
          </p>
          <button
            onClick={() => setShowCreate(true)}
            style={{
              background: "var(--accent)",
              color: "#fff",
              border: "none",
              padding: "10px 20px",
              borderRadius: 8,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            + Add Content
          </button>
        </div>
      ) : viewMode === "list" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {filteredItems.map((item) => (
            <div
              key={item.id}
              onClick={() => setSelectedItem(item)}
              style={{
                background: selectedItem?.id === item.id ? "var(--hover-overlay)" : "var(--card-bg)",
                border: "1px solid var(--border-color)",
                borderRadius: 10,
                padding: "14px 20px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                transition: "background 0.15s",
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                  {item.title}
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                  {item.source_type === "text" ? "Blog / Article" :
                   item.source_type === "description" ? "Job Description" : "Uploaded File"}
                  {" \u00B7 "}
                  {timeAgo(item.created_at)}
                  {item.source_content && (
                    <span> &middot; {item.source_content.length.toLocaleString()} chars</span>
                  )}
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <StatusBadge status={item.status} />
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(item.id); }}
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
      ) : null}

      {/* Detail panel */}
      {selectedItem && (
        <div style={{
          marginTop: 24,
          background: "var(--card-bg)",
          border: "1px solid var(--border-color)",
          borderRadius: 12,
          padding: "24px",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
            <div>
              <h2 style={{ margin: 0, fontSize: "1.2rem", color: "var(--text-primary)" }}>{selectedItem.title}</h2>
              <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: 4 }}>
                Created {new Date(selectedItem.created_at).toLocaleString()}
                {" \u00B7 "}
                <StatusBadge status={selectedItem.status} />
              </div>
            </div>
            <button
              onClick={() => setSelectedItem(null)}
              style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "1.2rem" }}
            >
              &#x2715;
            </button>
          </div>
          <div style={{
            background: "var(--bg-primary)",
            border: "1px solid var(--border-color)",
            borderRadius: 8,
            padding: 16,
            maxHeight: 300,
            overflowY: "auto",
            whiteSpace: "pre-wrap",
            fontSize: "0.9rem",
            color: "var(--text-primary)",
            lineHeight: 1.6,
          }}>
            {selectedItem.source_content}
          </div>
          {selectedItem.platform_versions && Object.keys(selectedItem.platform_versions).length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h3 style={{ fontSize: "1rem", color: "var(--text-primary)", margin: "0 0 12px" }}>
                Generated Versions
              </h3>
              {Object.entries(selectedItem.platform_versions).map(([platform, text]) => (
                <div key={platform} style={{
                  marginBottom: 12,
                  background: "var(--bg-primary)",
                  border: editingPlatform === platform ? "2px solid var(--accent)" : "1px solid var(--border-color)",
                  borderRadius: 8,
                  padding: 12,
                }}>
                  <div style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 6,
                  }}>
                    <span style={{
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      textTransform: "uppercase",
                      color: "var(--accent)",
                    }}>
                      {PLATFORM_LABELS[platform] || platform}
                    </span>
                    <div style={{ display: "flex", gap: 6 }}>
                      {editingPlatform === platform ? (
                        <>
                          <button
                            onClick={() => handleEditSave(platform)}
                            disabled={saving}
                            style={{
                              background: "var(--green)",
                              border: "none",
                              color: "#fff",
                              padding: "3px 10px",
                              borderRadius: 6,
                              fontSize: "0.7rem",
                              cursor: saving ? "default" : "pointer",
                              fontWeight: 500,
                            }}
                          >
                            {saving ? "Saving..." : "Save"}
                          </button>
                          <button
                            onClick={() => { setEditingPlatform(null); setEditText(""); }}
                            style={{
                              background: "var(--hover-overlay)",
                              border: "1px solid var(--border-color)",
                              color: "var(--text-secondary)",
                              padding: "3px 10px",
                              borderRadius: 6,
                              fontSize: "0.7rem",
                              cursor: "pointer",
                              fontWeight: 500,
                            }}
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => { setEditingPlatform(platform); setEditText(text); }}
                            style={{
                              background: "var(--hover-overlay)",
                              border: "1px solid var(--border-color)",
                              color: "var(--text-secondary)",
                              padding: "3px 10px",
                              borderRadius: 6,
                              fontSize: "0.7rem",
                              cursor: "pointer",
                              fontWeight: 500,
                            }}
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleCopy(platform, text)}
                            style={{
                              background: copiedPlatform === platform ? "var(--green)" : "var(--hover-overlay)",
                              border: "1px solid var(--border-color)",
                              color: copiedPlatform === platform ? "#fff" : "var(--text-secondary)",
                              padding: "3px 10px",
                              borderRadius: 6,
                              fontSize: "0.7rem",
                              cursor: "pointer",
                              fontWeight: 500,
                              transition: "all 0.15s",
                            }}
                          >
                            {copiedPlatform === platform ? "Copied!" : "Copy"}
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                  {editingPlatform === platform ? (
                    <textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      rows={8}
                      style={{
                        width: "100%",
                        padding: "10px 12px",
                        borderRadius: 6,
                        border: "1px solid var(--border-color)",
                        background: "var(--card-bg)",
                        color: "var(--text-primary)",
                        fontSize: "0.85rem",
                        resize: "vertical",
                        fontFamily: "inherit",
                        lineHeight: 1.6,
                        boxSizing: "border-box",
                      }}
                    />
                  ) : (
                    <div style={{ fontSize: "0.85rem", color: "var(--text-primary)", whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
                      {text}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          {/* Generate / Regenerate button */}
          <div style={{ marginTop: 16, display: "flex", gap: 12, alignItems: "center" }}>
            <button
              onClick={() => handleRepurpose(selectedItem.id)}
              disabled={generating}
              style={{
                background: generating ? "var(--text-muted)" : "var(--accent)",
                color: "#fff",
                border: "none",
                padding: "10px 20px",
                borderRadius: 8,
                fontWeight: 600,
                cursor: generating ? "default" : "pointer",
                fontSize: "0.85rem",
              }}
            >
              {generating
                ? "Generating..."
                : selectedItem.platform_versions && Object.keys(selectedItem.platform_versions).length > 0
                  ? "Regenerate All Versions"
                  : "Generate AI Versions"}
            </button>
            {generateError && (
              <span style={{ color: "#f87171", fontSize: "0.85rem" }}>{generateError}</span>
            )}
          </div>
          {/* Schedule date picker */}
          {selectedItem.platform_versions && Object.keys(selectedItem.platform_versions).length > 0 && (
            <div style={{ marginTop: 12, display: "flex", gap: 12, alignItems: "center" }}>
              <label style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>Schedule for:</label>
              <input
                type="date"
                value={selectedItem.scheduled_for || ""}
                onChange={(e) => handleSchedule(selectedItem.id, e.target.value || null)}
                style={{
                  padding: "7px 12px",
                  borderRadius: 8,
                  border: "1px solid var(--border-color)",
                  background: "var(--card-bg)",
                  color: "var(--text-primary)",
                  fontSize: "0.85rem",
                }}
              />
              {selectedItem.scheduled_for && (
                <button
                  onClick={() => handleSchedule(selectedItem.id, null)}
                  style={{
                    background: "var(--hover-overlay)",
                    border: "1px solid var(--border-color)",
                    color: "var(--text-secondary)",
                    padding: "6px 12px",
                    borderRadius: 8,
                    fontSize: "0.8rem",
                    cursor: "pointer",
                  }}
                >
                  Unschedule
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.6)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000,
        }}
          onClick={() => setShowCreate(false)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "var(--card-bg)",
              borderRadius: 16,
              padding: "28px 32px",
              width: "90%",
              maxWidth: 700,
              maxHeight: "90vh",
              overflowY: "auto",
              border: "1px solid var(--border-color)",
            }}
          >
            <h2 style={{ margin: "0 0 20px", color: "var(--text-primary)", fontSize: "1.2rem" }}>
              Add Source Content
            </h2>

            {/* Source type selector */}
            <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
              {SOURCE_TYPES.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setSourceType(t.key)}
                  style={{
                    padding: "8px 16px",
                    borderRadius: 8,
                    border: sourceType === t.key ? "2px solid var(--accent)" : "1px solid var(--border-color)",
                    background: sourceType === t.key ? "var(--accent-dim)" : "var(--bg-primary)",
                    color: sourceType === t.key ? "var(--accent)" : "var(--text-secondary)",
                    cursor: "pointer",
                    fontWeight: sourceType === t.key ? 600 : 400,
                    fontSize: "0.85rem",
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Title */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 6 }}>
                Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Give this content a name..."
                maxLength={200}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--border-color)",
                  background: "var(--bg-primary)",
                  color: "var(--text-primary)",
                  fontSize: "0.9rem",
                  boxSizing: "border-box",
                }}
              />
            </div>

            {/* Content input */}
            {sourceType === "file" ? (
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: "block", fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 6 }}>
                  Upload a text file (.txt, .md)
                </label>
                <input
                  type="file"
                  accept=".txt,.md,.text"
                  onChange={handleFileUpload}
                  style={{
                    padding: "10px",
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border-color)",
                    borderRadius: 8,
                    color: "var(--text-primary)",
                    width: "100%",
                    boxSizing: "border-box",
                  }}
                />
                {content && (
                  <div style={{
                    marginTop: 12,
                    padding: 12,
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border-color)",
                    borderRadius: 8,
                    maxHeight: 150,
                    overflowY: "auto",
                    fontSize: "0.8rem",
                    color: "var(--text-secondary)",
                    whiteSpace: "pre-wrap",
                  }}>
                    {content.slice(0, 500)}{content.length > 500 ? "..." : ""}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: "block", fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 6 }}>
                  Content
                </label>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder={currentSourceType.placeholder}
                  rows={10}
                  maxLength={50000}
                  style={{
                    width: "100%",
                    padding: "12px 14px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-primary)",
                    color: "var(--text-primary)",
                    fontSize: "0.9rem",
                    resize: "vertical",
                    fontFamily: "inherit",
                    lineHeight: 1.6,
                    boxSizing: "border-box",
                  }}
                />
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4, textAlign: "right" }}>
                  {content.length.toLocaleString()} / 50,000
                </div>
              </div>
            )}

            {error && (
              <div style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 12 }}>{error}</div>
            )}

            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button
                onClick={() => { setShowCreate(false); setError(null); }}
                style={{
                  padding: "10px 20px",
                  borderRadius: 8,
                  border: "1px solid var(--border-color)",
                  background: "var(--bg-primary)",
                  color: "var(--text-secondary)",
                  cursor: "pointer",
                  fontWeight: 500,
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={creating || !title.trim() || !content.trim()}
                style={{
                  padding: "10px 20px",
                  borderRadius: 8,
                  border: "none",
                  background: creating ? "var(--text-muted)" : "var(--accent)",
                  color: "#fff",
                  cursor: creating ? "default" : "pointer",
                  fontWeight: 600,
                }}
              >
                {creating ? "Saving..." : "Save Content"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
