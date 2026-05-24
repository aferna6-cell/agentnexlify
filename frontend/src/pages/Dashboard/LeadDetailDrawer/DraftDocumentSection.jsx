import { useState } from "react";
import {
  draftDocument,
  downloadDraftedDocument,
} from "../../../utils/api/managed-agents";

export default function DraftDocumentSection({ lead, form, tenantId, token }) {
  const [showDraftQuote, setShowDraftQuote] = useState(false);
  const [draftKind, setDraftKind] = useState("quote");
  const [draftNotes, setDraftNotes] = useState("");
  const [draftLineItems, setDraftLineItems] = useState([
    { description: "", qty: 1, unit_price: 0 },
  ]);
  const [draftingDoc, setDraftingDoc] = useState(false);
  const [draftResult, setDraftResult] = useState(null);
  const [draftError, setDraftError] = useState(null);
  const [downloadingDoc, setDownloadingDoc] = useState(false);

  const handleLineItemChange = (index, field) => (e) => {
    const value =
      field === "description"
        ? e.target.value
        : parseFloat(e.target.value) || 0;
    setDraftLineItems((items) =>
      items.map((it, i) => (i === index ? { ...it, [field]: value } : it)),
    );
  };

  const handleAddLineItem = () => {
    setDraftLineItems((items) => [
      ...items,
      { description: "", qty: 1, unit_price: 0 },
    ]);
  };

  const handleRemoveLineItem = (index) => {
    setDraftLineItems((items) => items.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!tenantId || !token) return;
    const cleanItems = draftLineItems
      .map((it) => ({
        description: (it.description || "").trim(),
        qty: Number(it.qty) || 0,
        unit_price: Number(it.unit_price) || 0,
      }))
      .filter((it) => it.description && it.qty > 0);
    if (cleanItems.length === 0) {
      setDraftError(
        "Add at least one line item with a description and quantity.",
      );
      return;
    }
    setDraftingDoc(true);
    setDraftError(null);
    setDraftResult(null);
    try {
      const result = await draftDocument(tenantId, token, {
        kind: draftKind,
        lead_id: lead.id,
        customer: {
          name: form.name || lead.name || "Customer",
          email: form.email || lead.email || undefined,
          phone: form.phone || lead.phone || undefined,
        },
        line_items: cleanItems,
        notes: draftNotes || undefined,
      });
      setDraftResult(result);
    } catch (err) {
      setDraftError(err.body?.detail || err.message || "Draft failed");
    } finally {
      setDraftingDoc(false);
    }
  };

  const handleDownload = async () => {
    if (!draftResult || !tenantId || !token) return;
    setDownloadingDoc(true);
    try {
      const { blob, filename } = await downloadDraftedDocument(
        tenantId,
        token,
        draftResult.document_id,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setDraftError(err.message || "Download failed");
    } finally {
      setDownloadingDoc(false);
    }
  };

  return (
    <div className="intel-section">
      <div
        className="intel-title"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        Draft Document (AI)
        {!showDraftQuote && (
          <button
            className="btn-sm"
            onClick={() => {
              setShowDraftQuote(true);
              setDraftResult(null);
              setDraftError(null);
            }}
            style={{ background: "var(--accent, #00BFFF)" }}
          >
            + Draft
          </button>
        )}
      </div>
      {showDraftQuote && (
        <div
          style={{
            padding: 12,
            borderRadius: 8,
            background: "rgba(0,191,255,0.05)",
            border: "1px solid rgba(0,191,255,0.2)",
          }}
        >
          <div className="drawer-field">
            <label className="drawer-label">Kind</label>
            <select
              className="drawer-input"
              value={draftKind}
              onChange={(e) => setDraftKind(e.target.value)}
            >
              <option value="quote">Quote (DOCX)</option>
              <option value="invoice">Invoice (XLSX)</option>
              <option value="proposal">Proposal (DOCX)</option>
            </select>
          </div>
          <div className="drawer-field">
            <label className="drawer-label">Line items</label>
            {draftLineItems.map((item, i) => (
              <div key={i} style={{ display: "flex", gap: 6, marginBottom: 6 }}>
                <input
                  className="drawer-input"
                  placeholder="Description"
                  value={item.description}
                  onChange={handleLineItemChange(i, "description")}
                  style={{ flex: 2 }}
                />
                <input
                  className="drawer-input"
                  type="number"
                  placeholder="Qty"
                  value={item.qty}
                  min="0"
                  step="0.1"
                  onChange={handleLineItemChange(i, "qty")}
                  style={{ width: 60 }}
                />
                <input
                  className="drawer-input"
                  type="number"
                  placeholder="Price"
                  value={item.unit_price}
                  min="0"
                  step="0.01"
                  onChange={handleLineItemChange(i, "unit_price")}
                  style={{ width: 80 }}
                />
                {draftLineItems.length > 1 && (
                  <button
                    className="btn-sm"
                    onClick={() => handleRemoveLineItem(i)}
                    style={{
                      background: "var(--red, #ef4444)",
                      width: 28,
                    }}
                    title="Remove"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
            <button
              className="btn-sm"
              onClick={handleAddLineItem}
              style={{ background: "var(--text-muted)" }}
            >
              + Add item
            </button>
          </div>
          <div className="drawer-field">
            <label className="drawer-label">Notes (optional)</label>
            <textarea
              className="drawer-input"
              rows="2"
              value={draftNotes}
              onChange={(e) => setDraftNotes(e.target.value)}
              placeholder="Any additional terms or context..."
            />
          </div>
          <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
            <button
              className="btn-sm"
              onClick={handleSubmit}
              disabled={draftingDoc}
              style={{ background: "var(--accent, #00BFFF)" }}
            >
              {draftingDoc ? "Drafting... (10-30s)" : "Generate"}
            </button>
            <button
              className="btn-sm"
              onClick={() => {
                setShowDraftQuote(false);
                setDraftResult(null);
                setDraftError(null);
              }}
            >
              Cancel
            </button>
          </div>
          {draftError && (
            <div
              style={{
                marginTop: 8,
                padding: "8px 10px",
                borderRadius: 6,
                background: "rgba(239,68,68,0.1)",
                color: "#ef4444",
                fontSize: "0.8rem",
              }}
            >
              {draftError}
            </div>
          )}
          {draftResult && (
            <div
              style={{
                marginTop: 8,
                padding: "10px 12px",
                borderRadius: 6,
                background: "rgba(34,197,94,0.1)",
                border: "1px solid rgba(34,197,94,0.3)",
                fontSize: "0.85rem",
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 6 }}>
                {draftResult.title}
              </div>
              <div
                style={{
                  color: "var(--text-muted)",
                  fontSize: "0.78rem",
                  marginBottom: 8,
                }}
              >
                {draftResult.file_name} · {draftResult.file_type.toUpperCase()}
                {draftResult.file_size_bytes
                  ? ` · ${Math.round(draftResult.file_size_bytes / 1024)} KB`
                  : ""}
              </div>
              <button
                className="btn-sm"
                onClick={handleDownload}
                disabled={downloadingDoc}
                style={{ background: "var(--green, #22c55e)" }}
              >
                {downloadingDoc ? "Downloading..." : "Download"}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
