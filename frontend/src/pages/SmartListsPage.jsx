import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  fetchSmartLists,
  createSmartList,
  updateSmartList,
  deleteSmartList,
  fetchSmartListLeads,
  refreshSmartList,
  exportSmartList,
} from "../utils/api";

const STATUS_OPTIONS = [
  { value: "new", label: "New" },
  { value: "contacted", label: "Contacted" },
  { value: "appointment_booked", label: "Appt Booked" },
  { value: "closed", label: "Closed" },
  { value: "lost", label: "Lost" },
];

const TEMPERATURE_OPTIONS = [
  { value: "", label: "Any" },
  { value: "hot", label: "Hot" },
  { value: "warm", label: "Warm" },
  { value: "cold", label: "Cold" },
];

const TEMPERATURE_COLORS = {
  hot: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
  warm: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  cold: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
};

const STATUS_BADGE_COLORS = {
  new: { color: "#6b7280", bg: "rgba(107,114,128,0.1)" },
  contacted: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  appointment_booked: { color: "#8b5cf6", bg: "rgba(139,92,246,0.1)" },
  closed: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  lost: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
};

const emptyFilters = {
  status: [],
  lead_temperature: "",
  min_score: "",
  max_score: "",
  tags_include: [],
  assigned_to: "",
  created_after: "",
  created_before: "",
  has_email: false,
  has_phone: false,
  search: "",
};

function TemperatureBadge({ temp }) {
  const tc = TEMPERATURE_COLORS[temp];
  if (!tc) return <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>--</span>;
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: "0.7rem",
        fontWeight: 600,
        color: tc.color,
        background: tc.bg,
        textTransform: "capitalize",
      }}
    >
      {temp}
    </span>
  );
}

function StatusBadge({ status }) {
  const sc = STATUS_BADGE_COLORS[status] || STATUS_BADGE_COLORS.new;
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: "0.7rem",
        fontWeight: 600,
        color: sc.color,
        background: sc.bg,
        textTransform: "capitalize",
      }}
    >
      {(status || "").replace(/_/g, " ")}
    </span>
  );
}

