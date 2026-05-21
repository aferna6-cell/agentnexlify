/**
 * Agent OS — chat-first orchestrator shell (P0).
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
  postOsMessage,
  fetchOsUsage,
} from "../utils/api/os";
import AgentRunFlowchart from "../components/os/AgentRunFlowchart";
import DeliverablePanel from "../components/os/DeliverablePanel";

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

export default function AgentOS() {
  const { token } = useAuth();

  const [threads, setThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [runs, setRuns] = useState([]);
  const [usage, setUsage] = useState(null);

  const [composer, setComposer] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingThreads, setLoadingThreads] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState(null);
  const [panelRunId, setPanelRunId] = useState(null);

  const scrollRef = useRef(null);

  const capReached = Boolean(usage?.cap_reached);
  const runMap = Object.fromEntries(runs.map((r) => [r.id, r]));
  const hasInFlight = runs.some(
    (r) => r.status === "queued" || r.status === "running",
  );

  const refreshUsage = useCallback(() => {
    if (!token) return;
    fetchOsUsage(token)
      .then(setUsage)
      .catch((err) => console.warn("usage fetch failed:", err.message || err));
  }, [token]);

  // Initial load — threads + usage.
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
    } catch (err) {
      setError(err.message || "Failed to start a conversation");
    }
  };

  const handleSend = async () => {
    const content = composer.trim();
    if (!content || sending || capReached) return;
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
      const result = await postOsMessage(token, threadId, content);
      setMessages((prev) => [
        ...prev,
        result.user_message,
        result.assistant_message,
      ]);
      if (result.agent_runs?.length) {
        setRuns((prev) => [...prev, ...result.agent_runs]);
      }
      setComposer("");
      refreshUsage();
    } catch (err) {
      if (err.status === 429) {
        setError("Monthly agent-run cap reached for this billing cycle.");
        refreshUsage();
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
      {/* Thread rail */}
      <aside
        style={{
          width: 240,
          flexShrink: 0,
          borderRight: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
        }}
      >
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
          ) : (
            threads.map((t) => {
              const active = t.id === activeThreadId;
              return (
                <button
                  key={t.id}
                  onClick={() => setActiveThreadId(t.id)}
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
                    style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}
                  >
                    {relTime(t.updated_at || t.created_at)}
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

        <div
          ref={scrollRef}
          style={{ flex: 1, overflowY: "auto", padding: 20 }}
        >
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
          ) : (
            messages.map((m) => {
              const meta = ROLE_META[m.role] || ROLE_META.assistant;
              const run = m.agent_run_id ? runMap[m.agent_run_id] : null;
              const showFlowchart = m.role === "assistant" && run;
              const showDraftButton =
                m.role === "agent" && run && run.deliverable;
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
    </div>
  );
}
