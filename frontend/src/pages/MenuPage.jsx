import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import { fetchMenuItems, createMenuItem, updateMenuItem, deleteMenuItem, toggleMenuItemAvailability, importMenuFromWebsite } from "../utils/api/menu";

export default function MenuPage() {
  const { user, token } = useAuth();
  const [items, setItems] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [filterCategory, setFilterCategory] = useState("");
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [form, setForm] = useState({
    name: "", description: "", price: "", category: "", available: true, image_url: "", sort_order: 0,
  });

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const data = await fetchMenuItems(user.tenantId, token);
      setItems(data.items || []);
      const cats = [...new Set((data.items || []).map(i => i.category).filter(Boolean))].sort();
      setCategories(cats);
    } catch (err) {
      console.warn("Failed to load menu:", err.message);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    setEditItem(null);
    setForm({ name: "", description: "", price: "", category: categories[0] || "", available: true, image_url: "", sort_order: 0 });
    setShowModal(true);
  };

  const openEdit = (item) => {
    setEditItem(item);
    setForm({
      name: item.name,
      description: item.description || "",
      price: String(item.price),
      category: item.category || "",
      available: item.available,
      image_url: item.image_url || "",
      sort_order: item.sort_order || 0,
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.name || !form.price) return;
    const body = {
      name: form.name,
      description: form.description || null,
      price: parseFloat(form.price),
      category: form.category || "uncategorized",
      available: form.available,
      image_url: form.image_url || null,
      sort_order: form.sort_order,
    };
    try {
      if (editItem) {
        await updateMenuItem(user.tenantId, token, editItem.id, body);
      } else {
        await createMenuItem(user.tenantId, token, body);
      }
      setShowModal(false);
      load();
    } catch (err) {
      console.warn("Save failed:", err.message);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this menu item?")) return;
    try {
      await deleteMenuItem(user.tenantId, token, id);
      load();
    } catch (err) {
      console.warn("Delete failed:", err.message);
    }
  };

  const handleToggle = async (item) => {
    try {
      await toggleMenuItemAvailability(user.tenantId, token, item.id);
      load();
    } catch (err) {
      console.warn("Toggle failed:", err.message);
    }
  };

  const handleImportFromWebsite = async () => {
    if (!user?.tenantId) return;
    setImporting(true);
    setImportResult(null);
    try {
      const result = await importMenuFromWebsite(user.tenantId, token);
      setImportResult(result);
      if (result.imported > 0) load();
    } catch (err) {
      setImportResult({ imported: 0, message: err.message || "Import failed." });
    } finally {
      setImporting(false);
    }
  };

  if (loading) return <SkeletonLoader />;

  const filtered = filterCategory
    ? items.filter(i => i.category === filterCategory)
    : items;

  // Group by category for display
  const grouped = {};
  for (const item of filtered) {
    const cat = item.category || "uncategorized";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(item);
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Menu</h1>
          <p>Manage your menu items for online ordering</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          {categories.length > 0 && (
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)", fontSize: "0.85rem" }}
            >
              <option value="">All Categories</option>
              {categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          )}
          <button
            className="btn-primary"
            onClick={handleImportFromWebsite}
            disabled={importing}
            style={{ background: "transparent", border: "1px solid var(--border-color)", color: "var(--text-primary)" }}
          >
            {importing ? "Importing..." : "Import from Website"}
          </button>
          <button className="btn-primary" onClick={openCreate}>+ Add Item</button>
        </div>
      </div>

      {importResult && (
        <div style={{
          padding: "10px 14px", borderRadius: 8, marginBottom: 16, fontSize: "0.85rem",
          background: importResult.imported > 0 ? "rgba(34,197,94,0.08)" : "rgba(250,204,21,0.08)",
          border: `1px solid ${importResult.imported > 0 ? "rgba(34,197,94,0.2)" : "rgba(250,204,21,0.2)"}`,
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <span>{importResult.message}</span>
          <button onClick={() => setImportResult(null)} style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}>dismiss</button>
        </div>
      )}

      {items.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>No menu items yet</div>
          <p style={{ maxWidth: 400, margin: "0 auto 20px" }}>
            Add your menu items to let customers browse and order through your chat widget.
          </p>
          <button className="btn-primary" onClick={openCreate}>Add Your First Item</button>
        </div>
      ) : (
        Object.entries(grouped).map(([cat, catItems]) => (
          <div key={cat} style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 12, textTransform: "capitalize", color: "var(--text-secondary)" }}>
              {cat} <span style={{ fontWeight: 400, fontSize: "0.8rem", color: "var(--text-muted)" }}>({catItems.length})</span>
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
              {catItems.map(item => (
                <div key={item.id} style={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 12,
                  padding: 16,
                  opacity: item.available ? 1 : 0.5,
                  position: "relative",
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: "0.95rem", marginBottom: 4 }}>{item.name}</div>
                      {item.description && (
                        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: 8, lineHeight: 1.4 }}>
                          {item.description}
                        </div>
                      )}
                    </div>
                    <div style={{ fontWeight: 700, fontSize: "1rem", color: "var(--green, #22c55e)", marginLeft: 12, whiteSpace: "nowrap" }}>
                      ${parseFloat(item.price).toFixed(2)}
                    </div>
                  </div>
                  {!item.available && (
                    <span style={{
                      display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: "0.7rem", fontWeight: 600,
                      background: "rgba(239,68,68,0.1)", color: "var(--red, #ef4444)", marginBottom: 8,
                    }}>Out of Stock</span>
                  )}
                  <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                    <button onClick={() => openEdit(item)} style={{
                      background: "none", border: "1px solid var(--border-color)", borderRadius: 6, padding: "4px 10px",
                      color: "var(--text-secondary)", cursor: "pointer", fontSize: "0.8rem",
                    }}>Edit</button>
                    <button onClick={() => handleToggle(item)} style={{
                      background: "none", border: "1px solid var(--border-color)", borderRadius: 6, padding: "4px 10px",
                      color: item.available ? "var(--yellow, #facc15)" : "var(--green, #22c55e)", cursor: "pointer", fontSize: "0.8rem",
                    }}>{item.available ? "Mark Unavailable" : "Mark Available"}</button>
                    <button onClick={() => handleDelete(item.id)} style={{
                      background: "none", border: "1px solid var(--border-color)", borderRadius: 6, padding: "4px 10px",
                      color: "var(--red, #ef4444)", cursor: "pointer", fontSize: "0.8rem", marginLeft: "auto",
                    }}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex",
          alignItems: "center", justifyContent: "center", zIndex: 1000,
        }} onClick={() => setShowModal(false)}>
          <div style={{
            background: "var(--bg-primary)", borderRadius: 12, padding: 24, width: "90%", maxWidth: 480,
            border: "1px solid var(--border-color)",
          }} onClick={e => e.stopPropagation()}>
            <h3 style={{ marginBottom: 16 }}>{editItem ? "Edit Menu Item" : "Add Menu Item"}</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>Name *</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="e.g. Margherita Pizza" style={{ width: "100%" }} />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>Description</label>
                <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Fresh mozzarella, basil, tomato sauce" rows={2} style={{ width: "100%", resize: "vertical" }} />
              </div>
              <div style={{ display: "flex", gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>Price *</label>
                  <input type="number" step="0.01" min="0" value={form.price} onChange={e => setForm(f => ({ ...f, price: e.target.value }))} placeholder="12.99" />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>Category</label>
                  <input value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))} placeholder="e.g. Appetizers" list="category-options" />
                  <datalist id="category-options">
                    {categories.map(c => <option key={c} value={c} />)}
                  </datalist>
                </div>
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>Image URL (optional)</label>
                <input value={form.image_url} onChange={e => setForm(f => ({ ...f, image_url: e.target.value }))} placeholder="https://..." />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input type="checkbox" checked={form.available} onChange={e => setForm(f => ({ ...f, available: e.target.checked }))} id="available-check" style={{ width: "auto" }} />
                <label htmlFor="available-check" style={{ margin: 0, cursor: "pointer", fontSize: "0.85rem" }}>Available (in stock)</label>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
              <button onClick={() => setShowModal(false)} style={{
                background: "transparent", border: "1px solid var(--border-color)", borderRadius: 8, padding: "8px 16px",
                color: "var(--text-primary)", cursor: "pointer",
              }}>Cancel</button>
              <button className="btn-primary" onClick={handleSave} disabled={!form.name || !form.price}>
                {editItem ? "Save Changes" : "Add Item"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
