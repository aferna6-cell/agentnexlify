import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import SkeletonLoader from "../../components/SkeletonLoader";
import {
  fetchSmartLists,
  createSmartList,
  updateSmartList,
  deleteSmartList,
  fetchSmartListLeads,
  refreshSmartList,
  exportSmartList,
} from "../../utils/api/smart-lists";
import ListSidebar from "./ListSidebar";
import SelectedListPanel from "./SelectedListPanel";
import SmartListModal from "./SmartListModal";

export default function SmartListsPage({ onNavigate }) {
  const { user, token } = useAuth();

  const [smartLists, setSmartLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedListId, setSelectedListId] = useState(null);
  const [selectedLeads, setSelectedLeads] = useState([]);
  const [leadsLoading, setLeadsLoading] = useState(false);

  const [showModal, setShowModal] = useState(false);
  const [editingList, setEditingList] = useState(null);
  const [saving, setSaving] = useState(false);

  const [deletingId, setDeletingId] = useState(null);
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

  const loadLeads = useCallback(
    async (listId) => {
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
    },
    [user?.tenantId, token],
  );

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
    if (!window.confirm("Delete this smart list? This cannot be undone."))
      return;
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
      setSmartLists((prev) =>
        prev.map((l) =>
          l.id === listId
            ? {
                ...l,
                cached_lead_count:
                  data.cached_lead_count ?? l.cached_lead_count,
              }
            : l,
        ),
      );
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
      onNavigate("campaigns", {
        smart_list_id: selectedListId,
        smart_list_name: selectedList?.name,
      });
    }
  };

  if (loading) return <SkeletonLoader />;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Smart Lists</h1>
          <p>
            Dynamic lead segments that update automatically as your leads change
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            className="btn-primary"
            onClick={() => {
              setLoading(true);
              loadSmartLists();
            }}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
            }}
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
            style={{
              marginLeft: 12,
              background: "none",
              border: "none",
              color: "#ef4444",
              cursor: "pointer",
              fontSize: "0.8rem",
              textDecoration: "underline",
            }}
          >
            dismiss
          </button>
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "280px 1fr",
          gap: 16,
          minHeight: 500,
        }}
      >
        <ListSidebar
          smartLists={smartLists}
          selectedListId={selectedListId}
          deletingId={deletingId}
          refreshingId={refreshingId}
          onSelect={handleSelectList}
          onRefresh={handleRefresh}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />

        <div
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {!selectedList ? (
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
                <svg
                  width="28"
                  height="28"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--accent)"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" />
                </svg>
              </div>
              <h3 style={{ marginBottom: 8, color: "var(--text-primary)" }}>
                {smartLists.length === 0
                  ? "Create your first Smart List"
                  : "Select a Smart List"}
              </h3>
              <p
                style={{
                  color: "var(--text-muted)",
                  fontSize: "0.9rem",
                  lineHeight: 1.6,
                  maxWidth: 420,
                  marginBottom: 24,
                }}
              >
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
            <SelectedListPanel
              selectedList={selectedList}
              selectedLeads={selectedLeads}
              leadsLoading={leadsLoading}
              exporting={exporting}
              onExport={handleExport}
              onUseCampaign={handleUseCampaign}
            />
          )}
        </div>
      </div>

      {showModal && (
        <SmartListModal
          list={editingList}
          onClose={() => {
            setShowModal(false);
            setEditingList(null);
          }}
          onSave={handleSave}
          saving={saving}
        />
      )}
    </div>
  );
}
