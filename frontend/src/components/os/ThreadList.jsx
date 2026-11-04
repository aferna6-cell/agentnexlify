/**
 * Task list for Agent OS. Repeated scheduled runs collapse into one row.
 * Titles wrap so the full name stays readable, and a search box filters them.
 */
import { useMemo, useState } from "react";
import { filterThreads, groupThreads } from "./threadRail";

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

const titleStyle = {
  fontSize: "0.83rem",
  whiteSpace: "normal",
  overflow: "visible",
  wordBreak: "break-word",
  lineHeight: 1.35,
};

export default function ThreadList({
  threads,
  activeThreadId,
  onSelect,
  sourceMetaFor,
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState({});
  const items = useMemo(
    () => groupThreads(filterThreads(threads, query)),
    [threads, query],
  );

  return (
    <div>
      <label style={{ display: "block", padding: "0 2px 8px" }}>
        <span className="sr-only" style={srOnly}>
          Search tasks
        </span>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search tasks"
          aria-label="Search tasks"
          style={{
            width: "100%",
            boxSizing: "border-box",
            background: "var(--bg-primary)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            color: "var(--text-primary)",
            padding: "7px 9px",
            fontSize: "0.8rem",
          }}
        />
      </label>
      {items.length === 0 ? (
        <div
          style={{
            padding: 12,
            fontSize: "0.8rem",
            color: "var(--text-muted)",
          }}
        >
          No tasks match that search.
        </div>
      ) : (
        items.map((item) => {
          if (item.kind === "group" && item.threads.length > 1) {
            const expanded = Boolean(open[item.key]);
            return (
              <div key={item.key} style={{ marginBottom: 4 }}>
                <button
                  type="button"
                  aria-expanded={expanded}
                  onClick={() =>
                    setOpen((prev) => ({ ...prev, [item.key]: !expanded }))
                  }
                  style={rowStyle(false)}
                >
                  <div
                    style={{
                      ...titleStyle,
                      fontWeight: 600,
                      color: "var(--text-primary)",
                    }}
                  >
                    {item.title}
                  </div>
                  <div
                    style={{
                      marginTop: 3,
                      fontSize: "0.68rem",
                      color: "var(--text-muted)",
                    }}
                  >
                    {item.threads.length} scheduled runs
                  </div>
                </button>
                {expanded &&
                  item.threads.map((thread) => (
                    <ThreadButton
                      key={thread.id}
                      thread={thread}
                      active={thread.id === activeThreadId}
                      onSelect={onSelect}
                      sourceMetaFor={sourceMetaFor}
                      nested
                    />
                  ))}
              </div>
            );
          }
          const thread = item.kind === "group" ? item.threads[0] : item.thread;
          return (
            <ThreadButton
              key={thread.id}
              thread={thread}
              title={item.title}
              active={thread.id === activeThreadId}
              onSelect={onSelect}
              sourceMetaFor={sourceMetaFor}
            />
          );
        })
      )}
    </div>
  );
}

function ThreadButton({
  thread,
  title,
  active,
  onSelect,
  sourceMetaFor,
  nested,
}) {
  const sourceKey = thread.source || "chat";
  const sourceMeta = sourceMetaFor ? sourceMetaFor(sourceKey) : null;
  return (
    <button
      type="button"
      onClick={() => onSelect(thread.id)}
      style={rowStyle(active, nested)}
    >
      <div
        style={{
          ...titleStyle,
          fontWeight: active ? 600 : 500,
          color: active ? "var(--text-primary)" : "var(--text-secondary)",
        }}
      >
        {title || thread.title || "Untitled task"}
      </div>
      <div
        style={{ marginTop: 3, display: "flex", alignItems: "center", gap: 6 }}
      >
        {sourceMeta?.show && (
          <span
            data-testid={`thread-source-${thread.id}`}
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
        <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>
          {relTime(thread.updated_at || thread.created_at)}
        </span>
      </div>
    </button>
  );
}

function rowStyle(active, nested) {
  return {
    display: "block",
    width: nested ? "calc(100% - 12px)" : "100%",
    marginLeft: nested ? 12 : 0,
    textAlign: "left",
    border: "none",
    borderRadius: 8,
    padding: "9px 10px",
    marginBottom: 2,
    cursor: "pointer",
    background: active ? "var(--accent-dim)" : "transparent",
    color: active ? "var(--text-primary)" : "var(--text-secondary)",
  };
}

const srOnly = {
  position: "absolute",
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: "hidden",
  clip: "rect(0,0,0,0)",
  border: 0,
};
