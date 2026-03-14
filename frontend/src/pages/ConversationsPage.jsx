import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import {
  fetchConversations,
  fetchConversationMessages,
  updateConversationTags,
  fetchTagDefinitions,
  fetchTeamMembers,
  assignConversation,
  fetchConversationNotes,
  createConversationNote,
  deleteConversationNote,
} from "../utils/api";
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

function formatNoteTime(dateStr) {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
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
  const [tagDefs, setTagDefs] = useState([]);

  // Shared inbox state
  const [inboxFilter, setInboxFilter] = useState("all"); // "all" | "mine"
  const [teamMembers, setTeamMembers] = useState([]);
  const [teamMemberMap, setTeamMemberMap] = useState({}); // id -> { name, email }
  const [assigning, setAssigning] = useState(false);

  // Internal notes state
  const [showNotes, setShowNotes] = useState(false);
  const [notes, setNotes] = useState([]);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [noteInput, setNoteInput] = useState("");
  const [addingNote, setAddingNote] = useState(false);

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const [convRes, tagRes, teamRes] = await Promise.all([
        fetchConversations(user.tenantId, token),
        fetchTagDefinitions(user.tenantId, token).catch(() => ({ tags: [] })),
        fetchTeamMembers(user.tenantId, token).catch(() => ({ members: [] })),
      ]);
      setConversations(convRes.conversations || []);
      setTagDefs(tagRes.tags || []);

      const members = teamRes.members || teamRes || [];
      setTeamMembers(Array.isArray(members) ? members : []);

      // Build lookup map: team_member_id -> { name, email }
      const map = {};
      (Array.isArray(members) ? members : []).forEach((m) => {
        const id = m.id || m.team_member_id;
        if (id) {
          map[id] = { name: m.name || m.email, email: m.email };
        }
      });
      setTeamMemberMap(map);
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
    setShowNotes(false);
    setNotes([]);
    try {
      const res = await fetchConversationMessages(user.tenantId, conv.session_id, token);
      setMessages(res.messages || []);
    } catch (err) {
      console.error("Failed to load messages", err);
    } finally {
      setLoadingMessages(false);
    }
  };

  // Load notes for the selected conversation
  const loadNotes = async (sessionId) => {
    if (!sessionId) return;
    setLoadingNotes(true);
    try {
      const res = await fetchConversationNotes(user.tenantId, token, sessionId);
      setNotes(res.notes || []);
    } catch (err) {
      console.error("Failed to load notes", err);
      setNotes([]);
    } finally {
      setLoadingNotes(false);
    }
  };

  const toggleNotes = () => {
    const next = !showNotes;
    setShowNotes(next);
    if (next && selected) {
      loadNotes(selected);
    }
  };

  const handleAddNote = async () => {
    const content = noteInput.trim();
    if (!content || !selected) return;
    setAddingNote(true);
    try {
      const res = await createConversationNote(user.tenantId, token, selected, content);
      // Append the new note; the API may return the note object or we re-fetch
      if (res && res.id) {
        setNotes((prev) => [...prev, res]);
      } else {
        // Re-fetch to be safe
        await loadNotes(selected);
      }
      setNoteInput("");
    } catch (err) {
      console.error("Failed to add note", err);
    } finally {
      setAddingNote(false);
    }
  };

  const handleDeleteNote = async (noteId) => {
    try {
      await deleteConversationNote(user.tenantId, token, noteId);
      setNotes((prev) => prev.filter((n) => n.id !== noteId));
    } catch (err) {
      console.error("Failed to delete note", err);
    }
  };

  // Assign conversation to a team member
  const handleAssign = async (sessionId, assignedTo) => {
    setAssigning(true);
    try {
      await assignConversation(user.tenantId, token, sessionId, assignedTo || null);
      setConversations((prev) =>
        prev.map((c) =>
          c.session_id === sessionId ? { ...c, assigned_to: assignedTo || null } : c
        )
      );
    } catch (err) {
      console.error("Failed to assign conversation", err);
    } finally {
      setAssigning(false);
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

  // Build a map of tag_name -> tag_color from tag definitions
  const tagColorMap = {};
  tagDefs.forEach((td) => {
    if (td.tag_name && td.tag_color) tagColorMap[td.tag_name] = td.tag_color;
  });

  function getTagColor(tag) {
    return tagColorMap[tag] || null;
  }

  function tagPillStyle(tag) {
    const color = getTagColor(tag);
    if (color) {
      return {
        display: "inline-block",
        padding: "1px 7px",
        borderRadius: 10,
        fontSize: "0.68rem",
        background: color + "26", // ~15% opacity hex suffix
        color: color,
      };
    }
    return {
      display: "inline-block",
      padding: "1px 7px",
      borderRadius: 10,
      fontSize: "0.68rem",
      background: "var(--accent-dim, rgba(0,191,255,0.15))",
      color: "var(--accent, #00BFFF)",
    };
  }

  // Helper: get assignee display name
  function getAssigneeName(assignedTo) {
    if (!assignedTo) return null;
    if (teamMemberMap[assignedTo]) return teamMemberMap[assignedTo].name;
    return "Team Member";
  }

  // Collect all unique tags with counts for the filter dropdown
  const tagCounts = {};
  conversations.forEach((c) => {
    (c.tags || []).forEach((t) => {
      tagCounts[t] = (tagCounts[t] || 0) + 1;
    });
  });
  const allTags = Object.keys(tagCounts).sort();

  if (loading) return <SkeletonLoader />;

  // Determine current user's userId for "My Conversations" filter
  const currentUserId = user?.userId || null;

  const filtered = conversations.filter((c) => {
    // Inbox filter: "mine" shows only conversations assigned to current user
    if (inboxFilter === "mine" && currentUserId) {
      if (c.assigned_to !== currentUserId) return false;
    }
    if (search) {
      const q = search.toLowerCase();
      if (!(c.lead_name || "").toLowerCase().includes(q) && !(c.preview || "").toLowerCase().includes(q)) return false;
    }
    if (tagFilter && !(c.tags || []).includes(tagFilter)) return false;
    return true;
  });

  // Count for the filter buttons
  const myCount = currentUserId
    ? conversations.filter((c) => c.assigned_to === currentUserId).length
    : 0;

  const selectedConv = conversations.find((c) => c.session_id === selected);

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
            {/* Inbox filter toggle */}
            <div style={{
              display: "flex",
              gap: 0,
              marginBottom: 8,
              borderRadius: 8,
              overflow: "hidden",
              border: "1px solid var(--border-color)",
            }}>
              <button
                onClick={() => setInboxFilter("all")}
                style={{
                  flex: 1,
                  padding: "7px 10px",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  border: "none",
                  cursor: "pointer",
                  background: inboxFilter === "all"
                    ? "var(--accent, #00BFFF)"
                    : "var(--bg-secondary)",
                  color: inboxFilter === "all"
                    ? "#fff"
                    : "var(--text-secondary)",
                  transition: "background 0.15s, color 0.15s",
                }}
              >
                All ({conversations.length})
              </button>
              <button
                onClick={() => setInboxFilter("mine")}
                style={{
                  flex: 1,
                  padding: "7px 10px",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  border: "none",
                  borderLeft: "1px solid var(--border-color)",
                  cursor: "pointer",
                  background: inboxFilter === "mine"
                    ? "var(--accent, #00BFFF)"
                    : "var(--bg-secondary)",
                  color: inboxFilter === "mine"
                    ? "#fff"
                    : "var(--text-secondary)",
                  transition: "background 0.15s, color 0.15s",
                }}
              >
                Mine ({myCount})
              </button>
            </div>

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
                <option value="">All tags ({conversations.length})</option>
                {allTags.map((t) => (
                  <option key={t} value={t}>{t} ({tagCounts[t]})</option>
                ))}
              </select>
            )}
            <div className="conv-list">
              {filtered.map((c) => {
                const assigneeName = getAssigneeName(c.assigned_to);
                return (
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
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 2 }}>
                      <span className="conv-item-count">{c.message_count} message{c.message_count !== 1 ? "s" : ""}</span>
                      <span style={{
                        fontSize: "0.7rem",
                        color: assigneeName ? "var(--accent, #00BFFF)" : "var(--text-muted)",
                        fontStyle: assigneeName ? "normal" : "italic",
                        maxWidth: 100,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}>
                        {assigneeName || "Unassigned"}
                      </span>
                    </div>
                    {(c.tags || []).length > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 4 }}>
                        {c.tags.map((tag) => (
                          <span key={tag} style={tagPillStyle(tag)}>{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
              {filtered.length === 0 && (
                <div style={{ padding: "1rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                  {inboxFilter === "mine" && myCount === 0
                    ? "No conversations assigned to you yet. Assign conversations from the conversation view, or switch to \"All\" to see all conversations."
                    : tagFilter
                    ? `No conversations tagged "${tagFilter}". Try selecting "All tags" to clear the filter.`
                    : "No conversations match your search."}
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
                {/* Toolbar: Assign dropdown + Tag management + Export + Notes toggle */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0 0 0.5rem", gap: 8, flexWrap: "wrap" }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", flex: 1 }}>
                    {/* Assign to dropdown */}
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", whiteSpace: "nowrap" }}>Assign:</label>
                      <select
                        value={selectedConv?.assigned_to || ""}
                        onChange={(e) => handleAssign(selected, e.target.value)}
                        disabled={assigning}
                        style={{
                          padding: "4px 8px",
                          fontSize: "0.75rem",
                          borderRadius: 6,
                          border: "1px solid var(--border-color)",
                          background: "var(--bg-secondary)",
                          color: "var(--text-primary)",
                          minWidth: 110,
                          cursor: assigning ? "wait" : "pointer",
                          opacity: assigning ? 0.6 : 1,
                        }}
                      >
                        <option value="">Unassigned</option>
                        {teamMembers.map((m) => {
                          const id = m.id || m.team_member_id;
                          return (
                            <option key={id} value={id}>
                              {m.name || m.email}
                            </option>
                          );
                        })}
                      </select>
                    </div>

                    {/* Divider */}
                    <span style={{ width: 1, height: 16, background: "var(--border-color)", flexShrink: 0 }} />

                    {/* Tags */}
                    {(selectedConv?.tags || []).map((tag) => {
                      const color = getTagColor(tag);
                      const pillBg = color ? color + "26" : "var(--accent-dim, rgba(0,191,255,0.15))";
                      const pillColor = color || "var(--accent, #00BFFF)";
                      return (
                        <span key={tag} style={{
                          display: "inline-flex", alignItems: "center", gap: 4,
                          padding: "2px 8px", borderRadius: 10, fontSize: "0.75rem",
                          background: pillBg,
                          color: pillColor,
                        }}>
                          {tag}
                          <span onClick={() => removeTag(selected, tag)} style={{ cursor: "pointer", fontWeight: 700 }}>&times;</span>
                        </span>
                      );
                    })}
                    <input
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") addTag(selected); }}
                      placeholder="Add tag..."
                      style={{ width: 80, padding: "2px 6px", fontSize: "0.75rem", borderRadius: 6, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)" }}
                    />
                  </div>
                  <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                    <button
                      className="btn-sm"
                      onClick={toggleNotes}
                      style={{
                        background: showNotes ? "rgba(139,92,246,0.15)" : undefined,
                        color: showNotes ? "rgba(167,139,250,1)" : undefined,
                        borderColor: showNotes ? "rgba(139,92,246,0.3)" : undefined,
                      }}
                    >
                      Notes {notes.length > 0 ? `(${notes.length})` : ""}
                    </button>
                    {messages.length > 0 && (
                      <button className="btn-sm" onClick={exportConversation}>Export</button>
                    )}
                  </div>
                </div>

                {/* Chat messages */}
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

                {/* Internal Notes Panel */}
                {showNotes && (
                  <div style={{
                    marginTop: "1rem",
                    padding: "1rem",
                    borderRadius: 10,
                    background: "rgba(139,92,246,0.06)",
                    border: "1px solid rgba(139,92,246,0.2)",
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-primary)" }}>
                          Internal Notes
                        </span>
                        <span style={{
                          fontSize: "0.65rem",
                          padding: "2px 6px",
                          borderRadius: 4,
                          background: "rgba(139,92,246,0.15)",
                          color: "rgba(167,139,250,1)",
                          fontWeight: 600,
                          textTransform: "uppercase",
                          letterSpacing: "0.5px",
                        }}>
                          Internal
                        </span>
                      </div>
                      <button
                        onClick={toggleNotes}
                        style={{
                          background: "none",
                          border: "none",
                          color: "var(--text-muted)",
                          cursor: "pointer",
                          fontSize: "1rem",
                          padding: "0 4px",
                          lineHeight: 1,
                        }}
                        title="Close notes"
                      >
                        &times;
                      </button>
                    </div>

                    {loadingNotes ? (
                      <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", padding: "0.5rem 0" }}>
                        Loading notes...
                      </div>
                    ) : notes.length === 0 ? (
                      <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", padding: "0.5rem 0" }}>
                        No internal notes yet. Use notes to share context with your team about this conversation.
                      </div>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: "0.75rem" }}>
                        {notes.map((note) => (
                          <div key={note.id} style={{
                            padding: "10px 12px",
                            borderRadius: 8,
                            background: "rgba(139,92,246,0.08)",
                            border: "1px solid rgba(139,92,246,0.12)",
                          }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                              <div>
                                <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "rgba(167,139,250,1)" }}>
                                  {note.author_name || note.author_email || "Team Member"}
                                </span>
                                <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginLeft: 8 }}>
                                  {formatNoteTime(note.created_at)}
                                </span>
                              </div>
                              <button
                                onClick={() => handleDeleteNote(note.id)}
                                style={{
                                  background: "none",
                                  border: "none",
                                  color: "var(--text-muted)",
                                  cursor: "pointer",
                                  fontSize: "0.75rem",
                                  padding: "0 2px",
                                  opacity: 0.7,
                                }}
                                title="Delete note"
                              >
                                &times;
                              </button>
                            </div>
                            <div style={{ fontSize: "0.85rem", color: "var(--text-primary)", marginTop: 4, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                              {note.content}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Add note input */}
                    <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
                      <textarea
                        value={noteInput}
                        onChange={(e) => setNoteInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            handleAddNote();
                          }
                        }}
                        placeholder="Add an internal note... (Enter to send, Shift+Enter for new line)"
                        rows={2}
                        style={{
                          flex: 1,
                          padding: "8px 10px",
                          fontSize: "0.85rem",
                          borderRadius: 8,
                          border: "1px solid rgba(139,92,246,0.25)",
                          background: "var(--bg-secondary)",
                          color: "var(--text-primary)",
                          resize: "vertical",
                          minHeight: 40,
                          fontFamily: "inherit",
                        }}
                      />
                      <button
                        className="btn-primary"
                        onClick={handleAddNote}
                        disabled={addingNote || !noteInput.trim()}
                        style={{
                          padding: "8px 14px",
                          fontSize: "0.8rem",
                          whiteSpace: "nowrap",
                          height: "fit-content",
                        }}
                      >
                        {addingNote ? "Adding..." : "Add Note"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
