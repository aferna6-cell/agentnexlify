export default function ListSidebar({
  smartLists,
  selectedListId,
  deletingId,
  refreshingId,
  onSelect,
  onRefresh,
  onEdit,
  onDelete,
}) {
  return (
    <div
      style={{
        background: "var(--bg-secondary)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "14px 16px",
          borderBottom: "1px solid var(--border)",
          fontSize: "0.8rem",
          fontWeight: 600,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span>Your Lists ({smartLists.length})</span>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "8px" }}>
        {smartLists.length === 0 ? (
          <div
            style={{
              padding: "24px 12px",
              textAlign: "center",
              color: "var(--text-muted)",
              fontSize: "0.8rem",
              lineHeight: 1.6,
            }}
          >
            No smart lists yet. Create one to start segmenting your leads by
            filters like status, temperature, or score.
          </div>
        ) : (
          smartLists.map((list) => {
            const isSelected = selectedListId === list.id;
            const isDeleting = deletingId === list.id;
            const isRefreshing = refreshingId === list.id;

            return (
              <div
                key={list.id}
                onClick={() => onSelect(list.id)}
                style={{
                  padding: "10px 12px",
                  borderRadius: 8,
                  cursor: "pointer",
                  background: isSelected ? "var(--accent-dim)" : "transparent",
                  border: isSelected
                    ? "1px solid var(--accent)"
                    : "1px solid transparent",
                  marginBottom: 4,
                  opacity: isDeleting ? 0.4 : 1,
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={(e) => {
                  if (!isSelected)
                    e.currentTarget.style.background = "var(--hover-overlay)";
                }}
                onMouseLeave={(e) => {
                  if (!isSelected)
                    e.currentTarget.style.background = "transparent";
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 2,
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.85rem",
                      fontWeight: isSelected ? 700 : 500,
                      color: isSelected
                        ? "var(--accent)"
                        : "var(--text-primary)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      flex: 1,
                    }}
                  >
                    {list.name}
                  </span>
                  <span
                    style={{
                      fontSize: "0.7rem",
                      fontWeight: 700,
                      color: isSelected ? "var(--accent)" : "var(--text-muted)",
                      background: isSelected
                        ? "rgba(99,102,241,0.15)"
                        : "var(--hover-overlay)",
                      padding: "2px 8px",
                      borderRadius: 10,
                      minWidth: 28,
                      textAlign: "center",
                      flexShrink: 0,
                      marginLeft: 8,
                    }}
                  >
                    {isRefreshing ? "..." : (list.cached_lead_count ?? "?")}
                  </span>
                </div>
                {list.description && (
                  <div
                    style={{
                      fontSize: "0.72rem",
                      color: "var(--text-muted)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {list.description}
                  </div>
                )}

                {isSelected && (
                  <div
                    style={{ display: "flex", gap: 6, marginTop: 8 }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      onClick={() => onRefresh(list.id)}
                      disabled={isRefreshing}
                      style={{
                        background: "none",
                        border: "1px solid var(--border)",
                        borderRadius: 4,
                        padding: "2px 8px",
                        color: "var(--text-secondary)",
                        cursor: "pointer",
                        fontSize: "0.7rem",
                      }}
                    >
                      {isRefreshing ? "..." : "Refresh"}
                    </button>
                    <button
                      onClick={() => onEdit(list)}
                      style={{
                        background: "none",
                        border: "1px solid var(--border)",
                        borderRadius: 4,
                        padding: "2px 8px",
                        color: "var(--accent)",
                        cursor: "pointer",
                        fontSize: "0.7rem",
                      }}
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => onDelete(list.id)}
                      disabled={isDeleting}
                      style={{
                        background: "none",
                        border: "1px solid var(--border)",
                        borderRadius: 4,
                        padding: "2px 8px",
                        color: "#ef4444",
                        cursor: "pointer",
                        fontSize: "0.7rem",
                      }}
                    >
                      {isDeleting ? "..." : "Delete"}
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
