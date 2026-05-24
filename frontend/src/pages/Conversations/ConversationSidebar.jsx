import { CHANNEL_BADGE } from "./constants";
import { timeAgo, tagPillStyle } from "./utils";

export default function ConversationSidebar({
  conversations,
  filtered,
  selected,
  myCount,
  allTags,
  tagCounts,
  inboxFilter,
  setInboxFilter,
  search,
  setSearch,
  setServerSearch,
  channelFilter,
  setChannelFilter,
  setSelected,
  tagFilter,
  setTagFilter,
  tagColorMap,
  getAssigneeName,
  handleSelect,
}) {
  return (
    <div className="conv-sidebar">
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
            color: inboxFilter === "all" ? "#fff" : "var(--text-secondary)",
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
            color: inboxFilter === "mine" ? "#fff" : "var(--text-secondary)",
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
                    const badge = CHANNEL_BADGE[ch] || CHANNEL_BADGE.widget;
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
                    <span key={tag} style={tagPillStyle(tag, tagColorMap)}>
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
  );
}
