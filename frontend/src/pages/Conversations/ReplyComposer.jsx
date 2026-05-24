import { CHANNEL_BADGE } from "./constants";
import SnippetPicker from "./SnippetPicker";

export default function ReplyComposer({
  selectedConv,
  replyInput,
  handleReplyChange,
  handleReplyKeyDown,
  handleSendReply,
  sendingReply,
  replyTextareaRef,
  snippetPickerRef,
  showSnippetPicker,
  toggleSnippetPicker,
  setShowSnippetPicker,
  snippetSearchRef,
  snippetSearch,
  setSnippetSearch,
  filteredSnippets,
  snippetsLoading,
  snippetsCache,
  insertSnippet,
}) {
  const convChannel = selectedConv?.channel || "widget";
  const badge = CHANNEL_BADGE[convChannel] || CHANNEL_BADGE.widget;

  return (
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
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
        <div style={{ position: "relative" }} ref={snippetPickerRef}>
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
              color: showSnippetPicker ? "#3b82f6" : "var(--text-secondary)",
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

          {showSnippetPicker && (
            <SnippetPicker
              snippetSearchRef={snippetSearchRef}
              snippetSearch={snippetSearch}
              setSnippetSearch={setSnippetSearch}
              setShowSnippetPicker={setShowSnippetPicker}
              replyTextareaRef={replyTextareaRef}
              filteredSnippets={filteredSnippets}
              snippetsLoading={snippetsLoading}
              snippetsCache={snippetsCache}
              insertSnippet={insertSnippet}
            />
          )}
        </div>

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
  );
}
