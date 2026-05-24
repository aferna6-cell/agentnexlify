import { SOURCE_TYPES, TONES, FORMAT_OPTIONS } from "./constants";

export default function InputPanel({
  sourceType,
  setSourceType,
  sourceInput,
  setSourceInput,
  tone,
  setTone,
  formats,
  toggleFormat,
  creating,
  onCreate,
}) {
  const sourceConfig =
    SOURCE_TYPES.find((s) => s.key === sourceType) || SOURCE_TYPES[0];

  return (
    <div
      style={{
        background: "var(--card-bg)",
        borderRadius: 12,
        border: "1px solid var(--border)",
        padding: 20,
      }}
    >
      <div style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: 16 }}>
        Repurpose Content
      </div>

      <div
        style={{
          display: "flex",
          gap: 4,
          marginBottom: 12,
          flexWrap: "wrap",
        }}
      >
        {SOURCE_TYPES.map((s) => (
          <button
            key={s.key}
            onClick={() => setSourceType(s.key)}
            style={{
              padding: "6px 12px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              cursor: "pointer",
              fontSize: "0.8rem",
              background:
                sourceType === s.key ? "var(--accent)" : "transparent",
              color: sourceType === s.key ? "#fff" : "var(--text-secondary)",
            }}
          >
            {s.icon} {s.label}
          </button>
        ))}
      </div>

      {sourceType === "url" || sourceType === "youtube" ? (
        <input
          type="url"
          value={sourceInput}
          onChange={(e) => setSourceInput(e.target.value)}
          placeholder={sourceConfig.placeholder}
          style={{
            width: "100%",
            padding: "10px 12px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: "var(--input-bg)",
            color: "var(--text-primary)",
            fontSize: "0.9rem",
            marginBottom: 12,
          }}
        />
      ) : (
        <textarea
          value={sourceInput}
          onChange={(e) => setSourceInput(e.target.value)}
          placeholder={sourceConfig.placeholder}
          rows={6}
          style={{
            width: "100%",
            padding: "10px 12px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: "var(--input-bg)",
            color: "var(--text-primary)",
            fontSize: "0.9rem",
            resize: "vertical",
            marginBottom: 12,
          }}
        />
      )}

      <div style={{ marginBottom: 12 }}>
        <label
          style={{
            fontSize: "0.8rem",
            color: "var(--text-secondary)",
            marginBottom: 4,
            display: "block",
          }}
        >
          Tone
        </label>
        <select
          value={tone}
          onChange={(e) => setTone(e.target.value)}
          style={{
            width: "100%",
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: "var(--input-bg)",
            color: "var(--text-primary)",
            fontSize: "0.85rem",
          }}
        >
          {TONES.map((t) => (
            <option key={t.key} value={t.key}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label
          style={{
            fontSize: "0.8rem",
            color: "var(--text-secondary)",
            marginBottom: 6,
            display: "block",
          }}
        >
          Output Formats
        </label>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {FORMAT_OPTIONS.map((f) => (
            <label
              key={f.key}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: "0.85rem",
                color: "var(--text-primary)",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={formats.includes(f.key)}
                onChange={() => toggleFormat(f.key)}
              />
              {f.label}
            </label>
          ))}
        </div>
      </div>

      <button
        className="btn-primary"
        onClick={onCreate}
        disabled={!sourceInput.trim() || creating || formats.length === 0}
        style={{ width: "100%" }}
      >
        {creating ? "Repurposing..." : "Repurpose"}
      </button>
    </div>
  );
}
