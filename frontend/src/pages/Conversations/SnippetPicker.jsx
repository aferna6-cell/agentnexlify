import { SNIPPET_CATEGORY_COLORS } from "./constants";

export default function SnippetPicker({
  snippetSearchRef,
  snippetSearch,
  setSnippetSearch,
  setShowSnippetPicker,
  replyTextareaRef,
  filteredSnippets,
  snippetsLoading,
  snippetsCache,
  insertSnippet,
}) {
  return (
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
            if (e.key === "Enter" && filteredSnippets.length > 0) {
              e.preventDefault();
              insertSnippet(filteredSnippets[0]);
            }
          }}
        />
      </div>

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
            const catKey = (snippet.category || "general").toLowerCase();
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
                  e.currentTarget.style.background = "var(--bg-secondary)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
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
                        background: "var(--accent-dim, rgba(0,191,255,0.1))",
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
  );
}
