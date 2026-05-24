import { formatNoteTime } from "./utils";

export default function InternalNotesPanel({
  notes,
  loadingNotes,
  noteInput,
  setNoteInput,
  addingNote,
  toggleNotes,
  handleAddNote,
  handleDeleteNote,
}) {
  return (
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
          No internal notes yet. Use notes to share context with your team about
          this conversation.
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
                    {note.author_name || note.author_email || "Team Member"}
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
  );
}
