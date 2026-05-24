export default function ConversationToolbar({
  selectedConv,
  selected,
  teamMembers,
  assigning,
  handleAssign,
  tagInput,
  setTagInput,
  addTag,
  removeTag,
  tagColorMap,
  showNotes,
  notes,
  toggleNotes,
  showLeadNote,
  setShowLeadNote,
  messages,
  exportConversation,
}) {
  return (
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
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
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

        <span
          style={{
            width: 1,
            height: 16,
            background: "var(--border)",
            flexShrink: 0,
          }}
        />

        {(selectedConv?.tags || []).map((tag) => {
          const color = tagColorMap[tag] || null;
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
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <button
          className="btn-sm"
          onClick={toggleNotes}
          style={{
            background: showNotes ? "rgba(139,92,246,0.15)" : undefined,
            color: showNotes ? "rgba(167,139,250,1)" : undefined,
            borderColor: showNotes ? "rgba(139,92,246,0.3)" : undefined,
          }}
        >
          Notes {notes.length > 0 ? `(${notes.length})` : ""}
        </button>
        {selectedConv?.lead_id && (
          <button
            className="btn-sm"
            onClick={() => setShowLeadNote(!showLeadNote)}
            style={{
              background: showLeadNote ? "rgba(16,185,129,0.15)" : undefined,
              color: showLeadNote ? "#10b981" : undefined,
              borderColor: showLeadNote ? "rgba(16,185,129,0.3)" : undefined,
            }}
            title="Add a note to the linked lead"
          >
            Lead Note
          </button>
        )}
        {messages.length > 0 && (
          <button className="btn-sm" onClick={exportConversation}>
            Export
          </button>
        )}
      </div>
    </div>
  );
}
