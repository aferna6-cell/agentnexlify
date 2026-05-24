export default function FormPreview({ fields, name, description }) {
  return (
    <div
      style={{
        background: "#f8f9fa",
        borderRadius: 10,
        padding: "24px 20px",
        minHeight: 200,
        color: "#1a1a2e",
      }}
    >
      {name && (
        <h3 style={{ margin: "0 0 4px", fontSize: "1.1rem", color: "#1a1a2e" }}>
          {name}
        </h3>
      )}
      {description && (
        <p style={{ margin: "0 0 16px", fontSize: "0.85rem", color: "#555" }}>
          {description}
        </p>
      )}
      {fields.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: "32px 0",
            color: "#999",
            fontSize: "0.85rem",
          }}
        >
          Add fields to see a live preview of your form
        </div>
      )}
      {fields.map((field) => (
        <div key={field.id} style={{ marginBottom: 14 }}>
          <label
            style={{
              display: "block",
              fontSize: "0.8rem",
              fontWeight: 600,
              marginBottom: 4,
              color: "#333",
            }}
          >
            {field.label || "(Untitled field)"}
            {field.required && (
              <span style={{ color: "#ef4444", marginLeft: 2 }}>*</span>
            )}
          </label>
          {field.type === "textarea" ? (
            <textarea
              readOnly
              placeholder={field.placeholder || ""}
              rows={3}
              style={{
                width: "100%",
                padding: "8px 10px",
                border: "1px solid #ccc",
                borderRadius: 6,
                fontSize: "0.85rem",
                resize: "vertical",
                background: "#fff",
                color: "#333",
                boxSizing: "border-box",
              }}
            />
          ) : field.type === "select" ? (
            <select
              disabled
              style={{
                width: "100%",
                padding: "8px 10px",
                border: "1px solid #ccc",
                borderRadius: 6,
                fontSize: "0.85rem",
                background: "#fff",
                color: "#333",
              }}
            >
              <option value="">{field.placeholder || "Select..."}</option>
              {(field.options || []).map((opt, i) => (
                <option key={i} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          ) : field.type === "radio" ? (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 6,
                marginTop: 4,
              }}
            >
              {(field.options || []).length === 0 ? (
                <span style={{ fontSize: "0.8rem", color: "#999" }}>
                  Add options for radio buttons
                </span>
              ) : (
                field.options.map((opt, i) => (
                  <label
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      fontSize: "0.85rem",
                      color: "#333",
                    }}
                  >
                    <input
                      type="radio"
                      name={`preview-${field.id}`}
                      disabled
                      style={{ width: "auto" }}
                    />
                    {opt}
                  </label>
                ))
              )}
            </div>
          ) : field.type === "checkbox" ? (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 6,
                marginTop: 4,
              }}
            >
              {(field.options || []).length === 0 ? (
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: "0.85rem",
                    color: "#333",
                  }}
                >
                  <input type="checkbox" disabled style={{ width: "auto" }} />
                  {field.label || "Checkbox"}
                </label>
              ) : (
                field.options.map((opt, i) => (
                  <label
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      fontSize: "0.85rem",
                      color: "#333",
                    }}
                  >
                    <input type="checkbox" disabled style={{ width: "auto" }} />
                    {opt}
                  </label>
                ))
              )}
            </div>
          ) : (
            <input
              readOnly
              type={
                field.type === "email"
                  ? "email"
                  : field.type === "phone"
                    ? "tel"
                    : field.type === "number"
                      ? "number"
                      : field.type === "date"
                        ? "date"
                        : "text"
              }
              placeholder={field.placeholder || ""}
              style={{
                width: "100%",
                padding: "8px 10px",
                border: "1px solid #ccc",
                borderRadius: 6,
                fontSize: "0.85rem",
                background: "#fff",
                color: "#333",
                boxSizing: "border-box",
              }}
            />
          )}
        </div>
      ))}
      {fields.length > 0 && (
        <button
          disabled
          style={{
            marginTop: 8,
            padding: "10px 24px",
            background: "var(--accent, #6366f1)",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            fontWeight: 600,
            fontSize: "0.9rem",
            cursor: "default",
            opacity: 0.85,
          }}
        >
          Submit
        </button>
      )}
    </div>
  );
}
