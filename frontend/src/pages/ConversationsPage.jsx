import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchConversations, fetchConversationMessages, updateConversationTags } from "../utils/api";
import SkeletonLoader from "../components/SkeletonLoader";

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export default function ConversationsPage() {
  const { user, token } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [search, setSearch] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [tagInput, setTagInput] = useState("");

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const res = await fetchConversations(user.tenantId, token);
      setConversations(res.conversations || []);
    } catch (err) {
      console.error("Failed to load conversations", err);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => { load(); }, [load]);

  const handleSelect = async (conv) => {
    setSelected(conv.session_id);
    setLoadingMessages(true);
    try {
      const res = await fetchConversationMessages(user.tenantId, conv.session_id, token);
      setMessages(res.messages || []);
    } catch (err) {
      console.error("Failed to load messages", err);
    } finally {
      setLoadingMessages(false);
    }
  };

  const exportConversation = () => {
    if (!messages.length) return;
    const conv = conversations.find((c) => c.session_id === selected);
    const name = conv?.lead_name || "Visitor";
    const lines = [
      `Conversation with ${name}`,
      `Session: ${selected}`,
      `Messages: ${messages.length}`,
      "",
      ...messages.map((m) => {
        const role = m.role === "user" ? "Visitor" : "AI";
        const time = m.created_at ? new Date(m.created_at).toLocaleString() : "";
        return `[${time}] ${role}:\n${m.content}\n`;
      }),
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `conversation-${name.replace(/\s+/g, "-")}-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const addTag = async (sessionId) => {
    const tag = tagInput.trim();
    if (!tag) return;
    const conv = conversations.find((c) => c.session_id === sessionId);
    if (!conv) return;
    const newTags = [...new Set([...(conv.tags || []), tag])];
    try {
      await updateConversationTags(user.tenantId, sessionId, token, newTags);
      setConversations((prev) =>
        prev.map((c) => (c.session_id === sessionId ? { ...c, tags: newTags } : c))
      );
      setTagInput("");
    } catch (err) {
      console.error("Failed to add tag", err);
    }
  };

  const removeTag = async (sessionId, tagToRemove) => {
    const conv = conversations.find((c) => c.session_id === sessionId);
    if (!conv) return;
    const newTags = (conv.tags || []).filter((t) => t !== tagToRemove);
    try {
      await updateConversationTags(user.tenantId, sessionId, token, newTags);
      setConversations((prev) =>
        prev.map((c) => (c.session_id === sessionId ? { ...c, tags: newTags } : c))
      );
    } catch (err) {
      console.error("Failed to remove tag", err);
    }
  };

  // Collect all unique tags for the filter dropdown
  const allTags = [...new Set(conversations.flatMap((c) => c.tags || []))].sort();

  if (loading) return <SkeletonLoader />;

  const filtered = conversations.filter((c) => {
    if (search) {
      const q = search.toLowerCase();
      if (!(c.lead_name || "").toLowerCase().includes(q) && !(c.preview || "").toLowerCase().includes(q)) return false;
    }
    if (tagFilter && !(c.tags || []).includes(tagFilter)) return false;
    return true;
  });

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Conversations</h1>
        <p>{conversations.length} chat session{conversations.length !== 1 ? "s" : ""}</p>
      </div>

      {conversations.length === 0 ? (
        <div className="empty-card">
          <p>No conversations yet. Conversations from your widget will appear here.</p>
        </div>
      ) : (
        <div className="conversations-layout">
          <div className="conv-sidebar">
            <input
              className="conv-search"
              placeholder="Search conversations..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {allTags.length > 0 && (
              <select
                value={tagFilter}
                onChange={(e) => setTagFilter(e.target.value)}
                style={{ width: "100%", padding: "6px 8px", marginBottom: 8, borderRadius: 6, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)", fontSize: "0.8rem" }}
              >
                <option value="">All tags</option>
                {allTags.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            )}
            <div className="conv-list">
              {filtered.map((c) => (
                <div
                  key={c.session_id}
                  className={`conv-item${selected === c.session_id ? " active" : ""}`}
                  onClick={() => handleSelect(c)}
                >
                  <div className="conv-item-header">
                    <span className="conv-item-name">{c.lead_name || "Visitor"}</span>
                    <span className="conv-item-time">{timeAgo(c.last_message_at)}</span>
                  </div>
                  <div className="conv-item-preview">{c.preview || c.last_message || "No messages"}</div>
                  <div className="conv-item-count">{c.message_count} message{c.message_count !== 1 ? "s" : ""}</div>
                  {(c.tags || []).length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 4 }}>
                      {c.tags.map((tag) => (
                        <span key={tag} style={{
                          display: "inline-block",
                          padding: "1px 7px",
                          borderRadius: 10,
                          fontSize: "0.68rem",
                          background: "var(--accent-dim, rgba(0,191,255,0.15))",
                          color: "var(--accent, #00BFFF)",
                        }}>{tag}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {filtered.length === 0 && (
                <div style={{ padding: "1rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                  No conversations match your search.
                </div>
              )}
            </div>
          </div>

          <div className="conv-messages">
            {!selected ? (
              <div className="conv-empty-state">Select a conversation to view messages</div>
            ) : loadingMessages ? (
              <div className="conv-empty-state">Loading...</div>
            ) : (
              <div className="conv-message-list">
                {/* Tag management + export toolbar */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0 0 0.5rem", gap: 8, flexWrap: "wrap" }}>
                  <div style={{ display: "flex", gap: 4, alignItems: "center", flexWrap: "wrap", flex: 1 }}>
                    {(conversations.find((c) => c.session_id === selected)?.tags || []).map((tag) => (
                      <span key={tag} style={{
                        display: "inline-flex", alignItems: "center", gap: 4,
                        padding: "2px 8px", borderRadius: 10, fontSize: "0.75rem",
                        background: "var(--accent-dim, rgba(0,191,255,0.15))",
                        color: "var(--accent, #00BFFF)",
                      }}>
                        {tag}
                        <span onClick={() => removeTag(selected, tag)} style={{ cursor: "pointer", fontWeight: 700 }}>&times;</span>
                      </span>
                    ))}
                    <input
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") addTag(selected); }}
                      placeholder="Add tag..."
                      style={{ width: 80, padding: "2px 6px", fontSize: "0.75rem", borderRadius: 6, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)" }}
                    />
                  </div>
                  {messages.length > 0 && (
                    <button className="btn-sm" onClick={exportConversation}>Export Transcript</button>
                  )}
                </div>
                {messages.map((m) => (
                  <div key={m.id} className={`conv-msg ${m.role}`}>
                    <div className="conv-msg-role">{m.role === "user" ? "Visitor" : "AI"}</div>
                    <div className="conv-msg-content">{m.content}</div>
                    <div className="conv-msg-time">{timeAgo(m.created_at)}</div>
                  </div>
                ))}
                {messages.length === 0 && (
                  <div className="conv-empty-state">No messages in this conversation.</div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
