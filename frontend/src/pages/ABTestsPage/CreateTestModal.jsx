import { useState } from "react";
import {
  apiFetch,
  TEST_TYPES,
  overlayStyle,
  modalStyle,
  inputStyle,
  labelStyle,
  btnPrimary,
  btnSecondary,
} from "./utils";

export default function CreateTestModal({
  tenantId,
  token,
  onClose,
  onCreated,
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [testType, setTestType] = useState("subject_line");
  const [variants, setVariants] = useState([
    {
      name: "Variant A",
      subject: "",
      body: "",
      send_time_override: "",
      allocation_percent: 50,
    },
    {
      name: "Variant B",
      subject: "",
      body: "",
      send_time_override: "",
      allocation_percent: 50,
    },
  ]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const addVariant = () => {
    if (variants.length >= 4) return;
    const nextLetter = String.fromCharCode(65 + variants.length);
    setVariants((prev) => [
      ...prev,
      {
        name: `Variant ${nextLetter}`,
        subject: "",
        body: "",
        send_time_override: "",
        allocation_percent: Math.floor(100 / (variants.length + 1)),
      },
    ]);
    setVariants((prev) =>
      prev.map((v, i) => ({
        ...v,
        allocation_percent:
          i < prev.length - 1
            ? Math.floor(100 / prev.length)
            : 100 -
              prev
                .slice(0, prev.length - 1)
                .reduce((s, x) => s + x.allocation_percent, 0),
      })),
    );
  };

  const removeVariant = (idx) => {
    if (variants.length <= 2) return;
    setVariants((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateVariant = (idx, field, value) => {
    setVariants((prev) =>
      prev.map((v, i) => (i === idx ? { ...v, [field]: value } : v)),
    );
  };

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError("Test name is required");
      return;
    }
    if (variants.length < 2) {
      setError("At least 2 variants required");
      return;
    }
    const totalAllocation = variants.reduce(
      (s, v) => s + (v.allocation_percent || 0),
      0,
    );
    if (totalAllocation !== 100) {
      setError("Variant allocations must sum to 100%");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await apiFetch(`/ab-tests/${tenantId}`, token, {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim(),
          test_type: testType,
          variants: variants.map((v) => ({
            name: v.name,
            subject: v.subject || null,
            body: v.body || null,
            send_time_override: v.send_time_override || null,
            allocation_percent: v.allocation_percent,
          })),
        }),
      });
      onCreated();
    } catch (e) {
      setError(e.message || "Failed to create A/B test");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={modalStyle}>
        <h2
          style={{
            margin: "0 0 20px",
            color: "var(--text-primary)",
            fontSize: "1.2rem",
          }}
        >
          Create A/B Test
        </h2>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 16,
            marginBottom: 16,
          }}
        >
          <div>
            <label style={labelStyle}>Test Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Summer Subject Line Test"
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Test Type</label>
            <select
              value={testType}
              onChange={(e) => setTestType(e.target.value)}
              style={inputStyle}
            >
              {TEST_TYPES.map((t) => (
                <option key={t.key} value={t.key}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Description (optional)</label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What are you testing and why?"
            style={inputStyle}
          />
        </div>

        <div style={{ marginBottom: 8 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 12,
            }}
          >
            <label style={{ ...labelStyle, margin: 0 }}>
              Variants ({variants.length}/4)
            </label>
            {variants.length < 4 && (
              <button
                onClick={addVariant}
                style={{
                  ...btnSecondary,
                  padding: "4px 12px",
                  fontSize: "0.8rem",
                }}
              >
                + Add Variant
              </button>
            )}
          </div>
        </div>

        {variants.map((v, idx) => (
          <div
            key={idx}
            style={{
              background: "var(--bg-primary)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: 16,
              marginBottom: 12,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: 10,
              }}
            >
              <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                {v.name}
              </span>
              {variants.length > 2 && (
                <button
                  onClick={() => removeVariant(idx)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    fontSize: "0.85rem",
                  }}
                >
                  Remove
                </button>
              )}
            </div>

            {testType === "subject_line" && (
              <input
                type="text"
                value={v.subject}
                onChange={(e) => updateVariant(idx, "subject", e.target.value)}
                placeholder="Subject line for this variant"
                style={{ ...inputStyle, marginBottom: 8 }}
              />
            )}

            {testType === "body_content" && (
              <textarea
                value={v.body}
                onChange={(e) => updateVariant(idx, "body", e.target.value)}
                placeholder="Email body for this variant"
                rows={4}
                style={{ ...inputStyle, resize: "vertical", marginBottom: 8 }}
              />
            )}

            {testType === "send_time" && (
              <input
                type="time"
                value={v.send_time_override}
                onChange={(e) =>
                  updateVariant(idx, "send_time_override", e.target.value)
                }
                style={inputStyle}
              />
            )}

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginTop: 8,
              }}
            >
              <label
                style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}
              >
                Allocation:
              </label>
              <input
                type="number"
                value={v.allocation_percent}
                min={1}
                max={99}
                onChange={(e) =>
                  updateVariant(
                    idx,
                    "allocation_percent",
                    parseInt(e.target.value) || 0,
                  )
                }
                style={{ ...inputStyle, width: 80 }}
              />
              <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                %
              </span>
            </div>
          </div>
        ))}

        <div style={{ marginBottom: 16 }}>
          <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            Total allocation:{" "}
            {variants.reduce((s, v) => s + (v.allocation_percent || 0), 0)}%
            {variants.reduce((s, v) => s + (v.allocation_percent || 0), 0) !==
              100 && (
              <span style={{ color: "#f87171", marginLeft: 8 }}>
                (must equal 100%)
              </span>
            )}
          </span>
        </div>

        {error && (
          <div
            style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 12 }}
          >
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={btnSecondary}>
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            style={{ ...btnPrimary, opacity: submitting ? 0.6 : 1 }}
          >
            {submitting ? "Creating..." : "Create A/B Test"}
          </button>
        </div>
      </div>
    </div>
  );
}
