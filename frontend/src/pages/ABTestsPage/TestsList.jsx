import StatusBadge from "./StatusBadge";
import { btnPrimary, btnSecondary, formatDate } from "./utils";

export default function TestsList({
  tests,
  onSelect,
  onStart,
  onComplete,
  onDelete,
}) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table
        style={{
          width: "100%",
          borderCollapse: "separate",
          borderSpacing: 0,
          background: "var(--bg-secondary, var(--card-bg))",
          border: "1px solid var(--border)",
          borderRadius: 12,
          overflow: "hidden",
        }}
      >
        <thead>
          <tr>
            {["Name", "Type", "Status", "Variants", "Started", "Actions"].map(
              (h) => (
                <th
                  key={h}
                  style={{
                    textAlign: "left",
                    padding: "12px 16px",
                    fontSize: "0.8rem",
                    color: "var(--text-muted)",
                    fontWeight: 600,
                    borderBottom: "1px solid var(--border)",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  {h}
                </th>
              ),
            )}
          </tr>
        </thead>
        <tbody>
          {tests.map((t) => (
            <tr
              key={t.id}
              onClick={() => onSelect(t)}
              style={{ cursor: "pointer", transition: "background 0.15s" }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = "var(--hover-overlay)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "transparent")
              }
            >
              <td
                style={{
                  padding: "12px 16px",
                  color: "var(--text-primary)",
                  fontWeight: 600,
                }}
              >
                {t.name || "Untitled Test"}
              </td>
              <td
                style={{
                  padding: "12px 16px",
                  color: "var(--text-secondary)",
                  fontSize: "0.85rem",
                  textTransform: "capitalize",
                }}
              >
                {t.test_type?.replace("_", " ") || "-"}
              </td>
              <td style={{ padding: "12px 16px" }}>
                <StatusBadge status={t.status} />
              </td>
              <td
                style={{
                  padding: "12px 16px",
                  color: "var(--text-secondary)",
                }}
              >
                {t.variants?.length ||
                  t.variant_count ||
                  t.ab_test_variants?.length ||
                  0}
              </td>
              <td
                style={{
                  padding: "12px 16px",
                  fontSize: "0.85rem",
                  color: "var(--text-muted)",
                }}
              >
                {formatDate(t.started_at)}
              </td>
              <td style={{ padding: "12px 16px" }}>
                <div style={{ display: "flex", gap: 6 }}>
                  {t.status === "draft" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onStart(t.id);
                      }}
                      style={{
                        ...btnPrimary,
                        padding: "4px 10px",
                        fontSize: "0.75rem",
                      }}
                    >
                      Start
                    </button>
                  )}
                  {t.status === "running" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onComplete(t.id);
                      }}
                      style={{
                        ...btnSecondary,
                        padding: "4px 10px",
                        fontSize: "0.75rem",
                      }}
                    >
                      Complete
                    </button>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(t.id);
                    }}
                    style={{
                      background: "none",
                      border: "1px solid var(--border)",
                      color: "var(--text-muted)",
                      padding: "4px 10px",
                      borderRadius: 6,
                      cursor: "pointer",
                      fontSize: "0.75rem",
                    }}
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
