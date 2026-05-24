import { useState } from "react";
import FilterBuilder from "./FilterBuilder";
import { emptyFilters } from "./utils";

export default function SmartListModal({ list, onClose, onSave, saving }) {
  const [name, setName] = useState(list?.name || "");
  const [description, setDescription] = useState(list?.description || "");
  const [filters, setFilters] = useState(() => {
    if (list?.filter_json) {
      try {
        return {
          ...emptyFilters,
          ...(typeof list.filter_json === "string"
            ? JSON.parse(list.filter_json)
            : list.filter_json),
        };
      } catch {
        return { ...emptyFilters };
      }
    }
    return { ...emptyFilters };
  });

  const handleSubmit = () => {
    if (!name.trim()) return;
    onSave({
      name: name.trim(),
      description: description.trim() || null,
      filter_json: filters,
    });
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "var(--bg-primary)",
          borderRadius: 12,
          padding: 24,
          width: "90%",
          maxWidth: 580,
          maxHeight: "90vh",
          overflowY: "auto",
          border: "1px solid var(--border)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ marginBottom: 16 }}>
          {list ? "Edit Smart List" : "Create Smart List"}
        </h3>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 12,
            marginBottom: 20,
          }}
        >
          <div>
            <label
              style={{
                display: "block",
                fontSize: "0.8rem",
                marginBottom: 4,
                color: "var(--text-secondary)",
              }}
            >
              Name *
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder='e.g. "Hot Leads in NYC"'
              style={{ width: "100%" }}
            />
          </div>
          <div>
            <label
              style={{
                display: "block",
                fontSize: "0.8rem",
                marginBottom: 4,
                color: "var(--text-secondary)",
              }}
            >
              Description (optional)
            </label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Briefly describe this segment..."
              style={{ width: "100%" }}
            />
          </div>
        </div>

        <div
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            padding: 16,
            marginBottom: 20,
          }}
        >
          <FilterBuilder filters={filters} onChange={setFilters} />
        </div>

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "8px 16px",
              color: "var(--text-primary)",
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={!name.trim() || saving}
          >
            {saving ? "Saving..." : list ? "Update List" : "Create List"}
          </button>
        </div>
      </div>
    </div>
  );
}
