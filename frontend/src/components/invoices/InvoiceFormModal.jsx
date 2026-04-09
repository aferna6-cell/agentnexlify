import { useState } from "react";

import {
  calcSubtotal,
  calcTotal,
  formatCurrency,
} from "./invoiceUtils";

export default function InvoiceFormModal({
  bids,
  saving,
  leads,
  loadingDropdowns,
  form,
  setForm,
  itemTemplates,
  showTemplates,
  onShowTemplatesChange,
  onClose,
  onCreateFromBid,
  onAddItem,
  onAddFromTemplate,
  onSaveTemplate,
  onRemoveItem,
  onUpdateItem,
  onSave,
}) {
  const [selectedBidId, setSelectedBidId] = useState("");

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
          maxWidth: 640,
          maxHeight: "88vh",
          overflowY: "auto",
          border: "1px solid var(--border)",
        }}
        onClick={(event) => event.stopPropagation()}
      >
        <h3 style={{ marginBottom: 16 }}>Create Invoice</h3>

        {bids.length > 0 && (
          <div
            style={{
              background: "rgba(59,130,246,0.08)",
              border: "1px solid rgba(59,130,246,0.2)",
              borderRadius: 8,
              padding: 12,
              marginBottom: 16,
            }}
          >
            <div
              style={{
                fontSize: "0.8rem",
                fontWeight: 600,
                color: "#3b82f6",
                marginBottom: 8,
              }}
            >
              Create from Bid
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <select
                value={selectedBidId}
                onChange={(event) => setSelectedBidId(event.target.value)}
                style={{ flex: 1, fontSize: "0.85rem" }}
              >
                <option value="" disabled>
                  Select a bid...
                </option>
                {bids.map((bid) => (
                  <option key={bid.id} value={bid.id}>
                    {bid.title} - {formatCurrency(calcTotal(bid.line_items || [], 0))}
                  </option>
                ))}
              </select>
              <button
                onClick={() => selectedBidId && onCreateFromBid(selectedBidId)}
                disabled={saving || !selectedBidId}
                style={{
                  background: "#3b82f6",
                  color: "#fff",
                  border: "none",
                  borderRadius: 6,
                  padding: "6px 14px",
                  cursor: "pointer",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                }}
              >
                {saving ? "Creating..." : "Convert"}
              </button>
            </div>
            <div
              style={{
                fontSize: "0.7rem",
                color: "var(--text-muted)",
                marginTop: 4,
              }}
            >
              Instantly converts a bid into an invoice with all line items copied
              over
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
              Customer (optional)
            </label>
            {loadingDropdowns ? (
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                Loading customers...
              </div>
            ) : (
              <select
                value={form.lead_id}
                onChange={(event) =>
                  setForm((current) => ({ ...current, lead_id: event.target.value }))
                }
                style={{ width: "100%" }}
              >
                <option value="">No customer linked</option>
                {leads.map((lead) => (
                  <option key={lead.id} value={lead.id}>
                    {lead.name || lead.email || lead.phone || lead.id}
                  </option>
                ))}
              </select>
            )}
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
                style={{
                  fontSize: "0.8rem",
                  color: "var(--text-secondary)",
                }}
              >
                Items *
              </label>
              <div style={{ display: "flex", gap: 6 }}>
                {itemTemplates.length > 0 && (
                  <div style={{ position: "relative" }}>
                    <button
                      onClick={() => onShowTemplatesChange(!showTemplates)}
                      style={{
                        background: "none",
                        border: "1px solid var(--border)",
                        borderRadius: 6,
                        padding: "4px 10px",
                        color: "var(--purple, #8b5cf6)",
                        cursor: "pointer",
                        fontSize: "0.75rem",
                      }}
                    >
                      Saved Items
                    </button>
                    {showTemplates && (
                      <div
                        style={{
                          position: "absolute",
                          right: 0,
                          top: "100%",
                          marginTop: 4,
                          background: "var(--bg-card, #1e1e2e)",
                          border: "1px solid var(--border)",
                          borderRadius: 8,
                          padding: 4,
                          zIndex: 50,
                          minWidth: 220,
                          maxHeight: 200,
                          overflowY: "auto",
                          boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                        }}
                      >
                        {itemTemplates.map((template) => (
                          <button
                            key={template.id}
                            onClick={() => onAddFromTemplate(template)}
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              width: "100%",
                              background: "none",
                              border: "none",
                              padding: "6px 8px",
                              color: "var(--text-primary)",
                              cursor: "pointer",
                              fontSize: "0.8rem",
                              borderRadius: 4,
                              textAlign: "left",
                            }}
                            onMouseEnter={(event) => {
                              event.currentTarget.style.background =
                                "var(--hover-overlay)";
                            }}
                            onMouseLeave={(event) => {
                              event.currentTarget.style.background = "none";
                            }}
                          >
                            <span>{template.description}</span>
                            <span
                              style={{
                                color: "var(--text-muted)",
                                marginLeft: 8,
                              }}
                            >
                              {formatCurrency(template.unit_price)}
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                <button
                  onClick={onAddItem}
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
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "2fr 1fr 1fr 80px 40px",
                gap: 6,
                marginBottom: 4,
                fontSize: "0.7rem",
                color: "var(--text-muted)",
                fontWeight: 600,
                textTransform: "uppercase",
              }}
            >
              <span>Description</span>
              <span style={{ textAlign: "right" }}>Qty</span>
              <span style={{ textAlign: "right" }}>Unit Price</span>
              <span style={{ textAlign: "right" }}>Total</span>
              <span />
            </div>

            {form.items.map((item, idx) => (
              <div
                key={idx}
                style={{
                  display: "grid",
                  gridTemplateColumns: "2fr 1fr 1fr 80px 40px",
                  gap: 6,
                  marginBottom: 6,
                  alignItems: "center",
                }}
              >
                <input
                  value={item.description}
                  onChange={(event) =>
                    onUpdateItem(idx, "description", event.target.value)
                  }
                  placeholder="Item description"
                />
                <input
                  type="number"
                  value={item.quantity}
                  onChange={(event) =>
                    onUpdateItem(idx, "quantity", event.target.value)
                  }
                  min={0}
                  step="1"
                  style={{ textAlign: "right" }}
                />
                <input
                  type="number"
                  value={item.unit_price}
                  onChange={(event) =>
                    onUpdateItem(idx, "unit_price", event.target.value)
                  }
                  min={0}
                  step="0.01"
                  placeholder="0.00"
                  style={{ textAlign: "right" }}
                />
                <span
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--text-muted)",
                    textAlign: "right",
                  }}
                >
                  {formatCurrency(
                    (Number(item.quantity) || 0) * (Number(item.unit_price) || 0),
                  )}
                </span>
                <div style={{ display: "flex", gap: 4 }}>
                  {item.description.trim() && (
                    <button
                      onClick={() => onSaveTemplate(item)}
                      title="Save as template"
                      style={{
                        background: "none",
                        border: "none",
                        color: "var(--purple, #8b5cf6)",
                        cursor: "pointer",
                        fontSize: "0.7rem",
                        padding: 0,
                      }}
                    >
                      Save
                    </button>
                  )}
                  {form.items.length > 1 && (
                    <button
                      onClick={() => onRemoveItem(idx)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "#ef4444",
                        cursor: "pointer",
                        fontSize: "0.9rem",
                        padding: 0,
                      }}
                    >
                      x
                    </button>
                  )}
                </div>
              </div>
            ))}

            <div
              style={{
                borderTop: "1px solid var(--border)",
                paddingTop: 8,
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-end",
                gap: 4,
                fontSize: "0.85rem",
              }}
            >
              <div style={{ color: "var(--text-secondary)" }}>
                Subtotal: {formatCurrency(calcSubtotal(form.items))}
              </div>
              {Number(form.tax_rate) > 0 && (
                <div style={{ color: "var(--text-secondary)" }}>
                  Tax ({form.tax_rate}%):{" "}
                  {formatCurrency(
                    calcSubtotal(form.items) * (Number(form.tax_rate) / 100),
                  )}
                </div>
              )}
              <div
                style={{
                  fontWeight: 700,
                  color: "#3b82f6",
                  fontSize: "0.95rem",
                }}
              >
                Total: {formatCurrency(calcTotal(form.items, form.tax_rate))}
              </div>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 12,
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
                Tax Rate (%)
              </label>
              <input
                type="number"
                value={form.tax_rate}
                onChange={(event) =>
                  setForm((current) => ({ ...current, tax_rate: event.target.value }))
                }
                min={0}
                max={100}
                step="0.1"
                placeholder="0"
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
                Due Date
              </label>
              <input
                type="date"
                value={form.due_date}
                onChange={(event) =>
                  setForm((current) => ({ ...current, due_date: event.target.value }))
                }
                style={{ width: "100%" }}
              />
            </div>
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
              Deposit Required
            </label>
            <input
              type="number"
              value={form.deposit_amount}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  deposit_amount: event.target.value,
                }))
              }
              min={0}
              step="0.01"
              placeholder="0.00"
              style={{ width: 150 }}
            />
            <span
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                marginLeft: 8,
              }}
            >
              Leave 0 for no deposit
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={form.is_recurring}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    is_recurring: event.target.checked,
                  }))
                }
                style={{ width: "auto" }}
              />
              Recurring Invoice
            </label>
            {form.is_recurring && (
              <select
                value={form.recurrence_interval}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    recurrence_interval: event.target.value,
                  }))
                }
                style={{ fontSize: "0.85rem" }}
              >
                <option value="">Select interval</option>
                <option value="weekly">Weekly</option>
                <option value="biweekly">Bi-weekly</option>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
              </select>
            )}
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
              Notes
            </label>
            <textarea
              value={form.notes}
              onChange={(event) =>
                setForm((current) => ({ ...current, notes: event.target.value }))
              }
              placeholder="Payment terms, special instructions..."
              rows={3}
              style={{ width: "100%", resize: "vertical" }}
            />
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
            onClick={onSave}
            disabled={!form.items.some((item) => item.description.trim()) || saving}
          >
            {saving ? "Creating..." : "Create Invoice"}
          </button>
        </div>
      </div>
    </div>
  );
}
