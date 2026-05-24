import { useState, useEffect, useCallback, useRef } from "react";
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
import {
  buildTagColorMap,
  tagPillStyle as _tagPillStyle,
} from "./Conversations/utils";
import ConversationSidebar from "./Conversations/ConversationSidebar";
import ConversationToolbar from "./Conversations/ConversationToolbar";
import MessageList from "./Conversations/MessageList";
import InternalNotesPanel from "./Conversations/InternalNotesPanel";
import LeadNotePanel from "./Conversations/LeadNotePanel";
import ReplyComposer from "./Conversations/ReplyComposer";
import SmsComposeModal from "./Conversations/SmsComposeModal";

export default function ConversationsPage({ pageData }) {
  const { user, token } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [search, setSearch] = useState("");
  const [serverSearch, setServerSearch] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [tagDefs, setTagDefs] = useState([]);

  const [inboxFilter, setInboxFilter] = useState("all");
  const [teamMembers, setTeamMembers] = useState([]);
  const [teamMemberMap, setTeamMemberMap] = useState({});
  const [assigning, setAssigning] = useState(false);

  const [showNotes, setShowNotes] = useState(false);
  const [notes, setNotes] = useState([]);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [noteInput, setNoteInput] = useState("");
  const [addingNote, setAddingNote] = useState(false);

  const [showLeadNote, setShowLeadNote] = useState(false);
  const [leadNoteInput, setLeadNoteInput] = useState("");
  const [addingLeadNote, setAddingLeadNote] = useState(false);
  const [leadNoteSuccess, setLeadNoteSuccess] = useState(false);

  const [replyInput, setReplyInput] = useState("");
  const [sendingReply, setSendingReply] = useState(false);

  const [showSmsCompose, setShowSmsCompose] = useState(false);
  const [smsPhone, setSmsPhone] = useState("");
  const [smsMessage, setSmsMessage] = useState("");
  const [sendingSms, setSendingSms] = useState(false);
  const [smsError, setSmsError] = useState(null);
  const [smsSent, setSmsSent] = useState(false);

  const [showSnippetPicker, setShowSnippetPicker] = useState(false);
  const [snippetsCache, setSnippetsCache] = useState(null);
  const [snippetsLoading, setSnippetsLoading] = useState(false);
  const [snippetSearch, setSnippetSearch] = useState("");
  const snippetPickerRef = useRef(null);
  const replyTextareaRef = useRef(null);
  const snippetSearchRef = useRef(null);
  const autoSelectedSessionRef = useRef(null);

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
      if (res && res.id) {
        setNotes((prev) => [...prev, res]);
      } else {
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

  const loadSnippets = async () => {
    if (snippetsCache !== null) return;
    if (!user?.tenantId) return;
    setSnippetsLoading(true);
    try {
      const res = await fetchSnippets(user.tenantId, token);
      setSnippetsCache(res.snippets || res || []);
    } catch (err) {
      console.error("Failed to load snippets", err);
      setSnippetsCache([]);
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
      setReplyInput((prev) => {
        if (prev.endsWith("/")) return prev.slice(0, -1) + snippet.content;
        return prev ? prev + "\n" + snippet.content : snippet.content;
      });
    } else {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const currentVal = replyInput;

      let insertStart = start;
      let prefix = currentVal.slice(0, start);
      if (prefix.endsWith("/")) {
        insertStart = start - 1;
        prefix = currentVal.slice(0, insertStart);
      }

      const after = currentVal.slice(end);
      const newVal = prefix + snippet.content + after;
      setReplyInput(newVal);

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
    try {
      await replyToConversation(user.tenantId, token, selected, content);
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

    if (val.endsWith("/")) {
      const charBefore = val.length >= 2 ? val[val.length - 2] : null;
      if (charBefore === null || charBefore === " " || charBefore === "\n") {
        loadSnippets();
        setShowSnippetPicker(true);
        setSnippetSearch("");
      }
    }
  };

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

  const tagColorMap = buildTagColorMap(tagDefs);

  function getAssigneeName(assignedTo) {
    if (!assignedTo) return null;
    if (teamMemberMap[assignedTo]) return teamMemberMap[assignedTo].name;
    return "Team Member";
  }

  const tagCounts = {};
  conversations.forEach((c) => {
    (c.tags || []).forEach((t) => {
      tagCounts[t] = (tagCounts[t] || 0) + 1;
    });
  });
  const allTags = Object.keys(tagCounts).sort();

  if (loading) return <SkeletonLoader />;

  const currentUserId = user?.userId || null;

  const filtered = conversations.filter((c) => {
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

      {showSmsCompose && (
        <SmsComposeModal
          smsPhone={smsPhone}
          setSmsPhone={setSmsPhone}
          smsMessage={smsMessage}
          setSmsMessage={setSmsMessage}
          sendingSms={sendingSms}
          smsError={smsError}
          smsSent={smsSent}
          onSend={handleSendSms}
          onClose={() => setShowSmsCompose(false)}
        />
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
            No conversations yet
          </div>
          <div
            style={{
              fontSize: "0.875rem",
              color: "var(--text-muted)",
              maxWidth: 420,
              margin: "0 auto",
            }}
          >
            Conversations from your chat widget will appear here in real time.
            Once a visitor starts chatting, you'll see their messages, lead
            info, and AI responses.
          </div>
        </div>
      ) : (
        <div className="conversations-layout">
          <ConversationSidebar
            conversations={conversations}
            filtered={filtered}
            selected={selected}
            myCount={myCount}
            allTags={allTags}
            tagCounts={tagCounts}
            inboxFilter={inboxFilter}
            setInboxFilter={setInboxFilter}
            search={search}
            setSearch={setSearch}
            setServerSearch={setServerSearch}
            channelFilter={channelFilter}
            setChannelFilter={setChannelFilter}
            setSelected={setSelected}
            tagFilter={tagFilter}
            setTagFilter={setTagFilter}
            tagColorMap={tagColorMap}
            getAssigneeName={getAssigneeName}
            handleSelect={handleSelect}
          />

          <div className="conv-messages">
            {!selected ? (
              <div className="conv-empty-state">
                Select a conversation to view messages
              </div>
            ) : loadingMessages ? (
              <div className="conv-empty-state">Loading...</div>
            ) : (
              <div className="conv-message-list">
                <ConversationToolbar
                  selectedConv={selectedConv}
                  selected={selected}
                  teamMembers={teamMembers}
                  assigning={assigning}
                  handleAssign={handleAssign}
                  tagInput={tagInput}
                  setTagInput={setTagInput}
                  addTag={addTag}
                  removeTag={removeTag}
                  tagColorMap={tagColorMap}
                  showNotes={showNotes}
                  notes={notes}
                  toggleNotes={toggleNotes}
                  showLeadNote={showLeadNote}
                  setShowLeadNote={setShowLeadNote}
                  messages={messages}
                  exportConversation={exportConversation}
                />

                <MessageList messages={messages} selectedConv={selectedConv} />

                {showNotes && (
                  <InternalNotesPanel
                    notes={notes}
                    loadingNotes={loadingNotes}
                    noteInput={noteInput}
                    setNoteInput={setNoteInput}
                    addingNote={addingNote}
                    toggleNotes={toggleNotes}
                    handleAddNote={handleAddNote}
                    handleDeleteNote={handleDeleteNote}
                  />
                )}

                {showLeadNote && (
                  <LeadNotePanel
                    selectedConv={selectedConv}
                    leadNoteInput={leadNoteInput}
                    setLeadNoteInput={setLeadNoteInput}
                    addingLeadNote={addingLeadNote}
                    leadNoteSuccess={leadNoteSuccess}
                    handleAddLeadNote={handleAddLeadNote}
                    setShowLeadNote={setShowLeadNote}
                  />
                )}

                <ReplyComposer
                  selectedConv={selectedConv}
                  replyInput={replyInput}
                  handleReplyChange={handleReplyChange}
                  handleReplyKeyDown={handleReplyKeyDown}
                  handleSendReply={handleSendReply}
                  sendingReply={sendingReply}
                  replyTextareaRef={replyTextareaRef}
                  snippetPickerRef={snippetPickerRef}
                  showSnippetPicker={showSnippetPicker}
                  toggleSnippetPicker={toggleSnippetPicker}
                  setShowSnippetPicker={setShowSnippetPicker}
                  snippetSearchRef={snippetSearchRef}
                  snippetSearch={snippetSearch}
                  setSnippetSearch={setSnippetSearch}
                  filteredSnippets={filteredSnippets}
                  snippetsLoading={snippetsLoading}
                  snippetsCache={snippetsCache}
                  insertSnippet={insertSnippet}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
