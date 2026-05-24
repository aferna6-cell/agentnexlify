import { STAGES } from "../Dashboard/LeadPipeline";

export default function BulkActionBar({
  selectedCount,
  view,
  bulkAction,
  onBulkActionChange,
  teamMembers,
  bulkRunning,
  onApply,
  onClear,
  bulkResult,
  onDismissResult,
}) {
  return (
    <>
      {selectedCount > 0 && view === "table" && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "10px 16px",
            marginBottom: 12,
            borderRadius: 10,
            background: "rgba(0,191,255,0.08)",
            border: "1px solid rgba(0,191,255,0.25)",
          }}
        >
          <span
            style={{
              fontWeight: 600,
              fontSize: 13,
              color: "var(--accent, #00BFFF)",
            }}
          >
            {selectedCount} selected
          </span>
          <select
            value={bulkAction}
            onChange={(e) => onBulkActionChange(e.target.value)}
            style={{
              background: "var(--bg-secondary)",
              color: "var(--text-primary)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: "5px 10px",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            <option value="">Choose action...</option>
            <optgroup label="Change Stage">
              {STAGES.map((s) => (
                <option key={s.key} value={`status:${s.key}`}>
                  {s.label}
                </option>
              ))}
            </optgroup>
            <optgroup label="Assign To">
              <option value="assign:">Unassign</option>
              {teamMembers.map((m) => (
                <option key={m.id} value={`assign:${m.id}`}>
                  {m.name || m.email}
                </option>
              ))}
            </optgroup>
            <option value="delete" style={{ color: "#ef4444" }}>
              Delete selected
            </option>
          </select>
          <button
            onClick={onApply}
            disabled={!bulkAction || bulkRunning}
            style={{
              background:
                bulkAction === "delete" ? "#ef4444" : "var(--accent, #00BFFF)",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              padding: "6px 16px",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              opacity: !bulkAction || bulkRunning ? 0.5 : 1,
            }}
          >
            {bulkRunning
              ? "Updating..."
              : bulkAction === "delete"
                ? "Delete"
                : "Apply"}
          </button>
          <button
            onClick={onClear}
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: 12,
              textDecoration: "underline",
            }}
          >
            Clear selection
          </button>
        </div>
      )}

      {bulkResult && (
        <div
          style={{
            marginBottom: 12,
            padding: "8px 14px",
            borderRadius: 8,
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            fontSize: 13,
          }}
        >
          Bulk update: {bulkResult.updated} updated
          {bulkResult.failed > 0 && `, ${bulkResult.failed} failed`}
          <button
            onClick={onDismissResult}
            style={{
              marginLeft: 12,
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            dismiss
          </button>
        </div>
      )}
    </>
  );
}
