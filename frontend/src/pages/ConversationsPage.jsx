import { useState, useEffect, useCallback, useRef } from "react";
import DOMPurify from "dompurify";
import { useAuth } from "../context/AuthContext";
import {
  fetchConversations,
  fetchConversationMessages,
  updateConversationTags,
} from "../utils/api/conversations";
import { fetchTeamMembers } from "../utils/api/team";
import {
  assignConversation,
  fetchConversationNotes,
  createConversationNote,
  deleteConversationNote,
  replyToConversation,
} from "../utils/api/inbox";
import { addClientNote } from "../utils/api/crm";
import { fetchSnippets } from "../utils/api/snippets";
import { fetchTagDefinitions } from "../utils/api/tags";
import { sendSms } from "../utils/api/misc";
import SkeletonLoader from "../components/SkeletonLoader";

const SNIPPET_CATEGORY_COLORS = {
  general: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  pricing: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  hours: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  services: { color: "#8b5cf6", bg: "rgba(139,92,246,0.1)" },
  custom: { color: "#ec4899", bg: "rgba(236,72,153,0.1)" },
};

const CHANNEL_BADGE = {
  widget: { label: "Chat", color: "#3b82f6", bg: "rgba(59,130,246,0.12)" },
  sms: { label: "SMS", color: "#10b981", bg: "rgba(16,185,129,0.12)" },
  facebook: { label: "FB", color: "#1877f2", bg: "rgba(24,119,242,0.12)" },
};

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

function _inlineMd(s) {
  // Escape HTML entities to prevent XSS
  s = s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  // Bold **text**
  s = s.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  // Italic *text* (not inside bold markers)
  s = s.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<em>$1</em>");
  // Links [text](url) - only allow https?:// to prevent XSS
  s = s.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
  );
  return s;
}

function renderMarkdown(text) {
  if (!text) return "";
  const lines = text.split("\n");
  const out = [];
  let inList = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();
    if (
      trimmed.startsWith("- ") ||
      trimmed.startsWith("* ") ||
      /^\d+\.\s/.test(trimmed)
    ) {
      if (!inList) {
        out.push('<ul style="margin:4px 0 4px 16px;padding:0;">');
        inList = true;
      }
      const content = trimmed.replace(/^[-*]\s|^\d+\.\s/, "");
      out.push("<li>" + _inlineMd(content) + "</li>");
    } else {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      if (trimmed === "") {
        if (out.length > 0) out.push("<br>");
      } else {
        out.push(_inlineMd(line));
        const nextTrimmed = (lines[i + 1] || "").trim();
        if (
          nextTrimmed &&
          !nextTrimmed.startsWith("- ") &&
          !nextTrimmed.startsWith("* ") &&
          !/^\d+\.\s/.test(nextTrimmed)
        ) {
          out.push("<br>");
        }
      }
    }
  }
  if (inList) out.push("</ul>");
  while (out.length && out[out.length - 1] === "<br>") out.pop();
  return out.join("");
}