function FilterBuilder({ filters, onChange, onPreview, previewing, previewCount }) {
  const toggleStatus = (val) => {
    const cur = filters.status || [];
    const next = cur.includes(val) ? cur.filter((s) => s !== val) : [...cur, val];
    onChange({ ...filters, status: next });
  };

  const set = (key, val) => onChange({ ...filters, [key]: val });

  const clearAll = () => onChange({ ...emptyFilters });

  const hasAnyFilter =
    (filters.status || []).length > 0 ||
    filters.lead_temperature ||
    filters.min_score ||
    filters.max_score ||
    (filters.tags_include || []).length > 0 ||
    filters.assigned_to ||
    filters.created_after ||
    filters.created_before ||
    filters.has_email ||
    filters.has_phone ||
    filters.search;

  const labelStyle = {
    display: "block",
    fontSize: "0.75rem",
    fontWeight: 600,
    color: "var(--text-muted)",
    marginBottom: 6,
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  };

  const rowStyle = { marginBottom: 16 };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>Filters</div>
        {hasAnyFilter && (
          <button
            onClick={clearAll}
            style={{
              background: "none",
              border: "none",
              color: "#ef4444",
              cursor: "pointer",
              fontSize: "0.75rem",
              fontWeight: 600,
              textDecoration: "underline",
            }}
          >
            Clear All
          </button>
        )}
      </div>

      {/* Status checkboxes */}
      <div style={rowStyle}>
        <label style={labelStyle}>Status</label>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {STATUS_OPTIONS.map((opt) => {
            const checked = (filters.status || []).includes(opt.value);
            return (
              <label
                key={opt.value}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  cursor: "pointer",
                  fontSize: "0.8rem",
                  color: checked ? "var(--text-primary)" : "var(--text-secondary)",
                  padding: "4px 8px",
                  borderRadius: 6,
                  background: checked ? "var(--accent-dim)" : "transparent",
                  border: checked ? "1px solid var(--accent)" : "1px solid var(--border-color)",
                  transition: "all 0.15s ease",
                }}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleStatus(opt.value)}
                  style={{ width: "auto", margin: 0 }}
                />
                {opt.label}
              </label>
            );
          })}
        </div>
      </div>

      {/* Temperature */}
      <div style={rowStyle}>
        <label style={labelStyle}>Temperature</label>
        <select
          value={filters.lead_temperature || ""}
          onChange={(e) => set("lead_temperature", e.target.value)}
          style={{ width: "100%", fontSize: "0.85rem" }}
        >
          {TEMPERATURE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Score range */}
      <div style={{ ...rowStyle, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <div>
          <label style={labelStyle}>Min Score</label>
          <input
            type="number"
            min={0}
            max={100}
            value={filters.min_score || ""}
            onChange={(e) => set("min_score", e.target.value)}
            placeholder="0"
            style={{ width: "100%", fontSize: "0.85rem" }}
          />
        </div>
        <div>
          <label style={labelStyle}>Max Score</label>
          <input
            type="number"
            min={0}
            max={100}
            value={filters.max_score || ""}
            onChange={(e) => set("max_score", e.target.value)}
            placeholder="100"
            style={{ width: "100%", fontSize: "0.85rem" }}
          />
        </div>
      </div>

      {/* Tags */}
      <div style={rowStyle}>
        <label style={labelStyle}>Tags (comma-separated)</label>
        <input
          type="text"
          value={(filters.tags_include || []).join(", ")}
          onChange={(e) => set("tags_include", e.target.value ? e.target.value.split(",").map(t => t.trim()).filter(Boolean) : [])}
          placeholder="e.g. interested, follow-up"
          style={{ width: "100%", fontSize: "0.85rem" }}
        />
      </div>

      {/* Assigned To */}
      <div style={rowStyle}>
        <label style={labelStyle}>Assigned To</label>
        <input
          type="text"
          value={filters.assigned_to || ""}
          onChange={(e) => set("assigned_to", e.target.value)}
          placeholder='Name or "Unassigned"'
          style={{ width: "100%", fontSize: "0.85rem" }}
        />
      </div>

      {/* Date range */}
      <div style={{ ...rowStyle, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <div>
          <label style={labelStyle}>Created After</label>
          <input
            type="date"
            value={filters.created_after || ""}
            onChange={(e) => set("created_after", e.target.value)}
            style={{ width: "100%", fontSize: "0.85rem" }}
          />
        </div>
        <div>
          <label style={labelStyle}>Created Before</label>
          <input
            type="date"
            value={filters.created_before || ""}
            onChange={(e) => set("created_before", e.target.value)}
            style={{ width: "100%", fontSize: "0.85rem" }}
          />
        </div>
      </div>

      {/* Contact info toggles */}
      <div style={{ ...rowStyle, display: "flex", gap: 20 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
          <input
            type="checkbox"
            checked={!!filters.has_email}
            onChange={(e) => set("has_email", e.target.checked)}
            style={{ width: "auto", margin: 0 }}
          />
          Has Email
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
          <input
            type="checkbox"
            checked={!!filters.has_phone}
            onChange={(e) => set("has_phone", e.target.checked)}
            style={{ width: "auto", margin: 0 }}
          />
          Has Phone
        </label>
      </div>

      {/* Keyword search */}
      <div style={rowStyle}>
        <label style={labelStyle}>Search (name / email / phone)</label>
        <input
          type="text"
          value={filters.search || ""}
          onChange={(e) => set("search", e.target.value)}
          placeholder="Keyword search..."
          style={{ width: "100%", fontSize: "0.85rem" }}
        />
      </div>

      {/* Preview: requires saved list to query leads — only shown when editing */}
    </div>
  );
}

function SmartListModal({ list, onClose, onSave, saving }) {
  const [name, setName] = useState(list?.name || "");
  const [description, setDescription] = useState(list?.description || "");
  const [filters, setFilters] = useState(() => {
    if (list?.filter_json) {
      try {
        return { ...emptyFilters, ...(typeof list.filter_json === "string" ? JSON.parse(list.filter_json) : list.filter_json) };
      } catch {
        return { ...emptyFilters };
      }
    }
    return { ...emptyFilters };
  });
  const [previewCount, setPreviewCount] = useState(null);
  const [previewing, setPreviewing] = useState(false);

  const handlePreview = async () => {
    setPreviewing(true);
    try {
      // Use onSave's tenant context — preview is just to show count
      // For now, we'll set a local count; the parent can override with actual API
      setPreviewCount(null);
      // Simulated — the parent will provide real preview through API if available
      setPreviewing(false);
    } catch {
      setPreviewing(false);
    }
  };

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
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}
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
          border: "1px solid var(--border-color)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ marginBottom: 16 }}>{list ? "Edit Smart List" : "Create Smart List"}</h3>

        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 20 }}>
          <div>
            <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
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
            <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
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
            border: "1px solid var(--border-color)",
            borderRadius: 10,
            padding: 16,
            marginBottom: 20,
          }}
        >
          <FilterBuilder
            filters={filters}
            onChange={setFilters}
            onPreview={handlePreview}
            previewing={previewing}
            previewCount={previewCount}
          />
        </div>

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "1px solid var(--border-color)",
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

