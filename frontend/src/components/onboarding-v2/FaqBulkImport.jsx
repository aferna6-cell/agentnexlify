import { useState, useRef } from "react";

const MAX_CSV_ROWS = 200;

function parseLines(text) {
  const lines = text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  if (lines.length % 2 !== 0) {
    throw new Error(
      `Odd number of lines (${lines.length}) — need Q/A pairs. Each question must be followed by an answer.`,
    );
  }
  const faqs = [];
  for (let i = 0; i < lines.length; i += 2) {
    faqs.push({ q: lines[i], a: lines[i + 1] });
  }
  return faqs;
}

function parseCsv(text) {
  const lines = text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  let warn = null;
  let rows = lines;
  if (rows.length > MAX_CSV_ROWS) {
    warn = `Only the first ${MAX_CSV_ROWS} rows imported (${rows.length} found).`;
    rows = rows.slice(0, MAX_CSV_ROWS);
  }

  const faqs = rows.map((line) => {
    const commaIdx = line.indexOf(",");
    if (commaIdx === -1) return { q: line, a: "" };
    return {
      q: line.slice(0, commaIdx).replace(/^"|"$/g, "").trim(),
      a: line
        .slice(commaIdx + 1)
        .replace(/^"|"$/g, "")
        .trim(),
    };
  });

  return { faqs, warn };
}

export default function FaqBulkImport({ onImport }) {
  const [tab, setTab] = useState("paste");
  const [pasteText, setPasteText] = useState("");
  const [error, setError] = useState(null);
  const [warn, setWarn] = useState(null);
  const fileRef = useRef(null);

  function handlePasteImport() {
    setError(null);
    setWarn(null);
    try {
      const faqs = parseLines(pasteText);
      if (faqs.length === 0) {
        setError(
          "No Q/A pairs found. Paste questions and answers on alternating lines.",
        );
        return;
      }
      onImport(faqs);
      setPasteText("");
    } catch (e) {
      setError(e.message);
    }
  }

  function handleFileChange(e) {
    setError(null);
    setWarn(null);
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const { faqs, warn: w } = parseCsv(ev.target.result);
        if (w) setWarn(w);
        onImport(faqs);
        if (fileRef.current) fileRef.current.value = "";
      } catch (err) {
        setError(err.message);
      }
    };
    reader.readAsText(file);
  }

  return (
    <div>
      {/* Tab bar */}
      <div
        style={{
          display: "flex",
          gap: 0,
          marginBottom: 16,
          background: "rgba(255,255,255,0.04)",
          borderRadius: 8,
          padding: 3,
        }}
      >
        {[
          { key: "paste", label: "Paste lines" },
          { key: "csv", label: "CSV upload" },
        ].map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => {
              setTab(t.key);
              setError(null);
              setWarn(null);
            }}
            style={{
              flex: 1,
              padding: "8px 0",
              minHeight: 44,
              border: "none",
              borderRadius: 6,
              background:
                tab === t.key ? "rgba(99, 102, 241, 0.25)" : "transparent",
              color: tab === t.key ? "#a5b4fc" : "rgba(255,255,255,0.45)",
              fontWeight: tab === t.key ? 600 : 400,
              fontSize: "0.85rem",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && (
        <div
          style={{
            background: "rgba(220, 38, 38, 0.15)",
            border: "1px solid rgba(220, 38, 38, 0.3)",
            color: "#fca5a5",
            padding: "10px 14px",
            borderRadius: 8,
            fontSize: "0.85rem",
            marginBottom: 12,
          }}
        >
          {error}
        </div>
      )}

      {warn && (
        <div
          style={{
            background: "rgba(234, 179, 8, 0.1)",
            border: "1px solid rgba(234, 179, 8, 0.25)",
            color: "#fde68a",
            padding: "10px 14px",
            borderRadius: 8,
            fontSize: "0.85rem",
            marginBottom: 12,
          }}
        >
          {warn}
        </div>
      )}

      {tab === "paste" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <p
            style={{
              fontSize: "0.8rem",
              color: "rgba(255,255,255,0.4)",
              margin: 0,
            }}
          >
            Paste alternating lines: first line = question, next line = answer,
            repeat.
          </p>
          <textarea
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            placeholder={
              "Do you offer free estimates?\nYes, we offer free estimates for all services.\nWhat areas do you serve?\nWe serve Austin and surrounding areas within 30 miles."
            }
            rows={8}
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 8,
              padding: "10px 14px",
              color: "#e2e8f0",
              fontSize: "0.85rem",
              resize: "vertical",
              width: "100%",
              boxSizing: "border-box",
              fontFamily: "inherit",
              minHeight: 160,
            }}
          />
          <button
            type="button"
            onClick={handlePasteImport}
            style={importBtnStyle}
          >
            Import
          </button>
        </div>
      )}

      {tab === "csv" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <p
            style={{
              fontSize: "0.8rem",
              color: "rgba(255,255,255,0.4)",
              margin: 0,
            }}
          >
            Upload a .csv file. Column 1 = question, column 2 = answer. Max{" "}
            {MAX_CSV_ROWS} rows.
          </p>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 80,
              border: "2px dashed rgba(255,255,255,0.15)",
              borderRadius: 10,
              cursor: "pointer",
              color: "rgba(255,255,255,0.4)",
              fontSize: "0.85rem",
              gap: 8,
            }}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
            </svg>
            Choose CSV file
            <input
              ref={fileRef}
              type="file"
              accept=".csv,text/csv"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />
          </label>
        </div>
      )}
    </div>
  );
}

const importBtnStyle = {
  padding: "12px 0",
  minHeight: 44,
  width: "100%",
  background: "rgba(99, 102, 241, 0.2)",
  border: "1px solid rgba(99, 102, 241, 0.4)",
  borderRadius: 8,
  color: "#a5b4fc",
  fontWeight: 600,
  fontSize: "0.9rem",
  cursor: "pointer",
};