export default function ConversationsPage({ pageData }) {
  const { user, token } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null); // distinct from "no conversations yet"
  const [replyError, setReplyError] = useState(null); // surface failed sends (audit C4)
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [search, setSearch] = useState("");
  const [serverSearch, setServerSearch] = useState(""); // triggers API reload
  const [tagFilter, setTagFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
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

  // Lead quick-note state
  const [showLeadNote, setShowLeadNote] = useState(false);
  const [leadNoteInput, setLeadNoteInput] = useState("");
  const [addingLeadNote, setAddingLeadNote] = useState(false);
  const [leadNoteSuccess, setLeadNoteSuccess] = useState(false);

  // Reply state
  const [replyInput, setReplyInput] = useState("");
  const [sendingReply, setSendingReply] = useState(false);

  // New SMS compose panel state
  const [showSmsCompose, setShowSmsCompose] = useState(false);
  const [smsPhone, setSmsPhone] = useState("");
  const [smsMessage, setSmsMessage] = useState("");
  const [sendingSms, setSendingSms] = useState(false);
  const [smsError, setSmsError] = useState(null);
  const [smsSent, setSmsSent] = useState(false);

  // Snippet picker state
  const [showSnippetPicker, setShowSnippetPicker] = useState(false);
  const [snippetsCache, setSnippetsCache] = useState(null); // null = not loaded yet
  const [snippetsLoading, setSnippetsLoading] = useState(false);
  const [snippetSearch, setSnippetSearch] = useState("");
  const snippetPickerRef = useRef(null);
  const replyTextareaRef = useRef(null);
  const snippetSearchRef = useRef(null);
  const autoSelectedSessionRef = useRef(null);

  // Close snippet picker on outside click
  useEffect(() => {
    if (!showSnippetPicker) return;
    const handleClickOutside = (e) => {
      if (
        snippetPickerRef.current &&
        !snippetPickerRef.current.contains(e.target)
      ) {
        setShowSnippetPicker(false);
        setSnippetSearch("");
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showSnippetPicker]);

  // Focus search input when picker opens
  useEffect(() => {
    if (showSnippetPicker && snippetSearchRef.current) {
      snippetSearchRef.current.focus();
    }
  }, [showSnippetPicker]);

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const [convRes, tagRes, teamRes] = await Promise.all([
        fetchConversations(user.tenantId, token, {
          channel: channelFilter || undefined,
          search: serverSearch.length >= 3 ? serverSearch : undefined,
        }),
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
      setLoadError(null);
    } catch (err) {
      console.error("Failed to load conversations", err);
      // Distinguish a real load failure from a genuinely empty inbox so the
      // owner doesn't read an API outage as "no leads" (audit C4).
      setLoadError(
        err?.message || "Couldn't load conversations. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, channelFilter, serverSearch]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSelect = useCallback(
    async (conv) => {
      setSelected(conv.session_id);
      setLoadingMessages(true);
      setShowNotes(false);
      setNotes([]);
      try {
        const res = await fetchConversationMessages(
          user.tenantId,
          conv.session_id,
          token,
        );
        setMessages(res.messages || []);
      } catch (err) {
        console.error("Failed to load messages", err);
      } finally {
        setLoadingMessages(false);
      }
    },
    [user?.tenantId, token],
  );

  useEffect(() => {
    const targetSessionId = pageData?.sessionId;
    if (!targetSessionId || loading || conversations.length === 0) return;
    if (autoSelectedSessionRef.current === targetSessionId) return;
    const targetConversation = conversations.find(
      (conv) => conv.session_id === targetSessionId,
    );
    if (!targetConversation) return;
    autoSelectedSessionRef.current = targetSessionId;
    handleSelect(targetConversation);
  }, [pageData?.sessionId, loading, conversations, handleSelect]);

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
      const res = await createConversationNote(
        user.tenantId,
        token,
        selected,
        content,
      );
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

  // Load snippets (lazy, cached)
  const loadSnippets = async () => {
    if (snippetsCache !== null) return; // already cached
    if (!user?.tenantId) return;
    setSnippetsLoading(true);
    try {
      const res = await fetchSnippets(user.tenantId, token);
      setSnippetsCache(res.snippets || res || []);
    } catch (err) {
      console.error("Failed to load snippets", err);
      setSnippetsCache([]); // cache empty to avoid re-fetching on error
    } finally {
      setSnippetsLoading(false);
    }
  };

  const toggleSnippetPicker = () => {
    const next = !showSnippetPicker;
    setShowSnippetPicker(next);
    setSnippetSearch("");
    if (next) {
      loadSnippets();
    }
  };

  const insertSnippet = (snippet) => {
    const textarea = replyTextareaRef.current;
    if (!textarea) {
      // Fallback: just append
      setReplyInput((prev) => {
        // If the user typed "/" to trigger, remove the trailing "/"
        if (prev.endsWith("/")) return prev.slice(0, -1) + snippet.content;
        return prev ? prev + "\n" + snippet.content : snippet.content;
      });
    } else {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const currentVal = replyInput;

      // Check if there's a "/" trigger to remove
      let insertStart = start;
      let prefix = currentVal.slice(0, start);
      if (prefix.endsWith("/")) {
        insertStart = start - 1;
        prefix = currentVal.slice(0, insertStart);
      }

      const after = currentVal.slice(end);
      const newVal = prefix + snippet.content + after;
      setReplyInput(newVal);

      // Move cursor to end of inserted content
      requestAnimationFrame(() => {
        const cursorPos = prefix.length + snippet.content.length;
        textarea.setSelectionRange(cursorPos, cursorPos);
        textarea.focus();
      });
    }

    setShowSnippetPicker(false);
    setSnippetSearch("");
  };

  const handleSendReply = async () => {
    const content = replyInput.trim();
    if (!content || !selected) return;
    setSendingReply(true);
    setReplyError(null);
    try {
      await replyToConversation(user.tenantId, token, selected, content);
      // Append the reply to the local messages list
      setMessages((prev) => [
        ...prev,
        {
          id: `reply-${Date.now()}`,
          role: "assistant",
          content,
          created_at: new Date().toISOString(),
        },
      ]);
      setReplyInput("");
    } catch (err) {
      console.error("Failed to send reply", err);
      // Surface the failure + keep the draft so a failed reply to a real
      // customer isn't silently lost with a false success (audit C4).
      setReplyError(err?.message || "Reply failed to send. Please try again.");
    } finally {
      setSendingReply(false);
    }
  };

  const handleSendSms = async () => {
    const phone = smsPhone.trim();
    const message = smsMessage.trim();
    if (!phone || !message) return;
    setSendingSms(true);
    setSmsError(null);
    setSmsSent(false);
    try {
      await sendSms(token, { phone, message });
      setSmsSent(true);
      setSmsPhone("");
      setSmsMessage("");
      // Refresh conversations so the new SMS thread appears
      load();
      setTimeout(() => {
        setSmsSent(false);
        setShowSmsCompose(false);
      }, 2000);
    } catch (err) {
      setSmsError(err.message || "Failed to send SMS. Please try again.");
    } finally {
      setSendingSms(false);
    }
  };

  const handleReplyKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendReply();
    }
  };

  const handleReplyChange = (e) => {
    const val = e.target.value;
    setReplyInput(val);

    // "/" shortcut trigger: if the user just typed "/" at start of input or after whitespace/newline
    if (val.endsWith("/")) {
      const charBefore = val.length >= 2 ? val[val.length - 2] : null;
      if (charBefore === null || charBefore === " " || charBefore === "\n") {
        loadSnippets();
        setShowSnippetPicker(true);
        setSnippetSearch("");
      }
    }
  };

  // Filter snippets for the picker
  const filteredSnippets = (snippetsCache || []).filter((s) => {
    if (!snippetSearch.trim()) return true;
    const q = snippetSearch.toLowerCase();
    return (
      (s.title || "").toLowerCase().includes(q) ||
      (s.content || "").toLowerCase().includes(q) ||
      (s.shortcut || "").toLowerCase().includes(q) ||
      (s.category || "").toLowerCase().includes(q)
    );
  });

  // Assign conversation to a team member
  const handleAssign = async (sessionId, assignedTo) => {
    setAssigning(true);
    try {
      await assignConversation(
        user.tenantId,
        token,
        sessionId,
        assignedTo || null,
      );
      setConversations((prev) =>
        prev.map((c) =>
          c.session_id === sessionId
            ? { ...c, assigned_to: assignedTo || null }
            : c,
        ),
      );
    } catch (err) {
      console.error("Failed to assign conversation", err);
    } finally {
      setAssigning(false);
    }
  };

  const handleAddLeadNote = async () => {
    if (!leadNoteInput.trim()) return;
    const conv = conversations.find((c) => c.session_id === selected);
    if (!conv?.lead_id) return;
    setAddingLeadNote(true);
    try {
      await addClientNote(
        user.tenantId,
        conv.lead_id,
        token,
        leadNoteInput.trim(),
      );
      setLeadNoteInput("");
      setLeadNoteSuccess(true);
      setTimeout(() => setLeadNoteSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to add lead note:", err);
    } finally {
      setAddingLeadNote(false);
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
        const time = m.created_at
          ? new Date(m.created_at).toLocaleString()
          : "";
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
        prev.map((c) =>
          c.session_id === sessionId ? { ...c, tags: newTags } : c,
        ),
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
        prev.map((c) =>
          c.session_id === sessionId ? { ...c, tags: newTags } : c,
        ),
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
      if (
        !(c.lead_name || "").toLowerCase().includes(q) &&
        !(c.preview || "").toLowerCase().includes(q)
      )
        return false;
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
        <div>
          <h1>Conversations</h1>
          <p>
            {conversations.length} chat session
            {conversations.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          className="btn-primary"
          onClick={() => {
            setShowSmsCompose(true);
            setSmsError(null);
            setSmsSent(false);
          }}
          style={{ whiteSpace: "nowrap" }}
        >
          New SMS
        </button>
      </div>

      {/* New SMS compose panel */}
      {showSmsCompose && (
        <div className="modal-overlay" onClick={() => setShowSmsCompose(false)}>
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: 460 }}
          >
            <h3 style={{ margin: "0 0 16px" }}>New SMS Message</h3>

            {smsError && (
              <div
                style={{
                  marginBottom: 12,
                  padding: "8px 12px",
                  borderRadius: 6,
                  fontSize: "0.85rem",
                  background: "rgba(239,68,68,0.08)",
                  border: "1px solid rgba(239,68,68,0.2)",
                  color: "var(--red, #ef4444)",
                }}
              >
                {smsError}
              </div>
            )}

            {smsSent && (
              <div
                style={{
                  marginBottom: 12,
                  padding: "8px 12px",
                  borderRadius: 6,
                  fontSize: "0.85rem",
                  background: "rgba(34,197,94,0.08)",
                  border: "1px solid rgba(34,197,94,0.2)",
                  color: "var(--green, #4ade80)",
                }}
              >
                SMS sent successfully.
              </div>
            )}

            <div className="modal-field">
              <label>Phone Number</label>
              <input
                className="modal-input"
                placeholder="+1 (555) 123-4567"
                value={smsPhone}
                onChange={(e) => setSmsPhone(e.target.value)}
                disabled={sendingSms}
              />
            </div>
            <div className="modal-field">
              <label>Message</label>
              <textarea
                className="modal-textarea"
                rows={4}
                placeholder="Type your message..."
                value={smsMessage}
                onChange={(e) => setSmsMessage(e.target.value)}
                disabled={sendingSms}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendSms();
                  }
                }}
              />
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                Press Enter to send, Shift+Enter for new line.
              </span>
            </div>

            <div className="modal-actions">
              <button
                className="btn-primary"
                onClick={handleSendSms}
                disabled={sendingSms || !smsPhone.trim() || !smsMessage.trim()}
              >
                {sendingSms ? "Sending..." : "Send SMS"}
              </button>
              <button
                className="btn-secondary"
                onClick={() => setShowSmsCompose(false)}
                disabled={sendingSms}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {conversations.length === 0 ? (
        <div
          style={{
            background: "var(--bg-secondary)",
            borderRadius: 12,
            padding: 48,
            textAlign: "center",
            margin: "8px 0",
          }}
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--text-muted)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ marginBottom: 12 }}
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <div
            style={{
              fontWeight: 600,
              fontSize: "1rem",
              color: "var(--text-primary)",
              marginBottom: 8,
            }}
          >
            {loadError ? "Couldn't load conversations" : "No conversations yet"}
          </div>
          <div
            style={{
              fontSize: "0.875rem",
              color: "var(--text-muted)",
              maxWidth: 420,
              margin: "0 auto",
            }}
          >
            {loadError
              ? loadError
              : "Conversations from your chat widget will appear here in real time. Once a visitor starts chatting, you'll see their messages, lead info, and AI responses."}
          </div>
          {loadError && (
            <button
              className="btn-primary"
              onClick={load}
              style={{ marginTop: 12, padding: "6px 16px", fontSize: "0.8rem" }}
            >
              Retry
            </button>
          )}
        </div>
      ) : (
        <div className="conversations-layout">
          <div className="conv-sidebar">
            {/* Inbox filter toggle */}
            <div
              style={{
                display: "flex",
                gap: 0,
                marginBottom: 8,
                borderRadius: 8,
                overflow: "hidden",
                border: "1px solid var(--border)",
              }}
            >
              <button
                onClick={() => setInboxFilter("all")}
                style={{
                  flex: 1,
                  padding: "7px 10px",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  border: "none",
                  cursor: "pointer",
                  background:
                    inboxFilter === "all"
                      ? "var(--accent, #00BFFF)"
                      : "var(--bg-secondary)",
                  color:
                    inboxFilter === "all" ? "#fff" : "var(--text-secondary)",
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
                  borderLeft: "1px solid var(--border)",
                  cursor: "pointer",
                  background:
                    inboxFilter === "mine"
                      ? "var(--accent, #00BFFF)"
                      : "var(--bg-secondary)",
                  color:
                    inboxFilter === "mine" ? "#fff" : "var(--text-secondary)",
                  transition: "background 0.15s, color 0.15s",
                }}
              >
                Mine ({myCount})
              </button>
            </div>

            <input
              className="conv-search"
              placeholder="Search conversations... (Enter to search messages)"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                if (!e.target.value) setServerSearch("");
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") setServerSearch(search);
              }}
            />
            <select
              value={channelFilter}
              onChange={(e) => {
                setChannelFilter(e.target.value);
                setSelected(null);
              }}
              style={{
                width: "100%",
                padding: "6px 8px",
                marginBottom: 8,
                borderRadius: 6,
                border: "1px solid var(--border)",
                background: "var(--bg-secondary)",
                color: "var(--text-primary)",
                fontSize: "0.8rem",
              }}
            >
              <option value="">All Channels</option>
              <option value="widget">Widget (Chat)</option>
              <option value="sms">SMS</option>
              <option value="facebook">Facebook</option>
            </select>
            {allTags.length > 0 && (
              <select
                value={tagFilter}
                onChange={(e) => setTagFilter(e.target.value)}
                style={{
                  width: "100%",
                  padding: "6px 8px",
                  marginBottom: 8,
                  borderRadius: 6,
                  border: "1px solid var(--border)",
                  background: "var(--bg-secondary)",
                  color: "var(--text-primary)",
                  fontSize: "0.8rem",
                }}
              >
                <option value="">All tags ({conversations.length})</option>
                {allTags.map((t) => (
                  <option key={t} value={t}>
                    {t} ({tagCounts[t]})
                  </option>
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
                      <span className="conv-item-name">
                        {c.lead_name || "Visitor"}
                      </span>
                      <span className="conv-item-time">
                        {timeAgo(c.last_message_at)}
                      </span>
                    </div>
                    <div className="conv-item-preview">
                      {c.preview || c.last_message || "No messages"}
                    </div>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginTop: 2,
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 5,
                        }}
                      >
                        <span className="conv-item-count">
                          {c.message_count} message
                          {c.message_count !== 1 ? "s" : ""}
                        </span>
                        {(() => {
                          const ch = c.channel || "widget";
                          const badge =
                            CHANNEL_BADGE[ch] || CHANNEL_BADGE.widget;
                          return (
                            <span
                              style={{
                                fontSize: "0.62rem",
                                fontWeight: 600,
                                padding: "1px 5px",
                                borderRadius: 4,
                                color: badge.color,
                                background: badge.bg,
                                lineHeight: 1.4,
                                flexShrink: 0,
                              }}
                            >
                              {badge.label}
                            </span>
                          );
                        })()}
                        {c.lead_id && (
                          <span
                            style={{
                              fontSize: "0.62rem",
                              fontWeight: 600,
                              padding: "1px 5px",
                              borderRadius: 4,
                              color: "#4caf50",
                              background: "rgba(76, 175, 80, 0.12)",
                              lineHeight: 1.4,
                              flexShrink: 0,
                            }}
                          >
                            Lead
                          </span>
                        )}
                      </div>
                      <span
                        style={{
                          fontSize: "0.7rem",
                          color: assigneeName
                            ? "var(--accent, #00BFFF)"
                            : "var(--text-muted)",
                          fontStyle: assigneeName ? "normal" : "italic",
                          maxWidth: 100,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {assigneeName || "Unassigned"}
                      </span>
                    </div>
                    {(c.tags || []).length > 0 && (
                      <div
                        style={{
                          display: "flex",
                          flexWrap: "wrap",
                          gap: 4,
                          marginTop: 4,
                        }}
                      >
                        {c.tags.map((tag) => (
                          <span key={tag} style={tagPillStyle(tag)}>
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
              {filtered.length === 0 && (
                <div
                  style={{
                    padding: "1rem",
                    color: "var(--text-muted)",
                    fontSize: "0.85rem",
                  }}
                >
                  {inboxFilter === "mine" && myCount === 0
                    ? 'No conversations assigned to you yet. Assign conversations from the conversation view, or switch to "All" to see all conversations.'
                    : channelFilter
                      ? `No ${CHANNEL_BADGE[channelFilter]?.label || channelFilter} conversations found. Switch to "All Channels" to see all conversations.`
                      : tagFilter
                        ? `No conversations tagged "${tagFilter}". Try selecting "All tags" to clear the filter.`
                        : "No conversations match your search."}
                </div>
              )}
            </div>
          </div>

          <div className="conv-messages">
            {!selected ? (
              <div className="conv-empty-state">
                Select a conversation to view messages
              </div>
            ) : loadingMessages ? (
              <div className="conv-empty-state">Loading...</div>
            ) : (
              <div className="conv-message-list">
                {/* Toolbar: Assign dropdown + Tag management + Export + Notes toggle */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "0 0 0.5rem",
                    gap: 8,
                    flexWrap: "wrap",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      gap: 8,
                      alignItems: "center",
                      flexWrap: "wrap",
                      flex: 1,
                    }}
                  >
                    {/* Assign to dropdown */}
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 4 }}
                    >
                      <label
                        style={{
                          fontSize: "0.75rem",
                          color: "var(--text-muted)",
                          whiteSpace: "nowrap",
                        }}
                      >
                        Assign:
                      </label>
                      <select
                        value={selectedConv?.assigned_to || ""}
                        onChange={(e) => handleAssign(selected, e.target.value)}
                        disabled={assigning}
                        style={{
                          padding: "4px 8px",
                          fontSize: "0.75rem",
                          borderRadius: 6,
                          border: "1px solid var(--border)",
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
                    <span
                      style={{
                        width: 1,
                        height: 16,
                        background: "var(--border)",
                        flexShrink: 0,
                      }}
                    />

                    {/* Tags */}
                    {(selectedConv?.tags || []).map((tag) => {
                      const color = getTagColor(tag);
                      const pillBg = color
                        ? color + "26"
                        : "var(--accent-dim, rgba(0,191,255,0.15))";
                      const pillColor = color || "var(--accent, #00BFFF)";
                      return (
                        <span
                          key={tag}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                            padding: "2px 8px",
                            borderRadius: 10,
                            fontSize: "0.75rem",
                            background: pillBg,
                            color: pillColor,
                          }}
                        >
                          {tag}
                          <span
                            onClick={() => removeTag(selected, tag)}
                            style={{ cursor: "pointer", fontWeight: 700 }}
                          >
                            &times;
                          </span>
                        </span>
                      );
                    })}
                    <input
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") addTag(selected);
                      }}
                      placeholder="Add tag..."
                      style={{
                        width: 80,
                        padding: "2px 6px",
                        fontSize: "0.75rem",
                        borderRadius: 6,
                        border: "1px solid var(--border)",
                        background: "var(--bg-secondary)",
                        color: "var(--text-primary)",
                      }}
                    />
                  </div>
                  <div
                    style={{ display: "flex", gap: 6, alignItems: "center" }}
                  >
                    <button
                      className="btn-sm"
                      onClick={toggleNotes}
                      style={{
                        background: showNotes
                          ? "rgba(139,92,246,0.15)"
                          : undefined,
                        color: showNotes ? "rgba(167,139,250,1)" : undefined,
                        borderColor: showNotes
                          ? "rgba(139,92,246,0.3)"
                          : undefined,
                      }}
                    >
                      Notes {notes.length > 0 ? `(${notes.length})` : ""}
                    </button>
                    {(() => {
                      const conv = conversations.find(
                        (c) => c.session_id === selected,
                      );
                      return conv?.lead_id ? (
                        <button
                          className="btn-sm"
                          onClick={() => setShowLeadNote(!showLeadNote)}
                          style={{
                            background: showLeadNote
                              ? "rgba(16,185,129,0.15)"
                              : undefined,
                            color: showLeadNote ? "#10b981" : undefined,
                            borderColor: showLeadNote
                              ? "rgba(16,185,129,0.3)"
                              : undefined,
                          }}
                          title="Add a note to the linked lead"
                        >
                          Lead Note
                        </button>
                      ) : null;
                    })()}
                    {messages.length > 0 && (
                      <button className="btn-sm" onClick={exportConversation}>
                        Export
                      </button>
                    )}
                  </div>
                </div>

                {/* Chat messages */}
                {messages.map((m) => (
                  <div key={m.id} className={`conv-msg ${m.role}`}>
                    <div className="conv-msg-role">
                      {m.role === "user" ? "Visitor" : "AI"}
                    </div>
                    {m.role === "assistant" ? (
                      <div
                        className="conv-msg-content"
                        dangerouslySetInnerHTML={{
                          __html: DOMPurify.sanitize(
                            renderMarkdown(m.content || ""),
                          ),
                        }}
                      />
                    ) : (
                      <div className="conv-msg-content">{m.content}</div>
                    )}
                    <div className="conv-msg-time">{timeAgo(m.created_at)}</div>
                  </div>
                ))}
                {messages.length === 0 && (
                  <div className="conv-empty-state">
                    No messages in this conversation.
                  </div>
                )}

                {/* Lead Captured banner */}
                {selected &&
                  (() => {
                    const conv = conversations.find(
                      (c) => c.session_id === selected,
                    );
                    return conv?.lead_id ? (
                      <div
                        style={{
                          background: "rgba(76, 175, 80, 0.08)",
                          border: "1px solid rgba(76, 175, 80, 0.25)",
                          borderRadius: 8,
                          padding: "8px 12px",
                          margin: "10px 0 0",
                          textAlign: "center",
                          fontSize: "0.8rem",
                          color: "#4caf50",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: 6,
                        }}
                      >
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="#4caf50"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                        <span style={{ fontWeight: 600 }}>Lead Captured</span>
                        <span
                          style={{
                            color: "rgba(76, 175, 80, 0.7)",
                            fontWeight: 400,
                          }}
                        >
                          {conv.lead_name
                            ? `\u2014 ${conv.lead_name}`
                            : "\u2014 Contact info detected"}
                        </span>
                      </div>
                    ) : null;
                  })()}

                {/* Internal Notes Panel */}
                {showNotes && (
                  <div
                    style={{
                      marginTop: "1rem",
                      padding: "1rem",
                      borderRadius: 10,
                      background: "rgba(139,92,246,0.06)",
                      border: "1px solid rgba(139,92,246,0.2)",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "0.75rem",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                        }}
                      >
                        <span
                          style={{
                            fontWeight: 600,
                            fontSize: "0.9rem",
                            color: "var(--text-primary)",
                          }}
                        >
                          Internal Notes
                        </span>
                        <span
                          style={{
                            fontSize: "0.65rem",
                            padding: "2px 6px",
                            borderRadius: 4,
                            background: "rgba(139,92,246,0.15)",
                            color: "rgba(167,139,250,1)",
                            fontWeight: 600,
                            textTransform: "uppercase",
                            letterSpacing: "0.5px",
                          }}
                        >
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
                      <div
                        style={{
                          color: "var(--text-muted)",
                          fontSize: "0.85rem",
                          padding: "0.5rem 0",
                        }}
                      >
                        Loading notes...
                      </div>
                    ) : notes.length === 0 ? (
                      <div
                        style={{
                          color: "var(--text-muted)",
                          fontSize: "0.85rem",
                          padding: "0.5rem 0",
                        }}
                      >
                        No internal notes yet. Use notes to share context with
                        your team about this conversation.
                      </div>
                    ) : (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 8,
                          marginBottom: "0.75rem",
                        }}
                      >
                        {notes.map((note) => (
                          <div
                            key={note.id}
                            style={{
                              padding: "10px 12px",
                              borderRadius: 8,
                              background: "rgba(139,92,246,0.08)",
                              border: "1px solid rgba(139,92,246,0.12)",
                            }}
                          >
                            <div
                              style={{
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "flex-start",
                              }}
                            >
                              <div>
                                <span
                                  style={{
                                    fontSize: "0.8rem",
                                    fontWeight: 600,
                                    color: "rgba(167,139,250,1)",
                                  }}
                                >
                                  {note.author_name ||
                                    note.author_email ||
                                    "Team Member"}
                                </span>
                                <span
                                  style={{
                                    fontSize: "0.7rem",
                                    color: "var(--text-muted)",
                                    marginLeft: 8,
                                  }}
                                >
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
                            <div
                              style={{
                                fontSize: "0.85rem",
                                color: "var(--text-primary)",
                                marginTop: 4,
                                lineHeight: 1.5,
                                whiteSpace: "pre-wrap",
                              }}
                            >
                              {note.content}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Add note input */}
                    <div
                      style={{
                        display: "flex",
                        gap: 8,
                        alignItems: "flex-end",
                      }}
                    >
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

                {/* Quick Lead Note Panel */}
                {showLeadNote &&
                  (() => {
                    const conv = conversations.find(
                      (c) => c.session_id === selected,
                    );
                    return conv?.lead_id ? (
                      <div
                        style={{
                          marginTop: "1rem",
                          padding: "1rem",
                          borderRadius: 10,
                          background: "rgba(16,185,129,0.06)",
                          border: "1px solid rgba(16,185,129,0.2)",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            marginBottom: "0.5rem",
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 8,
                            }}
                          >
                            <span
                              style={{
                                fontWeight: 600,
                                fontSize: "0.9rem",
                                color: "var(--text-primary)",
                              }}
                            >
                              Quick Lead Note
                            </span>
                            <span
                              style={{
                                fontSize: "0.65rem",
                                padding: "2px 6px",
                                borderRadius: 4,
                                background: "rgba(16,185,129,0.15)",
                                color: "#10b981",
                                fontWeight: 600,
                                textTransform: "uppercase",
                                letterSpacing: "0.5px",
                              }}
                            >
                              {conv.lead_name || "Lead"}
                            </span>
                          </div>
                          <button
                            onClick={() => setShowLeadNote(false)}
                            style={{
                              background: "none",
                              border: "none",
                              color: "var(--text-muted)",
                              cursor: "pointer",
                              fontSize: "1rem",
                              padding: "0 4px",
                              lineHeight: 1,
                            }}
                            title="Close"
                          >
                            &times;
                          </button>
                        </div>
                        {leadNoteSuccess && (
                          <div
                            style={{
                              color: "#10b981",
                              fontSize: "0.8rem",
                              marginBottom: "0.5rem",
                              fontWeight: 500,
                            }}
                          >
                            Note added to lead successfully!
                          </div>
                        )}
                        <div
                          style={{
                            display: "flex",
                            gap: 8,
                            alignItems: "flex-start",
                          }}
                        >
                          <textarea
                            value={leadNoteInput}
                            onChange={(e) => setLeadNoteInput(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                handleAddLeadNote();
                              }
                            }}
                            placeholder="Add a note about this lead..."
                            rows={2}
                            style={{
                              flex: 1,
                              padding: "8px 10px",
                              fontSize: "0.85rem",
                              borderRadius: 8,
                              border: "1px solid rgba(16,185,129,0.3)",
                              background: "var(--bg-primary)",
                              color: "var(--text-primary)",
                              resize: "vertical",
                            }}
                          />
                          <button
                            className="btn-primary"
                            onClick={handleAddLeadNote}
                            disabled={addingLeadNote || !leadNoteInput.trim()}
                            style={{
                              padding: "8px 14px",
                              fontSize: "0.8rem",
                              whiteSpace: "nowrap",
                              height: "fit-content",
                            }}
                          >
                            {addingLeadNote ? "Adding..." : "Save"}
                          </button>
                        </div>
                      </div>
                    ) : null;
                  })()}

                {/* Reply area with snippet picker */}
                <div
                  style={{
                    marginTop: "1rem",
                    padding: "0.75rem",
                    borderRadius: 10,
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border)",
                    position: "relative",
                  }}
                >
                  {replyError && (
                    <div
                      style={{
                        color: "var(--red)",
                        fontSize: "0.75rem",
                        marginBottom: 8,
                      }}
                    >
                      {replyError}
                    </div>
                  )}
                  {/* Channel indicator for outbound reply */}
                  {(() => {
                    const convChannel = selectedConv?.channel || "widget";
                    const badge =
                      CHANNEL_BADGE[convChannel] || CHANNEL_BADGE.widget;
                    return (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 5,
                          marginBottom: 8,
                          fontSize: "0.72rem",
                          color: "var(--text-muted)",
                        }}
                      >
                        <span>Reply via</span>
                        <span
                          style={{
                            fontWeight: 600,
                            padding: "1px 6px",
                            borderRadius: 4,
                            color: badge.color,
                            background: badge.bg,
                            fontSize: "0.72rem",
                          }}
                        >
                          {badge.label}
                        </span>
                      </div>
                    );
                  })()}
                  <div
                    style={{ display: "flex", gap: 8, alignItems: "flex-end" }}
                  >
                    {/* Snippet picker button */}
                    <div
                      style={{ position: "relative" }}
                      ref={snippetPickerRef}
                    >
                      <button
                        onClick={toggleSnippetPicker}
                        title="Insert snippet (or type / in the reply box)"
                        style={{
                          background: showSnippetPicker
                            ? "rgba(59,130,246,0.15)"
                            : "transparent",
                          border: showSnippetPicker
                            ? "1px solid rgba(59,130,246,0.3)"
                            : "1px solid var(--border)",
                          borderRadius: 8,
                          padding: "8px 10px",
                          cursor: "pointer",
                          color: showSnippetPicker
                            ? "#3b82f6"
                            : "var(--text-secondary)",
                          fontSize: "1rem",
                          lineHeight: 1,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          height: 38,
                          width: 38,
                          transition: "all 0.15s ease",
                        }}
                      >
                        <svg
                          width="18"
                          height="18"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                        </svg>
                      </button>

                      {/* Snippet picker dropdown */}
                      {showSnippetPicker && (
                        <div
                          style={{
                            position: "absolute",
                            bottom: "calc(100% + 8px)",
                            left: 0,
                            width: 360,
                            maxHeight: 380,
                            background: "var(--bg-primary)",
                            border: "1px solid var(--border)",
                            borderRadius: 12,
                            boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
                            display: "flex",
                            flexDirection: "column",
                            overflow: "hidden",
                            zIndex: 100,
                          }}
                        >
                          {/* Picker header */}
                          <div
                            style={{
                              padding: "10px 12px",
                              borderBottom: "1px solid var(--border)",
                            }}
                          >
                            <div
                              style={{
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                                marginBottom: 8,
                              }}
                            >
                              <span
                                style={{
                                  fontWeight: 600,
                                  fontSize: "0.85rem",
                                  color: "var(--text-primary)",
                                }}
                              >
                                Insert Snippet
                              </span>
                              <span
                                style={{
                                  fontSize: "0.65rem",
                                  color: "var(--text-muted)",
                                  padding: "2px 6px",
                                  borderRadius: 4,
                                  background: "var(--bg-secondary)",
                                  fontFamily: "monospace",
                                }}
                              >
                                / shortcut
                              </span>
                            </div>
                            <input
                              ref={snippetSearchRef}
                              type="text"
                              value={snippetSearch}
                              onChange={(e) => setSnippetSearch(e.target.value)}
                              placeholder="Search snippets..."
                              style={{
                                width: "100%",
                                padding: "7px 10px",
                                borderRadius: 6,
                                border: "1px solid var(--border)",
                                background: "var(--bg-secondary)",
                                color: "var(--text-primary)",
                                fontSize: "0.8rem",
                                outline: "none",
                              }}
                              onKeyDown={(e) => {
                                if (e.key === "Escape") {
                                  setShowSnippetPicker(false);
                                  setSnippetSearch("");
                                  replyTextareaRef.current?.focus();
                                }
                                // Enter selects first filtered snippet
                                if (
                                  e.key === "Enter" &&
                                  filteredSnippets.length > 0
                                ) {
                                  e.preventDefault();
                                  insertSnippet(filteredSnippets[0]);
                                }
                              }}
                            />
                          </div>

                          {/* Picker body */}
                          <div
                            style={{
                              flex: 1,
                              overflowY: "auto",
                              padding: "4px 0",
                            }}
                          >
                            {snippetsLoading ? (
                              <div
                                style={{
                                  padding: "1.5rem",
                                  textAlign: "center",
                                  color: "var(--text-muted)",
                                  fontSize: "0.85rem",
                                }}
                              >
                                Loading snippets...
                              </div>
                            ) : filteredSnippets.length === 0 ? (
                              <div
                                style={{
                                  padding: "1.5rem 1rem",
                                  textAlign: "center",
                                  color: "var(--text-muted)",
                                  fontSize: "0.85rem",
                                  lineHeight: 1.6,
                                }}
                              >
                                {(snippetsCache || []).length === 0
                                  ? "No snippets created yet. Go to Snippets in the sidebar to create reusable reply templates."
                                  : "No snippets match your search. Try a different keyword."}
                              </div>
                            ) : (
                              filteredSnippets.map((snippet) => {
                                const catKey = (
                                  snippet.category || "general"
                                ).toLowerCase();
                                const catColor =
                                  SNIPPET_CATEGORY_COLORS[catKey] ||
                                  SNIPPET_CATEGORY_COLORS.general;
                                return (
                                  <button
                                    key={snippet.id}
                                    onClick={() => insertSnippet(snippet)}
                                    style={{
                                      display: "block",
                                      width: "100%",
                                      padding: "10px 12px",
                                      background: "transparent",
                                      border: "none",
                                      borderBottom: "1px solid var(--border)",
                                      cursor: "pointer",
                                      textAlign: "left",
                                      transition: "background 0.1s ease",
                                      color: "inherit",
                                    }}
                                    onMouseEnter={(e) => {
                                      e.currentTarget.style.background =
                                        "var(--bg-secondary)";
                                    }}
                                    onMouseLeave={(e) => {
                                      e.currentTarget.style.background =
                                        "transparent";
                                    }}
                                  >
                                    <div
                                      style={{
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 8,
                                        marginBottom: 4,
                                      }}
                                    >
                                      <span
                                        style={{
                                          fontWeight: 600,
                                          fontSize: "0.85rem",
                                          color: "var(--text-primary)",
                                          flex: 1,
                                          minWidth: 0,
                                          overflow: "hidden",
                                          textOverflow: "ellipsis",
                                          whiteSpace: "nowrap",
                                        }}
                                      >
                                        {snippet.title}
                                      </span>
                                      <span
                                        style={{
                                          display: "inline-block",
                                          padding: "1px 6px",
                                          borderRadius: 4,
                                          fontSize: "0.65rem",
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
                                      {snippet.shortcut && (
                                        <span
                                          style={{
                                            fontSize: "0.65rem",
                                            fontFamily: "monospace",
                                            color: "var(--accent, #00BFFF)",
                                            background:
                                              "var(--accent-dim, rgba(0,191,255,0.1))",
                                            padding: "1px 5px",
                                            borderRadius: 3,
                                            flexShrink: 0,
                                          }}
                                        >
                                          /{snippet.shortcut}
                                        </span>
                                      )}
                                    </div>
                                    <div
                                      style={{
                                        fontSize: "0.78rem",
                                        color: "var(--text-secondary)",
                                        lineHeight: 1.4,
                                        overflow: "hidden",
                                        textOverflow: "ellipsis",
                                        display: "-webkit-box",
                                        WebkitLineClamp: 2,
                                        WebkitBoxOrient: "vertical",
                                      }}
                                    >
                                      {snippet.content}
                                    </div>
                                  </button>
                                );
                              })
                            )}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Reply textarea */}
                    <textarea
                      ref={replyTextareaRef}
                      value={replyInput}
                      onChange={handleReplyChange}
                      onKeyDown={handleReplyKeyDown}
                      placeholder='Type a reply... (Enter to send, Shift+Enter for new line, "/" for snippets)'
                      rows={2}
                      style={{
                        flex: 1,
                        padding: "8px 10px",
                        fontSize: "0.85rem",
                        borderRadius: 8,
                        border: "1px solid var(--border)",
                        background: "var(--bg-primary)",
                        color: "var(--text-primary)",
                        resize: "vertical",
                        minHeight: 40,
                        fontFamily: "inherit",
                        outline: "none",
                      }}
                    />

                    {/* Send button */}
                    <button
                      className="btn-primary"
                      onClick={handleSendReply}
                      disabled={sendingReply || !replyInput.trim()}
                      style={{
                        padding: "8px 16px",
                        fontSize: "0.8rem",
                        whiteSpace: "nowrap",
                        height: "fit-content",
                      }}
                    >
                      {sendingReply ? "Sending..." : "Send"}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
