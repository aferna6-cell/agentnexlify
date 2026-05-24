export default function LeadNotePanel({
  selectedConv,
  leadNoteInput,
  setLeadNoteInput,
  addingLeadNote,
  leadNoteSuccess,
  handleAddLeadNote,
  setShowLeadNote,
}) {
  if (!selectedConv?.lead_id) return null;

  return (
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
            {selectedConv.lead_name || "Lead"}
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
  );
}
