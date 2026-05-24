import { formatCurrency, calcTotal } from "./utils";

export default function BidEditorModal({
  showModal,
  setShowModal,
  editBid,
  setEditBid,
  form,
  setForm,
  saving,
  handleSave,
  aiPrompt,
  setAiPrompt,
  aiGenerating,
  handleAiGenerate,
  addLineItem,
  removeLineItem,
  updateLineItem,
}) {
  if (!showModal) return null;

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
      onClick={() => setShowModal(false)}
    >
      <div
        style={{
          background: "var(--bg-primary)",
          borderRadius: 12,
          padding: 24,
          width: "90%",
          maxWidth: 600,
          maxHeight: "85vh",
          overflowY: "auto",
          border: "1px solid var(--border)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ marginBottom: 16 }}>
          {editBid ? "Edit Bid" : "Create New Bid"}
        </h3>

        {!editBid && (
          <div
            style={{
              background: "rgba(139,92,246,0.08)",
              border: "1px solid rgba(139,92,246,0.25)",
              borderRadius: 8,
              padding: 12,
              marginBottom: 16,
            }}
          >
            <div
              style={{
                fontSize: "0.8rem",
                fontWeight: 600,
                color: "#8b5cf6",
                marginBottom: 6,
              }}
            >
              AI Generate
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <textarea
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                placeholder="Describe the job... e.g. 'Kitchen remodel: replace countertops, install backsplash, update plumbing'"
                rows={2}
                style={{ flex: 1, fontSize: "0.85rem", resize: "vertical" }}
                disabled={aiGenerating}
              />
              <button
                onClick={handleAiGenerate}
                disabled={!aiPrompt.trim() || aiGenerating}
                style={{
                  background: "#8b5cf6",
                  color: "#fff",
                  border: "none",
                  borderRadius: 6,
                  padding: "6px 14px",
                  cursor: "pointer",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                  opacity: !aiPrompt.trim() || aiGenerating ? 0.5 : 1,
                  alignSelf: "flex-end",
                }}
              >
                {aiGenerating ? "Generating..." : "AI Generate"}
              </button>
            </div>
            <div
              style={{
                fontSize: "0.7rem",
                color: "var(--text-muted)",
                marginTop: 4,
              }}
            >
              Describe the project and AI will generate a professional bid with
              line items
            </div>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <label
              style={{
                display: "block",
                fontSize: "0.8rem",
                marginBottom: 4,
                color: "var(--text-secondary)",
              }}
            >
              Title *
            </label>
            <input
              value={form.title}
              onChange={(e) =>
                setForm((f) => ({ ...f, title: e.target.value }))
              }
              placeholder="e.g. Kitchen Remodel Bid, Landscaping Proposal"
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
              Description
            </label>
            <textarea
              value={form.description}
              onChange={(e) =>
                setForm((f) => ({ ...f, description: e.target.value }))
              }
              placeholder="Project scope, overview, and details..."
              rows={3}
              style={{ width: "100%", resize: "vertical" }}
            />
          </div>

          <div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 8,
              }}
            >
              <label
                style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}
              >
                Line Items
              </label>
              <button
                onClick={addLineItem}
                style={{
                  background: "none",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  padding: "4px 10px",
                  color: "var(--accent)",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                }}
              >
                + Add Item
              </button>
            </div>
            {form.line_items.map((li, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  gap: 8,
                  marginBottom: 6,
                  alignItems: "center",
                }}
              >
                <input
                  value={li.name}
                  onChange={(e) => updateLineItem(idx, "name", e.target.value)}
                  placeholder="Item name"
                  style={{ flex: 2 }}
                />
                <input
                  type="number"
                  value={li.qty}
                  onChange={(e) => updateLineItem(idx, "qty", e.target.value)}
                  placeholder="Qty"
                  min={0}
                  style={{ flex: 0.5, textAlign: "right" }}
                />
                <input
                  type="number"
                  value={li.unit_price}
                  onChange={(e) =>
                    updateLineItem(idx, "unit_price", e.target.value)
                  }
                  placeholder="Unit $"
                  min={0}
                  step="0.01"
                  style={{ flex: 0.7, textAlign: "right" }}
                />
                <span
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--text-muted)",
                    minWidth: 60,
                    textAlign: "right",
                  }}
                >
                  {formatCurrency(
                    (Number(li.qty) || 0) * (Number(li.unit_price) || 0),
                  )}
                </span>
                {form.line_items.length > 1 && (
                  <button
                    onClick={() => removeLineItem(idx)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "#ef4444",
                      cursor: "pointer",
                      fontSize: "0.9rem",
                      padding: "0 4px",
                    }}
                  >
                    x
                  </button>
                )}
              </div>
            ))}
            <div
              style={{
                textAlign: "right",
                fontSize: "0.9rem",
                fontWeight: 600,
                color: "#3b82f6",
                marginTop: 4,
              }}
            >
              Total: {formatCurrency(calcTotal(form.line_items))}
            </div>
          </div>

          <div style={{ display: "flex", gap: 12 }}>
            <div style={{ flex: 1 }}>
              <label
                style={{
                  display: "block",
                  fontSize: "0.8rem",
                  marginBottom: 4,
                  color: "var(--text-secondary)",
                }}
              >
                Terms
              </label>
              <textarea
                value={form.terms}
                onChange={(e) =>
                  setForm((f) => ({ ...f, terms: e.target.value }))
                }
                placeholder="Payment terms, warranty, conditions..."
                rows={2}
                style={{ width: "100%", resize: "vertical" }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label
                style={{
                  display: "block",
                  fontSize: "0.8rem",
                  marginBottom: 4,
                  color: "var(--text-secondary)",
                }}
              >
                Timeline
              </label>
              <input
                value={form.timeline}
                onChange={(e) =>
                  setForm((f) => ({ ...f, timeline: e.target.value }))
                }
                placeholder="e.g. 2-3 weeks, Start March 25"
                style={{ width: "100%" }}
              />
            </div>
          </div>
        </div>

        <div
          style={{
            display: "flex",
            gap: 8,
            marginTop: 20,
            justifyContent: "flex-end",
          }}
        >
          <button
            onClick={() => {
              setShowModal(false);
              setEditBid(null);
            }}
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
            onClick={handleSave}
            disabled={!form.title.trim() || saving}
          >
            {saving ? "Saving..." : editBid ? "Save Changes" : "Create Bid"}
          </button>
        </div>
      </div>
    </div>
  );
}
