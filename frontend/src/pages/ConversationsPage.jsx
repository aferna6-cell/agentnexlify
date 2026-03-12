import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchConversations, fetchConversationMessages } from "../utils/api";
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

  if (loading) return <SkeletonLoader />;

  const filtered = search
    ? conversations.filter(
        (c) =>
          (c.lead_name || "").toLowerCase().includes(search.toLowerCase()) ||
          (c.preview || "").toLowerCase().includes(search.toLowerCase())
      )
    : conversations;

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
                {messages.length > 0 && (
                  <div style={{ display: "flex", justifyContent: "flex-end", padding: "0 0 0.5rem" }}>
                    <button className="btn-sm" onClick={exportConversation}>Export Transcript</button>
                  </div>
                )}
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
