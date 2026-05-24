import { useState } from "react";
import { catColors } from "./constants";
import { btnSecondary } from "./styles";

export default function TemplatePicker({
  templates,
  starterTemplates,
  onSelect,
  onClose,
}) {
  const [filter, setFilter] = useState("all");
  const all = [
    ...(starterTemplates || []).map((t) => ({ ...t, _src: "built-in" })),
    ...(templates || []).map((t) => ({ ...t, _src: "custom" })),
  ];
  const filtered =
    filter === "all" ? all : all.filter((t) => t.category === filter);
  const cats = [
    "all",
    "welcome",
    "follow_up",
    "reminder",
    "review",
    "promotion",
    "custom",
  ];

  return (
    <div
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-sm)",
        padding: "14px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "10px",
        }}
      >
        <span
          style={{
            color: "var(--text-primary)",
            fontWeight: 600,
            fontSize: "13px",
          }}
        >
          Choose a Template
        </span>
        <button
          onClick={onClose}
          style={{ ...btnSecondary, padding: "2px 8px", fontSize: "14px" }}
        >
          &times;
        </button>
      </div>
      <div
        style={{
          display: "flex",
          gap: "5px",
          flexWrap: "wrap",
          marginBottom: "10px",
        }}
      >
        {cats.map((c) => (
          <button
            key={c}
            onClick={() => setFilter(c)}
            style={{
              padding: "3px 9px",
              background: filter === c ? "var(--accent)" : "var(--bg-primary)",
              color:
                filter === c
                  ? "var(--accent-contrast)"
                  : "var(--text-secondary)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              fontSize: "11px",
              textTransform: "capitalize",
            }}
          >
            {c === "follow_up" ? "Follow-Up" : c}
          </button>
        ))}
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: "8px",
          maxHeight: "240px",
          overflowY: "auto",
        }}
      >
        {filtered.map((t) => (
          <div
            key={t.id}
            onClick={() => onSelect(t)}
            style={{
              background: "var(--bg-primary)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
              padding: "10px",
              cursor: "pointer",
              transition: "border-color 0.15s",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.borderColor = "var(--accent)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.borderColor = "var(--border)")
            }
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "5px",
                marginBottom: "4px",
              }}
            >
              <span
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  background: catColors[t.category] || catColors.custom,
                  flexShrink: 0,
                }}
              />
              <span
                style={{
                  fontSize: "10px",
                  color: "var(--text-muted)",
                  textTransform: "capitalize",
                }}
              >
                {t.category === "follow_up" ? "Follow-Up" : t.category}
              </span>
              {t._src === "built-in" && (
                <span
                  style={{
                    fontSize: "9px",
                    color: "var(--text-muted)",
                    marginLeft: "auto",
                  }}
                >
                  Built-in
                </span>
              )}
            </div>
            <div
              style={{
                color: "var(--text-primary)",
                fontSize: "12px",
                fontWeight: 600,
                marginBottom: "2px",
              }}
            >
              {t.name}
            </div>
            <div
              style={{
                color: "var(--text-muted)",
                fontSize: "11px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {t.subject_template || "(no subject)"}
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div
            style={{
              color: "var(--text-muted)",
              fontSize: "12px",
              padding: "16px",
              textAlign: "center",
              gridColumn: "1 / -1",
            }}
          >
            No templates in this category
          </div>
        )}
      </div>
    </div>
  );
}
