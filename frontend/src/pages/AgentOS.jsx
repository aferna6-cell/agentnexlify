/**
 * Agent OS - chat-first orchestrator shell (P0).
 *
 * Left rail lists task threads. The main column is the chat: the owner
 * posts a task, the orchestrator answers / delegates / backlogs it, and
 * delegated work shows up as an agent run with a thought-process
 * flowchart. Approval-gated drafts open in the side DeliverablePanel.
 *
 * Threads + runs are polled while any run is queued/running so the
 * async background worker's post-back lands in the UI without a reload.
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import {
  listOsThreads,
  createOsThread,
  fetchOsThreadMessages,
  orchestrateOsTurn,
  postOsMessage,
  fetchOsUsage,
} from "../utils/api/os";
import AgentRunFlowchart from "../components/os/AgentRunFlowchart";
import DeliverablePanel from "../components/os/DeliverablePanel";
import DemoTour from "../components/os/DemoTour";
import MemoryPanel from "../components/os/MemoryPanel";
import FirstRunStarters from "../components/os/FirstRunStarters";
import OsInsightsCard from "../components/os/OsInsightsCard";
import ComposerAttachments from "../components/os/ComposerAttachments";
import UsageUpgradeNudge from "../components/UsageUpgradeNudge";
import UpgradePrompt from "../components/UpgradePrompt";
import useIsMobile from "../hooks/useIsMobile";

const POLL_MS = 3000;

function relTime(at) {
  if (!at) return "";
  const d = new Date(at);
  if (Number.isNaN(d.getTime())) return "";
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

const ROLE_META = {
  user: { align: "flex-end", bg: "var(--accent-dim)", label: null },
  assistant: { align: "flex-start", bg: "var(--bg-secondary)", label: null },
  agent: {
    align: "flex-start",
    bg: "var(--bg-secondary)",
    label: "Worker agent",
  },
};

// Source badge metadata for the thread rail. 'chat' = owner-typed
// orchestrator task (no badge shown). The other four are inbound
// customer-facing channels surfaced through os_inbound_bridge.
const SOURCE_META = {
  chat: { label: "Owner", color: "var(--text-muted)", show: false },
  widget: { label: "Widget", color: "#22c55e", show: true },
  email: { label: "Email", color: "#3b82f6", show: true },
  sms: { label: "SMS", color: "#a855f7", show: true },
  facebook: { label: "Facebook", color: "#0ea5e9", show: true },
};

const SOURCE_FILTERS = [
  { key: "all", label: "All" },
  { key: "chat", label: "Owner" },
  { key: "widget", label: "Widget" },
  { key: "email", label: "Email" },
  { key: "sms", label: "SMS" },
  { key: "facebook", label: "Facebook" },
];

export default function AgentOS({ onNavigate }) {
  const { token, user } = useAuth();

  const [threads, setThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [runs, setRuns] = useState([]);
  const [usage, setUsage] = useState(null);

  const [composer, setComposer] = useState("");
  const [attachments, setAttachments] = useState([]);
  const [sending, setSending] = useState(false);
  const [sourceFilter, setSourceFilter] = useState("all");
  const [loadingThreads, setLoadingThreads] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState(null);
  const [panelRunId, setPanelRunId] = useState(null);
  const [showMemory, setShowMemory] = useState(false);
  // Shown when orchestrate returns 402 (AI Front Desk tenant hitting the
  // AI Workforce) - a clean upgrade prompt instead of a raw error string.
  const [showUpgrade, setShowUpgrade] = useState(false);

  const scrollRef = useRef(null);
  const composerRef = useRef(null);
  const isMobile = useIsMobile();
  const [railOpen, setRailOpen] = useState(false);

  const capReached = Boolean(usage?.cap_reached);
  const runMap = Object.fromEntries(runs.map((r) => [r.id, r]));
  const hasInFlight = runs.some(
    (r) => r.status === "queued" || r.status === "running",
  );
  const visibleThreads =
    sourceFilter === "all"
      ? threads
      : threads.filter((t) => (t.source || "chat") === sourceFilter);

  const refreshUsage = useCallback(() => {
    if (!token) return;
    fetchOsUsage(token)
      .then(setUsage)
      .catch((err) => console.warn("usage fetch failed:", err.message || err));
  }, [token]);

  // Initial load - threads + usage.
  useEffect(() => {
    if (!token) return;
    let live = true;
    setLoadingThreads(true);
    listOsThreads(token)
      .then((data) => {
        if (!live) return;
        const list = data || [];
        setThreads(list);
        if (list.length) setActiveThreadId(list[0].id);
      })
      .catch((err) => live && setError(err.message || "Failed to load threads"))
      .finally(() => live && setLoadingThreads(false));
    refreshUsage();
    return () => {
      live = false;
    };
  }, [token, refreshUsage]);

  const loadMessages = useCallback(
    (threadId) => {
      if (!token || !threadId) return Promise.resolve();
      return fetchOsThreadMessages(token, threadId)
        .then((data) => {
          setMessages(data?.messages || []);
          setRuns(data?.agent_runs || []);
        })
        .catch((err) => setError(err.message || "Failed to load messages"));
    },
    [token],
  );

  // Load the active thread's messages on switch.
  useEffect(() => {
    if (!activeThreadId) {
      setMessages([]);
      setRuns([]);
      return;
    }
    setLoadingMessages(true);
    setError(null);
    loadMessages(activeThreadId).finally(() => setLoadingMessages(false));
  }, [activeThreadId, loadMessages]);

  // Poll while a run is in flight so the background worker's post-back lands.
  useEffect(() => {
    if (!activeThreadId || !hasInFlight) return;
    const id = setInterval(() => {
      loadMessages(activeThreadId);
    }, POLL_MS);
    return () => clearInterval(id);
  }, [activeThreadId, hasInFlight, loadMessages]);

  // Keep the chat pinned to the latest message.
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, runs]);

  const handleNewThread = async () => {
    if (!token) return;
    try {
      const thread = await createOsThread(token);
      setThreads((prev) => [thread, ...prev]);
      setActiveThreadId(thread.id);
      setComposer("");
      setError(null);
      setRailOpen(false);
    } catch (err) {
      setError(err.message || "Failed to start a conversation");
    }
  };

  const handleSend = async () => {
    let content = composer.trim();
    if (!content || sending || capReached) return;
    // Fold attachments into the message so the AI staff sees them and the
    // thread keeps a durable reference (URLs live in Supabase Storage).
    if (attachments.length > 0) {
      const blocks = attachments.map((a) => {
        let block = `[Attached: ${a.filename} - ${a.public_url}]`;
        if (a.vision_summary) block += `\n[Image description: ${a.vision_summary}]`;
        return block;
      });
      content = `${content}\n\n${blocks.join("\n")}`;
      setAttachments([]);
    }
    setSending(true);
    setError(null);
    try {
      let threadId = activeThreadId;
      if (!threadId) {
        const thread = await createOsThread(token, content.slice(0, 60));
        setThreads((prev) => [thread, ...prev]);
        setActiveThreadId(thread.id);
        threadId = thread.id;
      }
      let result;
      try {
        result = await orchestrateOsTurn(token, threadId, content);
      } catch (err) {
        // Engine route missing (old backend) or unavailable - fall back to the
        // legacy turn endpoint so the dashboard never breaks during rollout.
        if (err.status === 404 || err.status === 503) {
          result = await postOsMessage(token, threadId, content);
        } else {
          throw err;
        }
      }
      setMessages((prev) => [
        ...prev,
        result.user_message,
        result.assistant_message,
        // Connector nudges ("connect HubSpot to do this for real") arrive as
        // extra assistant messages; tolerate their absence.
        ...(result.followup_messages || []),
      ]);
      // The engine runs one agent per turn (agent_run, singular); tolerate the
      // legacy agent_runs array shape too.
      const newRuns =
        result.agent_runs ?? (result.agent_run ? [result.agent_run] : []);
      if (newRuns.length) {
        setRuns((prev) => [...prev, ...newRuns]);
      }
      setComposer("");
      refreshUsage();
    } catch (err) {
      if (err.status === 402) {
        // AI Front Desk plan hitting the AI Workforce - show the upgrade modal.
        setShowUpgrade(true);
      } else if (err.status === 429) {
        setError("Monthly agent-run cap reached for this billing cycle.");
        refreshUsage();
      } else if (err.status === 503) {
        setError("Agent OS engine is not connected yet - try again shortly.");
      } else {
        setError(err.message || "Failed to send message");
      }
    } finally {
      setSending(false);
    }
  };

  const handleComposerKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const panelRun = panelRunId ? runMap[panelRunId] : null;

  const handleRunUpdated = (updated) => {
    if (!updated) return;
    setRuns((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
  };

  return (
    <div
      style={{
        display: "flex",
        height: "calc(100vh - 130px)",
        minHeight: 0,
        border: "1px solid var(--border)",
        borderRadius: 12,
        overflow: "hidden",
        background: "var(--bg-primary)",
      }}
    >
      {/* Thread rail - fixed full-screen overlay on mobile, 240px column on desktop */}
      {isMobile && railOpen && (
        <div
          onClick={() => setRailOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            zIndex: 59,
          }}
        />
      )}
      <aside
        data-tour="thread-rail"
        style={
          isMobile
            ? {
                position: "fixed",
                inset: 0,
                zIndex: 60,
                width: "100%",
                background: "var(--bg-primary)",
                display: railOpen ? "flex" : "none",
                flexDirection: "column",
              }
            : {
                width: 240,
                flexShrink: 0,
                borderRight: "1px solid var(--border)",
                display: "flex",
                flexDirection: "column",
              }
        }
      >
        {isMobile && (
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "12px 14px 8px",
              borderBottom: "1px solid var(--border)",
            }}
          >
            <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>Tasks</span>
            <button
              onClick={() => setRailOpen(false)}
              aria-label="Close task list"
              style={{
                background: "transparent",
                border: "1px solid var(--border)",
                borderRadius: 6,
                padding: "4px 10px",
                color: "var(--text-secondary)",
                cursor: "pointer",
                fontSize: "0.8rem",
              }}
            >
              Close
            </button>
          </div>
        )}
        <div
          style={{
            padding: "14px 14px 10px",
            borderBottom: "1px solid var(--border)",
          }}
        >
          <button
            className="btn-primary"
            onClick={handleNewThread}
            style={{ width: "100%", fontSize: "0.85rem" }}
          >
            New task
          </button>
          <button
            onClick={() => setShowMemory((v) => !v)}
            aria-pressed={showMemory}
            style={{
              width: "100%",
              marginTop: 6,
              fontSize: "0.8rem",
              border: "1px solid var(--border)",
              background: "transparent",
              color: "var(--text-muted)",
              borderRadius: 8,
              padding: "6px 0",
              cursor: "pointer",
            }}
          >
            {showMemory ? "Hide memory" : "Memory"}
          </button>
        </div>
        <div
          role="toolbar"
          aria-label="Filter threads by source"
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 4,
            padding: "8px 8px 4px",
            borderBottom: "1px solid var(--border)",
          }}
        >
          {SOURCE_FILTERS.map((f) => {
            const active = f.key === sourceFilter;
            return (
              <button
                key={f.key}
                onClick={() => setSourceFilter(f.key)}
                aria-pressed={active}
                style={{
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  padding: "3px 8px",
                  fontSize: "0.72rem",
                  fontWeight: active ? 600 : 500,
                  background: active ? "var(--accent-dim)" : "transparent",
                  color: active
                    ? "var(--text-primary)"
                    : "var(--text-secondary)",
                  cursor: "pointer",
                }}
              >
                {f.label}
              </button>
            );
          })}
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: 8 }}>
          {loadingThreads ? (
            <div
              style={{
                padding: 12,
                fontSize: "0.8rem",
                color: "var(--text-muted)",
              }}
            >
              Loading...
            </div>
          ) : threads.length === 0 ? (
            <div
              style={{
                padding: 12,
                fontSize: "0.8rem",
                color: "var(--text-muted)",
                lineHeight: 1.5,
              }}
            >
              No tasks yet. Start one to hand work to the orchestrator.
            </div>
          ) : visibleThreads.length === 0 ? (
            <div
              style={{
                padding: 12,
                fontSize: "0.8rem",
                color: "var(--text-muted)",
                lineHeight: 1.5,
              }}
            >
              No threads match this source filter.
            </div>
          ) : (
            visibleThreads.map((t) => {
              const active = t.id === activeThreadId;
              const sourceKey = t.source || "chat";
              const sourceMeta = SOURCE_META[sourceKey] || SOURCE_META.chat;
              return (
                <button
                  key={t.id}
                  onClick={() => {
                    setActiveThreadId(t.id);
                    if (isMobile) setRailOpen(false);
                  }}
                  style={{
                    display: "block",
                    width: "100%",
                    textAlign: "left",
                    border: "none",
                    borderRadius: 8,
                    padding: "9px 10px",
                    marginBottom: 2,
                    cursor: "pointer",
                    background: active ? "var(--accent-dim)" : "transparent",
                    color: active
                      ? "var(--text-primary)"
                      : "var(--text-secondary)",
                  }}
                >
                  <div
                    style={{
                      fontSize: "0.83rem",
                      fontWeight: active ? 600 : 500,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {t.title || "Untitled task"}
                  </div>
                  <div
                    style={{
                      marginTop: 3,
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                    }}
                  >
                    {sourceMeta.show && (
                      <span
                        data-testid={`thread-source-${t.id}`}
                        style={{
                          fontSize: "0.62rem",
                          fontWeight: 600,
                          letterSpacing: "0.02em",
                          textTransform: "uppercase",
                          color: sourceMeta.color,
                          border: `1px solid ${sourceMeta.color}`,
                          borderRadius: 4,
                          padding: "1px 5px",
                          lineHeight: 1.4,
                        }}
                      >
                        {sourceMeta.label}
                      </span>
                    )}
                    <span
                      style={{
                        fontSize: "0.68rem",
                        color: "var(--text-muted)",
                      }}
                    >
                      {relTime(t.updated_at || t.created_at)}
                    </span>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </aside>

      {/* Chat column */}
      <div
        style={{
          flex: 1,
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {isMobile && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 12px",
              borderBottom: "1px solid var(--border)",
              flexShrink: 0,
            }}
          >
            <button
              onClick={() => setRailOpen(true)}
              aria-label="Open task list"
              style={{
                background: "transparent",
                border: "1px solid var(--border)",
                borderRadius: 6,
                padding: "5px 12px",
                color: "var(--text-secondary)",
                cursor: "pointer",
                fontSize: "0.8rem",
                fontWeight: 500,
              }}
            >
              Tasks
            </button>
            {activeThreadId && threads.length > 0 && (
              <span
                style={{
                  fontSize: "0.8rem",
                  color: "var(--text-muted)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {threads.find((t) => t.id === activeThreadId)?.title ||
                  "Untitled task"}
              </span>
            )}
          </div>
        )}
        {capReached && (
          <div
            style={{
              padding: "10px 16px",
              background: "rgba(245,158,11,0.12)",
              borderBottom: "1px solid rgba(245,158,11,0.3)",
              color: "#f59e0b",
              fontSize: "0.8rem",
              fontWeight: 500,
            }}
          >
            Monthly agent-run cap reached
            {usage?.cap != null ? ` (${usage.agent_runs}/${usage.cap})` : ""}.
            New tasks resume next billing cycle.
          </div>
        )}

        <UsageUpgradeNudge usage={usage} onNavigate={onNavigate} />
        {showUpgrade && (
          <UpgradePrompt
            feature="the AI Workforce"
            requiredPlan="agent_os"
            onClose={() => setShowUpgrade(false)}
            onNavigate={onNavigate}
          />
        )}

        <div
          ref={scrollRef}
          style={{ flex: 1, overflowY: "auto", padding: 20 }}
        >
          {!activeThreadId && (
            <OsInsightsCard token={token} onSuggestion={setComposer} />
          )}
          {error && (
            <div
              style={{
                marginBottom: 14,
                padding: "8px 12px",
                background: "rgba(239,68,68,0.1)",
                border: "1px solid rgba(239,68,68,0.3)",
                borderRadius: 8,
                color: "#ef4444",
                fontSize: "0.8rem",
              }}
            >
              {error}
            </div>
          )}

          {loadingMessages ? (
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
              Loading conversation...
            </div>
          ) : messages.length === 0 ? (
            threads.length === 0 && !activeThreadId ? (
              <FirstRunStarters
                businessType={user?.businessType || ""}
                onSelectPrompt={setComposer}
                composerRef={composerRef}
                isMobile={isMobile}
              />
            ) : (
            <div
              style={{
                height: "100%",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                color: "var(--text-muted)",
                gap: 8,
              }}
            >
              <div
                style={{
                  fontSize: "1.05rem",
                  fontWeight: 600,
                  color: "var(--text-secondary)",
                }}
              >
                Hand a task to the orchestrator
              </div>
              <div
                style={{ fontSize: "0.85rem", maxWidth: 420, lineHeight: 1.6 }}
              >
                Describe what you need. The orchestrator answers directly,
                routes it to a worker agent, or parks it for your decision when
                nothing fits.
              </div>
            </div>
            )
          ) : (
            messages.map((m) => {
              const meta = ROLE_META[m.role] || ROLE_META.assistant;
              const run = m.agent_run_id ? runMap[m.agent_run_id] : null;
              const showFlowchart = m.role === "assistant" && run;
              // The engine writes a single assistant message carrying the run +
              // its deliverable (no separate "agent" message), so gate the
              // Review button on the deliverable itself, not the message role.
              const showDraftButton = Boolean(run && run.deliverable);
              return (
                <div
                  key={m.id}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: meta.align,
                    marginBottom: 14,
                  }}
                >
                  {meta.label && (
                    <span
                      style={{
                        fontSize: "0.68rem",
                        fontWeight: 600,
                        color: "var(--text-muted)",
                        marginBottom: 3,
                      }}
                    >
                      {meta.label}
                    </span>
                  )}
                  <div
                    style={{
                      maxWidth: "78%",
                      background: meta.bg,
                      border: "1px solid var(--border)",
                      borderRadius: 12,
                      padding: "9px 13px",
                      fontSize: "0.86rem",
                      lineHeight: 1.55,
                      color: "var(--text-primary)",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                    }}
                  >
                    {m.content}
                  </div>
                  {showFlowchart && (
                    <div style={{ width: "78%", maxWidth: "78%" }}>
                      <AgentRunFlowchart run={run} />
                    </div>
                  )}
                  {showDraftButton && (
                    <button
                      data-tour="deliverable-panel"
                      onClick={() => setPanelRunId(run.id)}
                      style={{
                        marginTop: 6,
                        background: "transparent",
                        border: "1px solid var(--accent)",
                        borderRadius: 8,
                        padding: "6px 14px",
                        color: "var(--accent)",
                        cursor: "pointer",
                        fontSize: "0.8rem",
                        fontWeight: 600,
                      }}
                    >
                      Review draft
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Composer */}
        <ComposerAttachments
          token={token}
          attachments={attachments}
          setAttachments={setAttachments}
          composerText={composer}
          disabled={sending || capReached}
        />
        <div
          style={{
            borderTop: "1px solid var(--border)",
            padding: 14,
            display: "flex",
            gap: 10,
            alignItems: "flex-end",
          }}
        >
          <textarea
            ref={composerRef}
            value={composer}
            onChange={(e) => setComposer(e.target.value)}
            onKeyDown={handleComposerKey}
            disabled={sending || capReached}
            rows={2}
            placeholder={
              capReached
                ? "Agent-run cap reached for this cycle"
                : "Describe a task for the orchestrator..."
            }
            style={{
              flex: 1,
              resize: "none",
              fontSize: "0.86rem",
              lineHeight: 1.5,
            }}
          />
          <button
            className="btn-primary"
            onClick={handleSend}
            disabled={!composer.trim() || sending || capReached}
            style={{ flexShrink: 0 }}
          >
            {sending ? "Sending..." : "Send"}
          </button>
        </div>
      </div>

      {/* Deliverable side panel */}
      {panelRun && (
        <DeliverablePanel
          run={panelRun}
          token={token}
          onClose={() => setPanelRunId(null)}
          onUpdated={handleRunUpdated}
        />
      )}

      {/* Long-term memory side panel */}
      {showMemory && (
        <MemoryPanel token={token} onClose={() => setShowMemory(false)} />
      )}

      {/* Demo-only guided tour - visible once per session for role=demo */}
      <DemoTour />
    </div>
  );
}
