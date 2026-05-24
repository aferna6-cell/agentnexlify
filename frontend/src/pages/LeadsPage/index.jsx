import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  fetchLeads,
  updateLead,
  deleteLead,
  importLeadsCSV,
  findDuplicateLeads,
  mergeLeads,
  bulkUpdateLeads,
  exportLeadsCSV,
  fetchLeadSuggestions,
  handleLeadSuggestion,
} from "../../utils/api/leads";
import { fetchTeamMembers } from "../../utils/api/team";
import LeadPipeline from "../Dashboard/LeadPipeline";
import LeadDetailDrawer from "../Dashboard/LeadDetailDrawer";
import LeadTable from "./LeadTable";
import QualityStatBar from "./QualityStatBar";
import SuggestionsPanel from "./SuggestionsPanel";
import Toolbar from "./Toolbar";
import BulkActionBar from "./BulkActionBar";
import StatusBanners from "./StatusBanners";
import Pagination from "./Pagination";
import DuplicatesModal from "./DuplicatesModal";

export default function LeadsPage() {
  const { user, token } = useAuth();
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [stageFilter, setStageFilter] = useState("");
  const [view, setView] = useState("board");
  const [sortField, setSortField] = useState("lead_score");
  const [sortOrder, setSortOrder] = useState("desc");
  const [selectedLead, setSelectedLead] = useState(null);
  const [error, setError] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [duplicates, setDuplicates] = useState(null);
  const [merging, setMerging] = useState(false);
  const [assignedFilter, setAssignedFilter] = useState("");
  const [teamMembers, setTeamMembers] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalLeads, setTotalLeads] = useState(0);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkAction, setBulkAction] = useState("");
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);
  const fileInputRef = useRef(null);
  const debounceRef = useRef(null);

  const loadLeads = useCallback(
    async (params = {}) => {
      if (!user?.tenantId) return;
      setLoading(true);
      try {
        const res = await fetchLeads(user.tenantId, token, {
          ...params,
          page: params.page || 1,
          per_page: 100,
        });
        setLeads(res.leads || []);
        setTotalPages(res.total_pages || 1);
        setTotalLeads(res.total || 0);
      } catch (err) {
        setLeads([]);
        setError(err.body?.detail || err.message || "Failed to load leads.");
      } finally {
        setLoading(false);
      }
    },
    [user?.tenantId, token],
  );

  useEffect(() => {
    if (user?.tenantId && token) {
      fetchTeamMembers(user.tenantId, token)
        .then((data) => setTeamMembers(data.members || []))
        .catch((err) => console.warn("Team fetch failed:", err.message));
      fetchLeadSuggestions(user.tenantId, token)
        .then((data) => setSuggestions(data.suggestions || []))
        .catch((err) => console.warn("Suggestions fetch failed:", err.message));
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadLeads({
      stage: stageFilter || undefined,
      sort: sortField,
      order: sortOrder,
      assigned_to: assignedFilter || undefined,
      page,
    });
  }, [loadLeads, stageFilter, sortField, sortOrder, assignedFilter, page]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      loadLeads({
        stage: stageFilter || undefined,
        search: search || undefined,
        sort: sortField,
        order: sortOrder,
        assigned_to: assignedFilter || undefined,
      });
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [search]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSort = (field) => {
    if (field === sortField) {
      setSortOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const handleStageDrop = useCallback(
    async (leadId, newStage) => {
      const prev = leads.slice();
      setLeads((cur) =>
        cur.map((l) => (l.id === leadId ? { ...l, status: newStage } : l)),
      );
      try {
        await updateLead(user.tenantId, token, leadId, { status: newStage });
        setError(null);
      } catch (err) {
        setLeads(prev);
        setError(
          err.body?.detail || err.message || "Failed to update lead stage.",
        );
      }
    },
    [leads, user?.tenantId, token],
  );

  const handleLeadSave = useCallback(
    async (leadId, updates) => {
      try {
        const updated = await updateLead(user.tenantId, token, leadId, updates);
        setLeads((cur) =>
          cur.map((l) => (l.id === leadId ? { ...l, ...updated } : l)),
        );
        setSelectedLead((cur) =>
          cur?.id === leadId ? { ...cur, ...updated } : cur,
        );
        setError(null);
      } catch (err) {
        setError(err.body?.detail || err.message || "Failed to save lead.");
      }
    },
    [user?.tenantId, token],
  );

  const handleLeadDelete = useCallback(
    async (leadId) => {
      try {
        await deleteLead(user.tenantId, token, leadId);
        setLeads((cur) => cur.filter((l) => l.id !== leadId));
        setSelectedLead(null);
        setError(null);
      } catch (err) {
        setError(err.body?.detail || err.message || "Failed to delete lead.");
      }
    },
    [user?.tenantId, token],
  );

  const handleExportCSV = async () => {
    try {
      await exportLeadsCSV(user.tenantId, token, {
        stage: stageFilter || undefined,
        search: search || undefined,
        assigned_to: assignedFilter || undefined,
      });
    } catch (err) {
      setError(err.body?.detail || err.message || "Export failed");
      setTimeout(() => setError(null), 5000);
    }
  };

  const handleImportCSV = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setImporting(true);
    setImportResult(null);
    setError(null);
    try {
      const result = await importLeadsCSV(user.tenantId, token, file);
      setImportResult(result);
      loadLeads({
        stage: stageFilter || undefined,
        sort: sortField,
        order: sortOrder,
        assigned_to: assignedFilter || undefined,
      });
    } catch (err) {
      setError(err.body?.detail || err.message || "Import failed");
    } finally {
      setImporting(false);
    }
  };

  const handleFindDuplicates = async () => {
    try {
      const res = await findDuplicateLeads(user.tenantId, token);
      setDuplicates(res.duplicates || []);
    } catch (err) {
      setError(err.body?.detail || err.message || "Failed to find duplicates");
    }
  };

  const handleMerge = async (keepId, mergeId) => {
    setMerging(true);
    try {
      await mergeLeads(user.tenantId, token, keepId, mergeId);
      setDuplicates((prev) =>
        prev.filter((d) => !d.leads.some((l) => l.id === mergeId)),
      );
      loadLeads({
        stage: stageFilter || undefined,
        sort: sortField,
        order: sortOrder,
        assigned_to: assignedFilter || undefined,
      });
      setError(null);
    } catch (err) {
      setError(err.body?.detail || err.message || "Merge failed");
    } finally {
      setMerging(false);
    }
  };

  const handleToggleSelect = useCallback((leadId) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(leadId)) next.delete(leadId);
      else next.add(leadId);
      return next;
    });
  }, []);

  const handleToggleSelectAll = useCallback((visibleLeads) => {
    setSelectedIds((prev) => {
      const allVisible = visibleLeads.every((l) => prev.has(l.id));
      if (allVisible) {
        const next = new Set(prev);
        visibleLeads.forEach((l) => next.delete(l.id));
        return next;
      }
      const next = new Set(prev);
      visibleLeads.forEach((l) => next.add(l.id));
      return next;
    });
  }, []);

  const handleBulkAction = useCallback(async () => {
    if (!bulkAction || selectedIds.size === 0) return;
    setBulkRunning(true);
    setBulkResult(null);
    setError(null);
    try {
      const lead_ids = Array.from(selectedIds);
      let payload = { lead_ids };

      if (bulkAction.startsWith("status:")) {
        payload.status = bulkAction.replace("status:", "");
      } else if (bulkAction.startsWith("assign:")) {
        const assignTo = bulkAction.replace("assign:", "");
        payload.assigned_to = assignTo || null;
      } else if (bulkAction === "delete") {
        let deleted = 0;
        for (const id of lead_ids) {
          try {
            await deleteLead(user.tenantId, token, id);
            deleted++;
          } catch {
            /* skip */
          }
        }
        setBulkResult({ updated: deleted, failed: lead_ids.length - deleted });
        setSelectedIds(new Set());
        setBulkAction("");
        loadLeads({
          stage: stageFilter || undefined,
          sort: sortField,
          order: sortOrder,
          assigned_to: assignedFilter || undefined,
          page,
        });
        return;
      }

      const result = await bulkUpdateLeads(user.tenantId, token, payload);
      setBulkResult(result);
      setSelectedIds(new Set());
      setBulkAction("");
      loadLeads({
        stage: stageFilter || undefined,
        sort: sortField,
        order: sortOrder,
        assigned_to: assignedFilter || undefined,
        page,
      });
    } catch (err) {
      setError(err.body?.detail || err.message || "Bulk update failed");
    } finally {
      setBulkRunning(false);
    }
  }, [
    bulkAction,
    selectedIds,
    user?.tenantId,
    token,
    loadLeads,
    stageFilter,
    sortField,
    sortOrder,
    assignedFilter,
    page,
  ]);

  const handleSuggestionApprove = async (id) => {
    await handleLeadSuggestion(user.tenantId, token, id, "approve");
    setSuggestions((prev) => prev.filter((x) => x.id !== id));
    loadLeads({
      stage: stageFilter || undefined,
      sort: sortField,
      order: sortOrder,
    });
  };

  const handleSuggestionDismiss = async (id) => {
    await handleLeadSuggestion(user.tenantId, token, id, "dismiss");
    setSuggestions((prev) => prev.filter((x) => x.id !== id));
  };

  const handleStageFilterChange = (val) => {
    setStageFilter(val);
    setPage(1);
  };

  const handleAssignedFilterChange = (val) => {
    setAssignedFilter(val);
    setPage(1);
  };

  const withAllFields = leads.filter(
    (l) => l.name && l.email && l.phone,
  ).length;
  const completionPct =
    leads.length > 0 ? Math.round((withAllFields / leads.length) * 100) : null;
  const aiEnrichedCount = leads.filter(
    (l) => l.enrichment_source === "ai",
  ).length;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Leads</h1>
        <p>
          {totalLeads} total lead{totalLeads !== 1 ? "s" : ""}
        </p>
      </div>

      <QualityStatBar
        completionPct={completionPct}
        aiEnrichedCount={aiEnrichedCount}
      />

      <SuggestionsPanel
        suggestions={suggestions}
        onApprove={handleSuggestionApprove}
        onDismiss={handleSuggestionDismiss}
      />

      <Toolbar
        search={search}
        onSearchChange={setSearch}
        stageFilter={stageFilter}
        onStageFilterChange={handleStageFilterChange}
        assignedFilter={assignedFilter}
        onAssignedFilterChange={handleAssignedFilterChange}
        teamMembers={teamMembers}
        view={view}
        onViewChange={setView}
        importing={importing}
        onImportClick={() => fileInputRef.current?.click()}
        fileInputRef={fileInputRef}
        onImportFile={handleImportCSV}
        onFindDuplicates={handleFindDuplicates}
        onExportCSV={handleExportCSV}
      />

      <BulkActionBar
        selectedCount={selectedIds.size}
        view={view}
        bulkAction={bulkAction}
        onBulkActionChange={setBulkAction}
        teamMembers={teamMembers}
        bulkRunning={bulkRunning}
        onApply={handleBulkAction}
        onClear={() => setSelectedIds(new Set())}
        bulkResult={bulkResult}
        onDismissResult={() => setBulkResult(null)}
      />

      <StatusBanners
        error={error}
        importResult={importResult}
        onDismissImport={() => setImportResult(null)}
      />

      {loading ? (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "var(--text-muted)",
          }}
        >
          Loading...
        </div>
      ) : view === "board" ? (
        <LeadPipeline
          leads={leads}
          onSelectLead={setSelectedLead}
          onStageDrop={handleStageDrop}
        />
      ) : (
        <LeadTable
          leads={leads}
          sortField={sortField}
          sortOrder={sortOrder}
          onSort={handleSort}
          onSelectLead={setSelectedLead}
          selectedIds={selectedIds}
          onToggleSelect={handleToggleSelect}
          onToggleSelectAll={handleToggleSelectAll}
        />
      )}

      <Pagination
        page={page}
        totalPages={totalPages}
        totalLeads={totalLeads}
        onPageChange={setPage}
      />

      {selectedLead && (
        <LeadDetailDrawer
          lead={selectedLead}
          onClose={() => setSelectedLead(null)}
          onSave={handleLeadSave}
          onDelete={handleLeadDelete}
        />
      )}

      <DuplicatesModal
        duplicates={duplicates}
        merging={merging}
        onMerge={handleMerge}
        onClose={() => setDuplicates(null)}
      />
    </div>
  );
}