function LeadsTable({ leads, loading }) {
  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "var(--text-muted)", fontSize: "0.9rem" }}>
        Loading leads...
      </div>
    );
  }

  if (!leads || leads.length === 0) {
    return (
      <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--text-muted)" }}>
        <div style={{ fontSize: "1.2rem", marginBottom: 8 }}>No matching leads</div>
        <p style={{ fontSize: "0.85rem", lineHeight: 1.6, maxWidth: 400, margin: "0 auto" }}>
          This smart list's filters did not match any current leads. As new leads come in or existing leads update, matching ones will appear here automatically.
        </p>
      </div>
    );
  }

  return (
    <div
      style={{
        background: "var(--bg-secondary)",
        border: "1px solid var(--border-color)",
        borderRadius: 12,
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.5fr 1.5fr 1fr 0.8fr 0.7fr 0.6fr",
          padding: "10px 16px",
          borderBottom: "1px solid var(--border-color)",
          fontSize: "0.75rem",
          color: "var(--text-muted)",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        <span>Name</span>
        <span>Email</span>
        <span>Phone</span>
        <span style={{ textAlign: "center" }}>Status</span>
        <span style={{ textAlign: "center" }}>Temp</span>
        <span style={{ textAlign: "center" }}>Score</span>
      </div>

      {/* Rows */}
      {leads.map((lead) => (
        <div
          key={lead.id}
          style={{
            display: "grid",
            gridTemplateColumns: "1.5fr 1.5fr 1fr 0.8fr 0.7fr 0.6fr",
            padding: "10px 16px",
            borderBottom: "1px solid var(--border-color)",
            alignItems: "center",
            fontSize: "0.85rem",
            transition: "background 0.1s ease",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = "var(--hover-overlay)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
        >
          <span style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {lead.name || "Unnamed"}
          </span>
          <span
            style={{ color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
            title={lead.email}
          >
            {lead.email || "--"}
          </span>
          <span style={{ color: "var(--text-secondary)" }}>{lead.phone || "--"}</span>
          <span style={{ textAlign: "center" }}>
            <StatusBadge status={lead.status} />
          </span>
          <span style={{ textAlign: "center" }}>
            <TemperatureBadge temp={lead.lead_temperature} />
          </span>
          <span
            style={{
              textAlign: "center",
              fontWeight: 600,
              color: lead.lead_score >= 70 ? "#22c55e" : lead.lead_score >= 40 ? "#f59e0b" : "var(--text-muted)",
            }}
          >
            {lead.lead_score != null ? lead.lead_score : "--"}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function SmartListsPage({ onNavigate }) {
  const { user, token } = useAuth();

  // Smart lists state
  const [smartLists, setSmartLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Selected list state
  const [selectedListId, setSelectedListId] = useState(null);
  const [selectedLeads, setSelectedLeads] = useState([]);
  const [leadsLoading, setLeadsLoading] = useState(false);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editingList, setEditingList] = useState(null);
  const [saving, setSaving] = useState(false);

  // Delete state
  const [deletingId, setDeletingId] = useState(null);

  // Refresh/export state
  const [refreshingId, setRefreshingId] = useState(null);
  const [exporting, setExporting] = useState(false);

  const selectedList = smartLists.find((l) => l.id === selectedListId) || null;

  const loadSmartLists = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const data = await fetchSmartLists(user.tenantId, token);
      setSmartLists(data.smart_lists || data || []);
      setError(null);
    } catch (err) {
      console.warn("Failed to load smart lists:", err.message);
      setError(err.message || "Failed to load smart lists");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    setLoading(true);
    loadSmartLists();
  }, [loadSmartLists]);

  // Load leads when a list is selected
  const loadLeads = useCallback(async (listId) => {
    if (!user?.tenantId || !listId) return;
    setLeadsLoading(true);
    try {
      const data = await fetchSmartListLeads(user.tenantId, token, listId);
      setSelectedLeads(data.leads || data || []);
    } catch (err) {
      console.warn("Failed to load smart list leads:", err.message);
      setSelectedLeads([]);
      setError(err.message || "Failed to load leads for this list");
    } finally {
      setLeadsLoading(false);
    }
  }, [user?.tenantId, token]);

  const handleSelectList = (listId) => {
    setSelectedListId(listId);
    loadLeads(listId);
  };

  const handleCreate = () => {
    setEditingList(null);
    setShowModal(true);
  };

  const handleEdit = (list) => {
    setEditingList(list);
    setShowModal(true);
  };

  const handleSave = async (formData) => {
    setSaving(true);
    try {
      if (editingList) {
        await updateSmartList(user.tenantId, token, editingList.id, formData);
      } else {
        await createSmartList(user.tenantId, token, formData);
      }
      setShowModal(false);
      setEditingList(null);
      await loadSmartLists();
      // If editing current selected list, reload leads
      if (editingList && editingList.id === selectedListId) {
        loadLeads(selectedListId);
      }
    } catch (err) {
      console.warn("Save smart list failed:", err.message);
      setError(err.message || "Failed to save smart list");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (listId) => {
    if (!window.confirm("Delete this smart list? This cannot be undone.")) return;
    setDeletingId(listId);
    try {
      await deleteSmartList(user.tenantId, token, listId);
      setSmartLists((prev) => prev.filter((l) => l.id !== listId));
      if (selectedListId === listId) {
        setSelectedListId(null);
        setSelectedLeads([]);
      }
      setError(null);
    } catch (err) {
      console.warn("Delete smart list failed:", err.message);
      setError(err.message || "Failed to delete smart list");
    } finally {
      setDeletingId(null);
    }
  };

  const handleRefresh = async (listId) => {
    setRefreshingId(listId);
    try {
      const data = await refreshSmartList(user.tenantId, token, listId);
      // Update the count in the list
      setSmartLists((prev) =>
        prev.map((l) => (l.id === listId ? { ...l, cached_lead_count: data.cached_lead_count ?? l.cached_lead_count } : l))
      );
      // If it's the selected list, reload leads too
      if (listId === selectedListId) {
        loadLeads(listId);
      }
    } catch (err) {
      console.warn("Refresh failed:", err.message);
      setError(err.message || "Failed to refresh list");
    } finally {
      setRefreshingId(null);
    }
  };

  const handleExport = async () => {
    if (!selectedListId) return;
    setExporting(true);
    try {
      const blob = await exportSmartList(user.tenantId, token, selectedListId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${selectedList?.name || "smart-list"}-leads.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.warn("Export failed:", err.message);
      setError(err.message || "Failed to export CSV");
    } finally {
      setExporting(false);
    }
  };

  const handleUseCampaign = () => {
    if (onNavigate) {
      onNavigate("campaigns", { smart_list_id: selectedListId, smart_list_name: selectedList?.name });
    }
  };

  if (loading) return <SkeletonLoader />;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Smart Lists</h1>
          <p>Dynamic lead segments that update automatically as your leads change</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            className="btn-primary"
            onClick={() => { setLoading(true); loadSmartLists(); }}
            style={{ background: "transparent", border: "1px solid var(--border-color)", color: "var(--text-primary)" }}
          >
            Refresh
          </button>
          <button className="btn-primary" onClick={handleCreate}>
            + New Smart List
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            marginBottom: 16,
            padding: "10px 16px",
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 8,
            color: "#ef4444",
            fontSize: "0.85rem",
          }}
        >
          {error}
          <button
            onClick={() => setError(null)}
            style={{ marginLeft: 12, background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: "0.8rem", textDecoration: "underline" }}
          >
            dismiss
          </button>
        </div>
      )}

      {/* Main Layout: Sidebar + Content */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "280px 1fr",
          gap: 16,
          minHeight: 500,
        }}
      >
        {/* Left Panel: Smart List Sidebar */}
        <div
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border-color)",
            borderRadius: 12,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* Sidebar header */}
          <div
            style={{
              padding: "14px 16px",
              borderBottom: "1px solid var(--border-color)",
              fontSize: "0.8rem",
              fontWeight: 600,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>Your Lists ({smartLists.length})</span>
          </div>

          {/* List items */}
          <div style={{ flex: 1, overflowY: "auto", padding: "8px" }}>
            {smartLists.length === 0 ? (
              <div style={{ padding: "24px 12px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.8rem", lineHeight: 1.6 }}>
                No smart lists yet. Create one to start segmenting your leads by filters like status, temperature, or score.
              </div>
            ) : (
              smartLists.map((list) => {
                const isSelected = selectedListId === list.id;
                const isDeleting = deletingId === list.id;
                const isRefreshing = refreshingId === list.id;

                return (
                  <div
                    key={list.id}
                    onClick={() => handleSelectList(list.id)}
                    style={{
                      padding: "10px 12px",
                      borderRadius: 8,
                      cursor: "pointer",
                      background: isSelected ? "var(--accent-dim)" : "transparent",
                      border: isSelected ? "1px solid var(--accent)" : "1px solid transparent",
                      marginBottom: 4,
                      opacity: isDeleting ? 0.4 : 1,
                      transition: "all 0.15s ease",
                    }}
                    onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = "var(--hover-overlay)"; }}
                    onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }}>
                      <span
                        style={{
                          fontSize: "0.85rem",
                          fontWeight: isSelected ? 700 : 500,
                          color: isSelected ? "var(--accent)" : "var(--text-primary)",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          flex: 1,
                        }}
                      >
                        {list.name}
                      </span>
                      <span
                        style={{
                          fontSize: "0.7rem",
                          fontWeight: 700,
                          color: isSelected ? "var(--accent)" : "var(--text-muted)",
                          background: isSelected ? "rgba(99,102,241,0.15)" : "var(--hover-overlay)",
                          padding: "2px 8px",
                          borderRadius: 10,
                          minWidth: 28,
                          textAlign: "center",
                          flexShrink: 0,
                          marginLeft: 8,
                        }}
                      >
                        {isRefreshing ? "..." : (list.cached_lead_count ?? "?")}
                      </span>
                    </div>
                    {list.description && (
                      <div
                        style={{
                          fontSize: "0.72rem",
                          color: "var(--text-muted)",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {list.description}
                      </div>
                    )}

                    {/* Inline actions */}
                    {isSelected && (
                      <div
                        style={{ display: "flex", gap: 6, marginTop: 8 }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={() => handleRefresh(list.id)}
                          disabled={isRefreshing}
                          style={{
                            background: "none",
                            border: "1px solid var(--border-color)",
                            borderRadius: 4,
                            padding: "2px 8px",
                            color: "var(--text-secondary)",
                            cursor: "pointer",
                            fontSize: "0.7rem",
                          }}
                        >
                          {isRefreshing ? "..." : "Refresh"}
                        </button>
                        <button
                          onClick={() => handleEdit(list)}
                          style={{
                            background: "none",
                            border: "1px solid var(--border-color)",
                            borderRadius: 4,
                            padding: "2px 8px",
                            color: "var(--accent)",
                            cursor: "pointer",
                            fontSize: "0.7rem",
                          }}
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(list.id)}
                          disabled={isDeleting}
                          style={{
                            background: "none",
                            border: "1px solid var(--border-color)",
                            borderRadius: 4,
                            padding: "2px 8px",
                            color: "#ef4444",
                            cursor: "pointer",
                            fontSize: "0.7rem",
                          }}
                        >
                          {isDeleting ? "..." : "Delete"}
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Panel: Content Area */}
        <div
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border-color)",
            borderRadius: 12,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {!selectedList ? (
            /* Empty state — no list selected */
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                flex: 1,
                padding: "60px 20px",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: "50%",
                  background: "var(--accent-dim)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: 20,
                }}
              >
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" />
                </svg>
              </div>
              <h3 style={{ marginBottom: 8, color: "var(--text-primary)" }}>
                {smartLists.length === 0 ? "Create your first Smart List" : "Select a Smart List"}
              </h3>
              <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", lineHeight: 1.6, maxWidth: 420, marginBottom: 24 }}>
                {smartLists.length === 0
                  ? 'Smart Lists are saved filter presets that dynamically group your leads. For example, create a "Hot Leads" list to always see your most engaged prospects in one place.'
                  : "Click on a smart list in the left panel to view its matching leads, or create a new one to segment your leads differently."}
              </p>
              {smartLists.length === 0 && (
                <button className="btn-primary" onClick={handleCreate}>
                  Create Your First Smart List
                </button>
              )}
            </div>
          ) : (
            /* Selected list view */
            <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
              {/* List header */}
              <div
                style={{
                  padding: "16px 20px",
                  borderBottom: "1px solid var(--border-color)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: 16,
                  flexWrap: "wrap",
                }}
              >
                <div style={{ flex: 1, minWidth: 200 }}>
                  <h2 style={{ fontSize: "1.2rem", marginBottom: 4 }}>{selectedList.name}</h2>
                  {selectedList.description && (
                    <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 6 }}>
                      {selectedList.description}
                    </p>
                  )}
                  <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                    <span style={{ fontWeight: 700, color: "var(--accent)" }}>
                      {leadsLoading ? "..." : selectedLeads.length}
                    </span>{" "}
                    matching lead{selectedLeads.length !== 1 ? "s" : ""}
                  </div>
                </div>

                <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                  <button
                    onClick={handleExport}
                    disabled={exporting || selectedLeads.length === 0}
                    style={{
                      background: "rgba(59,130,246,0.1)",
                      border: "1px solid rgba(59,130,246,0.3)",
                      borderRadius: 8,
                      padding: "8px 14px",
                      color: "#3b82f6",
                      cursor: selectedLeads.length === 0 ? "not-allowed" : "pointer",
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      opacity: selectedLeads.length === 0 ? 0.5 : 1,
                    }}
                  >
                    {exporting ? "Exporting..." : "Export CSV"}
                  </button>
                  <button
                    onClick={handleUseCampaign}
                    disabled={selectedLeads.length === 0}
                    style={{
                      background: "rgba(139,92,246,0.1)",
                      border: "1px solid rgba(139,92,246,0.3)",
                      borderRadius: 8,
                      padding: "8px 14px",
                      color: "#8b5cf6",
                      cursor: selectedLeads.length === 0 ? "not-allowed" : "pointer",
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      opacity: selectedLeads.length === 0 ? 0.5 : 1,
                    }}
                  >
                    Use in Campaign
                  </button>
                </div>
              </div>

              {/* Filter summary badges */}
              {selectedList.filter_json && (
                <div style={{ padding: "10px 20px", borderBottom: "1px solid var(--border-color)", display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                  <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", marginRight: 4 }}>
                    Filters:
                  </span>
                  {(() => {
                    const f = typeof selectedList.filter_json === "string"
                      ? (() => { try { return JSON.parse(selectedList.filter_json); } catch { return {}; } })()
                      : selectedList.filter_json || {};
                    const badges = [];
                    if ((f.status || []).length > 0)
                      badges.push(`Status: ${f.status.join(", ")}`);
                    if (f.lead_temperature) badges.push(`Temp: ${f.lead_temperature}`);
                    if (f.min_score) badges.push(`Score >= ${f.min_score}`);
                    if (f.max_score) badges.push(`Score <= ${f.max_score}`);
                    if ((f.tags_include || []).length > 0) badges.push(`Tags: ${f.tags_include.join(", ")}`);
                    if (f.assigned_to) badges.push(`Assigned: ${f.assigned_to}`);
                    if (f.created_after) badges.push(`After: ${f.created_after}`);
                    if (f.created_before) badges.push(`Before: ${f.created_before}`);
                    if (f.has_email) badges.push("Has email");
                    if (f.has_phone) badges.push("Has phone");
                    if (f.search) badges.push(`Search: "${f.search}"`);
                    if (badges.length === 0) badges.push("No filters (all leads)");
                    return badges.map((b, i) => (
                      <span
                        key={i}
                        style={{
                          padding: "3px 8px",
                          borderRadius: 6,
                          fontSize: "0.72rem",
                          background: "var(--hover-overlay)",
                          color: "var(--text-secondary)",
                          border: "1px solid var(--border-color)",
                        }}
                      >
                        {b}
                      </span>
                    ));
                  })()}
                </div>
              )}

              {/* Leads table */}
              <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
                <LeadsTable leads={selectedLeads} loading={leadsLoading} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <SmartListModal
          list={editingList}
          onClose={() => { setShowModal(false); setEditingList(null); }}
          onSave={handleSave}
          saving={saving}
        />
      )}
    </div>
  );
}
