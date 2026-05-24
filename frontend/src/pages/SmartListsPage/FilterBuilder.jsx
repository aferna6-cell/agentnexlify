import { STATUS_OPTIONS, TEMPERATURE_OPTIONS, emptyFilters } from "./utils";

export default function FilterBuilder({ filters, onChange }) {
  const toggleStatus = (val) => {
    const cur = filters.status || [];
    const next = cur.includes(val)
      ? cur.filter((s) => s !== val)
      : [...cur, val];
    onChange({ ...filters, status: next });
  };

  const set = (key, val) => onChange({ ...filters, [key]: val });

  const clearAll = () => onChange({ ...emptyFilters });

  const hasAnyFilter =
    (filters.status || []).length > 0 ||
    filters.lead_temperature ||
    filters.min_score ||
    filters.max_score ||
    (filters.tags_include || []).length > 0 ||
    filters.assigned_to ||
    filters.created_after ||
    filters.created_before ||
    filters.has_email ||
    filters.has_phone ||
    filters.search;

  const labelStyle = {
    display: "block",
    fontSize: "0.75rem",
    fontWeight: 600,
    color: "var(--text-muted)",
    marginBottom: 6,
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  };

  const rowStyle = { marginBottom: 16 };

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <div
          style={{
            fontSize: "0.85rem",
            fontWeight: 600,
            color: "var(--text-primary)",
          }}
        >
          Filters
        </div>
        {hasAnyFilter && (
          <button
            onClick={clearAll}
            style={{
              background: "none",
              border: "none",
              color: "#ef4444",
              cursor: "pointer",
              fontSize: "0.75rem",
              fontWeight: 600,
              textDecoration: "underline",
            }}
          >
            Clear All
          </button>
        )}
      </div>

      <div style={rowStyle}>
        <label style={labelStyle}>Status</label>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {STATUS_OPTIONS.map((opt) => {
            const checked = (filters.status || []).includes(opt.value);
            return (
              <label
                key={opt.value}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  cursor: "pointer",
                  fontSize: "0.8rem",
                  color: checked
                    ? "var(--text-primary)"
                    : "var(--text-secondary)",
                  padding: "4px 8px",
                  borderRadius: 6,
                  background: checked ? "var(--accent-dim)" : "transparent",
                  border: checked
                    ? "1px solid var(--accent)"
                    : "1px solid var(--border)",
                  transition: "all 0.15s ease",
                }}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleStatus(opt.value)}
                  style={{ width: "auto", margin: 0 }}
                />
                {opt.label}
              </label>
            );
          })}
        </div>
      </div>

      <div style={rowStyle}>
        <label style={labelStyle}>Temperature</label>
        <select
          value={filters.lead_temperature || ""}
          onChange={(e) => set("lead_temperature", e.target.value)}
          style={{ width: "100%", fontSize: "0.85rem" }}
        >
          {TEMPERATURE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div
        style={{
          ...rowStyle,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 10,
        }}
      >
        <div>
          <label style={labelStyle}>Min Score</label>
          <input
            type="number"
            min={0}
            max={100}
            value={filters.min_score || ""}
            onChange={(e) => set("min_score", e.target.value)}
            placeholder="0"
            style={{ width: "100%", fontSize: "0.85rem" }}
          />
        </div>
        <div>
          <label style={labelStyle}>Max Score</label>
          <input
            type="number"
            min={0}
            max={100}
            value={filters.max_score || ""}
            onChange={(e) => set("max_score", e.target.value)}
            placeholder="100"
            style={{ width: "100%", fontSize: "0.85rem" }}
          />
        </div>
      </div>

      <div style={rowStyle}>
        <label style={labelStyle}>Tags (comma-separated)</label>
        <input
          type="text"
          value={(filters.tags_include || []).join(", ")}
          onChange={(e) =>
            set(
              "tags_include",
              e.target.value
                ? e.target.value
                    .split(",")
                    .map((t) => t.trim())
                    .filter(Boolean)
                : [],
            )
          }
          placeholder="e.g. interested, follow-up"
          style={{ width: "100%", fontSize: "0.85rem" }}
        />
      </div>

      <div style={rowStyle}>
        <label style={labelStyle}>Assigned To</label>
        <input
          type="text"
          value={filters.assigned_to || ""}
          onChange={(e) => set("assigned_to", e.target.value)}
          placeholder='Name or "Unassigned"'
          style={{ width: "100%", fontSize: "0.85rem" }}
        />
      </div>

      <div
        style={{
          ...rowStyle,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 10,
        }}
      >
        <div>
          <label style={labelStyle}>Created After</label>
          <input
            type="date"
            value={filters.created_after || ""}
            onChange={(e) => set("created_after", e.target.value)}
            style={{ width: "100%", fontSize: "0.85rem" }}
          />
        </div>
        <div>
          <label style={labelStyle}>Created Before</label>
          <input
            type="date"
            value={filters.created_before || ""}
            onChange={(e) => set("created_before", e.target.value)}
            style={{ width: "100%", fontSize: "0.85rem" }}
          />
        </div>
      </div>

      <div style={{ ...rowStyle, display: "flex", gap: 20 }}>
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            cursor: "pointer",
            fontSize: "0.85rem",
            color: "var(--text-secondary)",
          }}
        >
          <input
            type="checkbox"
            checked={!!filters.has_email}
            onChange={(e) => set("has_email", e.target.checked)}
            style={{ width: "auto", margin: 0 }}
          />
          Has Email
        </label>
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            cursor: "pointer",
            fontSize: "0.85rem",
            color: "var(--text-secondary)",
          }}
        >
          <input
            type="checkbox"
            checked={!!filters.has_phone}
            onChange={(e) => set("has_phone", e.target.checked)}
            style={{ width: "auto", margin: 0 }}
          />
          Has Phone
        </label>
      </div>

      <div style={rowStyle}>
        <label style={labelStyle}>Search (name / email / phone)</label>
        <input
          type="text"
          value={filters.search || ""}
          onChange={(e) => set("search", e.target.value)}
          placeholder="Keyword search..."
          style={{ width: "100%", fontSize: "0.85rem" }}
        />
      </div>
    </div>
  );
}
