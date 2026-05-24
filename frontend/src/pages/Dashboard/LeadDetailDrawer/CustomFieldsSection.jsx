import { useState, useEffect } from "react";
import {
  fetchFieldDefinitions,
  fetchLeadFieldValues,
  updateLeadFieldValues,
} from "../../../utils/api/misc";

export default function CustomFieldsSection({ lead, tenantId, token }) {
  const [customFieldDefs, setCustomFieldDefs] = useState([]);
  const [customFieldValues, setCustomFieldValues] = useState({});
  const [savingCustomFields, setSavingCustomFields] = useState(false);
  const [customFieldStatus, setCustomFieldStatus] = useState(null);

  useEffect(() => {
    if (!tenantId || !token || !lead?.id) return;
    Promise.all([
      fetchFieldDefinitions(tenantId, token),
      fetchLeadFieldValues(tenantId, token, lead.id),
    ]).then(([defs, vals]) => {
      setCustomFieldDefs(Array.isArray(defs) ? defs : defs?.fields || []);
      setCustomFieldValues(vals && typeof vals === "object" ? vals : {});
    });
  }, [tenantId, token, lead?.id]);

  useEffect(() => {
    setCustomFieldValues({});
    setCustomFieldStatus(null);
  }, [lead?.id]);

  const handleSaveCustomFields = async () => {
    setSavingCustomFields(true);
    setCustomFieldStatus(null);
    try {
      await updateLeadFieldValues(tenantId, token, lead.id, customFieldValues);
      setCustomFieldStatus("saved");
    } catch (err) {
      setCustomFieldStatus(err.body?.detail || err.message || "Failed to save");
    } finally {
      setSavingCustomFields(false);
    }
  };

  if (customFieldDefs.length === 0) return null;

  return (
    <div className="intel-section">
      <div className="intel-title">Custom Fields</div>
      {customFieldDefs.map((field) => {
        const fieldId = field.id;
        const currentVal =
          customFieldValues[fieldId] !== undefined
            ? customFieldValues[fieldId]
            : "";
        const onChange = (val) =>
          setCustomFieldValues((prev) => ({ ...prev, [fieldId]: val }));

        return (
          <div key={fieldId} className="drawer-field">
            <label className="drawer-label">
              {field.name}
              {field.is_required && (
                <span style={{ color: "#f87171", marginLeft: 4 }}>*</span>
              )}
            </label>
            {field.field_type === "text" && (
              <input
                className="drawer-input"
                value={currentVal}
                onChange={(e) => onChange(e.target.value)}
                placeholder={field.name}
              />
            )}
            {field.field_type === "number" && (
              <input
                className="drawer-input"
                type="number"
                value={currentVal}
                onChange={(e) => onChange(e.target.value)}
                placeholder="0"
              />
            )}
            {field.field_type === "date" && (
              <input
                className="drawer-input"
                type="date"
                value={currentVal}
                onChange={(e) => onChange(e.target.value)}
              />
            )}
            {field.field_type === "checkbox" && (
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  cursor: "pointer",
                  color: "var(--text-secondary)",
                  fontSize: "0.9rem",
                }}
              >
                <input
                  type="checkbox"
                  checked={!!currentVal}
                  onChange={(e) => onChange(e.target.checked)}
                  style={{ width: "auto" }}
                />
                {field.name}
              </label>
            )}
            {field.field_type === "dropdown" && (
              <select
                className="drawer-select"
                value={currentVal}
                onChange={(e) => onChange(e.target.value)}
              >
                <option value="">-- Select --</option>
                {(field.options || []).map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            )}
          </div>
        );
      })}

      {customFieldStatus === "saved" && (
        <div
          style={{
            color: "var(--green, #22c55e)",
            fontSize: "0.85rem",
            marginTop: 4,
          }}
        >
          Custom fields saved
        </div>
      )}
      {customFieldStatus && customFieldStatus !== "saved" && (
        <div style={{ color: "#f87171", fontSize: "0.85rem", marginTop: 4 }}>
          {customFieldStatus}
        </div>
      )}

      <button
        className="btn-secondary"
        onClick={handleSaveCustomFields}
        disabled={savingCustomFields}
        style={{ marginTop: 10, fontSize: "0.85rem" }}
      >
        {savingCustomFields ? "Saving..." : "Save Custom Fields"}
      </button>
    </div>
  );
}
