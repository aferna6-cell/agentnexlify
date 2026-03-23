import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchLeads, updateLead, deleteLead, importLeadsCSV, findDuplicateLeads, mergeLeads, bulkLeadAction, exportLeadsCSV } from "../utils/api/leads";
import { fetchLeadSuggestions, handleLeadSuggestion } from "../utils/api/leads";
import { fetchTeamMembers } from "../utils/api/team";
import LeadPipeline, { STAGES } from "./Dashboard/LeadPipeline";
import LeadDetailDrawer from "./Dashboard/LeadDetailDrawer";

function formatDate(dateStr) {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

function scoreClass(score) {
  if (score >= 70) return "score-hot";
  if (score >= 40) return "score-warm";
  return "score-cold";
}

function scoreLabel(score) {
  if (score >= 70) return "Hot";
  if (score >= 40) return "Warm";
  return "Cold";
}

function LeadTable({ leads, sortField, sortOrder, onSort, onSelectLead, selectedIds, onToggleSelect, onToggleAll }) {
  const columns = [
    { key: "name", label: "Name" },
    { key: "email", label: "Email" },
    { key: "phone", label: "Phone" },
    { key: "status", label: "Stage" },
    { key: "lead_score", label: "Score" },
    { key: "tags", label: "Tags", sortable: false },
    { key: "created_at", label: "Created" },
  ];

  const allSelected = leads.length > 0 && leads.every((l) => selectedIds.has(l.id));

  return (
    <div className="leads-table-wrapper">
      <table className="leads-table">
        <thead>
          <tr>
            <th style={{ width: 36, cursor: "default" }}>
              <input
                type="checkbox"
                checked={allSelected}
                onChange={(e) => onToggleAll(e.target.checked)}
                style={{ cursor: "pointer" }}
              />
            </th>
            {columns.map((col) => (
              <th
                key={col.key}
                onClick={col.sortable !== false ? () => onSort(col.key) : undefined}
                className={sortField === col.key ? "sorted" : ""}
                style={col.sortable === false ? { cursor: "default" } : undefined}
              >
                {col.label}
                {sortField === col.key && (
                  <span className="sort-arrow">{sortOrder === "asc" ? " \u2191" : " \u2193"}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => (
            <tr key={lead.id} onClick={() => onSelectLead(lead)} style={{ background: selectedIds.has(lead.id) ? "rgba(0,191,255,0.06)" : undefined }}>
              <td onClick={(e) => e.stopPropagation()} style={{ width: 36 }}>
                <input
                  type="checkbox"
                  checked={selectedIds.has(lead.id)}
                  onChange={() => onToggleSelect(lead.id)}
                  style={{ cursor: "pointer" }}
                />
              </td>
              <td>
                <div>{lead.name || "Unknown"}</div>
                {lead.conversation_summary && (
                  <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginTop: 2 }}>
                    {lead.conversation_summary}
                  </div>
                )}
              </td>
              <td>{lead.email || "\u2014"}</td>
              <td>{lead.phone || "\u2014"}</td>
              <td><span className={`stage-badge stage-${lead.status || "new"}`}>{lead.status || "new"}</span></td>
              <td>
                <span className={`lead-tag ${scoreClass(lead.lead_score)}`}>
                  {lead.lead_score ?? "N/A"} &middot; {scoreLabel(lead.lead_score)}
                </span>
              </td>
              <td>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {(lead.tags || []).slice(0, 3).map((tag, ti) => (
                    <span key={ti} style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: 12,
                      fontSize: "0.7rem",
                      background: "var(--accent-dim, rgba(0,191,255,0.15))",
                      color: "var(--accent, #00BFFF)",
                      whiteSpace: "nowrap",
                      maxWidth: 140,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}>
                      {tag}
                    </span>
                  ))}
                  {(lead.tags || []).length > 3 && (
                    <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                      +{lead.tags.length - 3}
                    </span>
                  )}
                </div>
              </td>
              <td>{formatDate(lead.created_at)}</td>
            </tr>
          ))}
          {leads.length === 0 && (
            <tr>
              <td colSpan={7}>
                <div style={{
                  background: "var(--bg-secondary)",
                  borderRadius: 12,
                  padding: 48,
                  textAlign: "center",
                  margin: "8px 0",
                }}>
                  <svg
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="var(--text-muted)"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ marginBottom: 12 }}
                  >
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                  <div style={{ fontWeight: 600, fontSize: "1rem", color: "var(--text-primary)", marginBottom: 8 }}>
                    No leads yet
                  </div>
                  <div style={{ fontSize: "0.875rem", color: "var(--text-muted)", maxWidth: 360, margin: "0 auto" }}>
                    Leads captured from your chat widget will appear here. Set up your widget to start capturing visitors.
                  </div>
                </div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

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
  const fileInputRef = useRef(null);
  const debounceRef = useRef(null);

  // Bulk selection state
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkAction, setBulkAction] = useState("");
  const [bulkParam, setBulkParam] = useState("");
  const [bulkProcessing, setBulkProcessing] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const toggleAll = (checked) => {
    if (checked) {
      setSelectedIds(new Set(leads.map((l) => l.id)));
    } else {
      setSelectedIds(new Set());
    }
  };
  const handleBulkAction = async () => {
    if (!bulkAction || selectedIds.size === 0) return;
    setBulkProcessing(true);
    setBulkResult(null);
    try {
      const params = {};
      if (bulkAction === "assign") params.assigned_to = bulkParam || null;
      if (bulkAction === "change_status") params.status = bulkParam;
      if (bulkAction === "add_tag") params.tag = bulkParam;
      const res = await bulkLeadAction(user.tenantId, token, [...selectedIds], bulkAction, params);
      setBulkResult({ success: true, message: `${res.affected} lead(s) updated` });
      setSelectedIds(new Set());
      setBulkAction("");
      setBulkParam("");
      loadLeads({ stage: stageFilter, search, sort: sortField, order: sortOrder, page, assigned_to: assignedFilter });
    } catch (err) {
      setBulkResult({ success: false, message: err.message || "Bulk action failed" });
    }
    setBulkProcessing(false);
  };

  const loadLeads = useCallback(async (params = {}) => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const res = await fetchLeads(user.tenantId, token, { ...params, page: params.page || 1, per_page: 100 });
      setLeads(res.leads || []);
      setTotalPages(res.total_pages || 1);
      setTotalLeads(res.total || 0);
    } catch {
      setLeads([]);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

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
    loadLeads({ stage: stageFilter || undefined, sort: sortField, order: sortOrder, assigned_to: assignedFilter || undefined, page });
  }, [loadLeads, stageFilter, sortField, sortOrder, assignedFilter, page]);

  // Debounced search
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

  const handleStageDrop = useCallback(async (leadId, newStage) => {
    const prev = leads.slice();
    setLeads((cur) =>
      cur.map((l) => (l.id === leadId ? { ...l, status: newStage } : l))
    );
    try {
      await updateLead(user.tenantId, token, leadId, { status: newStage });
      setError(null);
    } catch (err) {
      setLeads(prev);
      setError(err.body?.detail || err.message || "Failed to update lead stage.");
    }
  }, [leads, user?.tenantId, token]);

  const handleLeadSave = useCallback(async (leadId, updates) => {
    try {
      const updated = await updateLead(user.tenantId, token, leadId, updates);
      setLeads((cur) => cur.map((l) => (l.id === leadId ? { ...l, ...updated } : l)));
      setSelectedLead((cur) => (cur?.id === leadId ? { ...cur, ...updated } : cur));
      setError(null);
    } catch (err) {
      setError(err.body?.detail || err.message || "Failed to save lead.");
    }
  }, [user?.tenantId, token]);

  const handleLeadDelete = useCallback(async (leadId) => {
    try {
      await deleteLead(user.tenantId, token, leadId);
      setLeads((cur) => cur.filter((l) => l.id !== leadId));
      setSelectedLead(null);
      setError(null);
    } catch (err) {
      setError(err.body?.detail || err.message || "Failed to delete lead.");
    }
  }, [user?.tenantId, token]);

  const handleExportCSV = () => {
    if (!leads.length) return;
    const headers = ["Name", "Email", "Phone", "Stage", "Score", "Source", "Service Interest", "Timeline", "Budget", "Notes", "Created"];
    const rows = leads.map((l) => [
      l.name || "", l.email || "", l.phone || "", l.status || "", l.lead_score ?? "",
      l.lead_temperature || "", l.areas_of_interest || "", l.timeline || "", l.budget || "",
      (l.conversation_summary || "").replace(/"/g, '""'), l.created_at || "",
    ]);
    const csv = [headers, ...rows].map((r) => r.map((v) => `"${v}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `leads-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
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
      loadLeads({ stage: stageFilter || undefined, sort: sortField, order: sortOrder, assigned_to: assignedFilter || undefined });
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
      setDuplicates((prev) => prev.filter((d) => !d.leads.some((l) => l.id === mergeId)));
      loadLeads({ stage: stageFilter || undefined, sort: sortField, order: sortOrder, assigned_to: assignedFilter || undefined });
      setError(null);
    } catch (err) {
      setError(err.body?.detail || err.message || "Merge failed");
    } finally {
      setMerging(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Leads</h1>
        <p>{totalLeads} total lead{totalLeads !== 1 ? "s" : ""}</p>
      </div>

      {/* AI Lead Update Suggestions */}
      {suggestions.length > 0 && (
        <div style={{
          marginBottom: 16, padding: "12px 16px", borderRadius: 10,
          background: "rgba(139,92,246,0.1)", border: "1px solid rgba(139,92,246,0.3)",
        }}>
          <div style={{ fontWeight: 600, fontSize: 13, color: "#8b5cf6", marginBottom: 8 }}>
            AI Suggestions ({suggestions.length})
          </div>
          {suggestions.slice(0, 5).map((s) => {
            const sData = s.metadata?.suggestions || {};
            return (
              <div key={s.id} style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "6px 0", borderTop: "1px solid rgba(139,92,246,0.15)",
                fontSize: 12, gap: 8,
              }}>
                <div style={{ flex: 1, color: "var(--text-primary)" }}>
                  {s.description}
                  {Object.entries(sData).map(([field, vals]) => (
                    <span key={field} style={{ marginLeft: 8, color: "var(--text-secondary)" }}>
                      {field}: <s style={{ opacity: 0.5 }}>{vals.old}</s> → <strong>{vals.new}</strong>
                    </span>
                  ))}
                </div>
                <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
                  <button onClick={async () => {
                    await handleLeadSuggestion(user.tenantId, token, s.id, "approve");
                    setSuggestions((prev) => prev.filter((x) => x.id !== s.id));
                    loadLeads({ stage: stageFilter || undefined, sort: sortField, order: sortOrder });
                  }} style={{
                    background: "rgba(34,197,94,0.15)", color: "#22c55e", border: "none",
                    borderRadius: 4, padding: "3px 8px", cursor: "pointer", fontSize: 11,
                  }}>Approve</button>
                  <button onClick={async () => {
                    await handleLeadSuggestion(user.tenantId, token, s.id, "dismiss");
                    setSuggestions((prev) => prev.filter((x) => x.id !== s.id));
                  }} style={{
                    background: "rgba(239,68,68,0.1)", color: "#ef4444", border: "none",
                    borderRadius: 4, padding: "3px 8px", cursor: "pointer", fontSize: 11,
                  }}>Dismiss</button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="leads-toolbar">
        <input
          className="leads-search"
          type="text"
          placeholder="Search leads..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="leads-filter"
          value={stageFilter}
          onChange={(e) => { setStageFilter(e.target.value); setPage(1); }}
        >
          <option value="">All Stages</option>
          {STAGES.map((s) => (
            <option key={s.key} value={s.key}>{s.label}</option>
          ))}
        </select>
        <select
          className="leads-filter"
          value={assignedFilter}
          onChange={(e) => { setAssignedFilter(e.target.value); setPage(1); }}
        >
          <option value="">All Assignees</option>
          {teamMembers.map((m) => (
            <option key={m.id} value={m.id}>{m.name || m.email}</option>
          ))}
        </select>
        <div className="leads-view-toggle">
          <button
            className={`view-btn${view === "board" ? " active" : ""}`}
            onClick={() => setView("board")}
          >
            Board
          </button>
          <button
            className={`view-btn${view === "table" ? " active" : ""}`}
            onClick={() => setView("table")}
          >
            Table
          </button>
        </div>
        <button className="leads-export-btn" onClick={handleExportCSV}>
          Export CSV
        </button>
        <button
          className="leads-export-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={importing}
        >
          {importing ? "Importing..." : "Import CSV"}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          style={{ display: "none" }}
          onChange={handleImportCSV}
        />
        <button
          className="leads-export-btn"
          onClick={async () => {
            try {
              await exportLeadsCSV(user.tenantId, token, { status: stageFilter !== "all" ? stageFilter : undefined });
            } catch (err) {
              console.error("Export failed", err);
            }
          }}
        >
          Export CSV
        </button>
        <button className="leads-export-btn" onClick={handleFindDuplicates}>
          Find Duplicates
        </button>
      </div>

      {error && <div className="error-banner" style={{ marginBottom: "1rem" }}>{error}</div>}
      {importResult && (
        <div style={{ marginBottom: "1rem", padding: "0.75rem 1rem", background: "var(--bg-card)", borderRadius: 8, border: "1px solid var(--border)", fontSize: "0.9rem" }}>
          Imported: {importResult.created} created, {importResult.updated} updated
          {importResult.total_errors > 0 && `, ${importResult.total_errors} error${importResult.total_errors !== 1 ? "s" : ""}`}
          <button onClick={() => setImportResult(null)} style={{ marginLeft: 12, background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}>dismiss</button>
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: 40, color: "var(--text-muted)" }}>Loading...</div>
      ) : view === "board" ? (
        <LeadPipeline
          leads={leads}
          onSelectLead={setSelectedLead}
          onStageDrop={handleStageDrop}
        />
      ) : (
        <>
        {/* Bulk action bar */}
        {selectedIds.size > 0 && (
          <div style={{
            display: "flex", alignItems: "center", gap: 10, padding: "10px 16px",
            background: "rgba(0,191,255,0.08)", borderRadius: 8, marginBottom: 12,
            border: "1px solid var(--accent, #00BFFF)",
          }}>
            <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>{selectedIds.size} selected</span>
            <select
              value={bulkAction}
              onChange={(e) => { setBulkAction(e.target.value); setBulkParam(""); }}
              style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)", fontSize: "0.8rem" }}
            >
              <option value="">Choose action...</option>
              <option value="change_status">Change Status</option>
              <option value="add_tag">Add Tag</option>
              <option value="assign">Assign To</option>
              <option value="delete">Delete</option>
            </select>
            {bulkAction === "change_status" && (
              <select value={bulkParam} onChange={(e) => setBulkParam(e.target.value)}
                style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)", fontSize: "0.8rem" }}>
                <option value="">Select status...</option>
                <option value="new">New</option>
                <option value="contacted">Contacted</option>
                <option value="appointment_booked">Appointment Booked</option>
                <option value="closed">Closed</option>
                <option value="lost">Lost</option>
              </select>
            )}
            {bulkAction === "add_tag" && (
              <input
                placeholder="Tag name..."
                value={bulkParam}
                onChange={(e) => setBulkParam(e.target.value)}
                style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)", fontSize: "0.8rem", width: 140 }}
              />
            )}
            {bulkAction === "assign" && teamMembers.length > 0 && (
              <select value={bulkParam} onChange={(e) => setBulkParam(e.target.value)}
                style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)", fontSize: "0.8rem" }}>
                <option value="">Select team member...</option>
                {teamMembers.map((m) => (
                  <option key={m.id} value={m.id}>{m.name || m.email}</option>
                ))}
              </select>
            )}
            <button
              className="btn-primary"
              onClick={handleBulkAction}
              disabled={bulkProcessing || !bulkAction || (bulkAction !== "delete" && !bulkParam)}
              style={{ fontSize: "0.8rem", padding: "4px 14px" }}
            >
              {bulkProcessing ? "Processing..." : bulkAction === "delete" ? "Delete Selected" : "Apply"}
            </button>
            <button
              onClick={() => { setSelectedIds(new Set()); setBulkAction(""); setBulkParam(""); }}
              style={{ fontSize: "0.8rem", padding: "4px 10px", background: "transparent", border: "1px solid var(--border-color)", borderRadius: 6, color: "var(--text-secondary)", cursor: "pointer" }}
            >
              Clear
            </button>
            {bulkResult && (
              <span style={{ fontSize: "0.78rem", color: bulkResult.success ? "#22c55e" : "#ef4444" }}>
                {bulkResult.message}
              </span>
            )}
          </div>
        )}
        <LeadTable
          leads={leads}
          sortField={sortField}
          sortOrder={sortOrder}
          onSort={handleSort}
          onSelectLead={setSelectedLead}
          selectedIds={selectedIds}
          onToggleSelect={toggleSelect}
          onToggleAll={toggleAll}
        />
        </>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{
          display: "flex", justifyContent: "center", alignItems: "center", gap: 12,
          padding: "16px 0", marginTop: 8,
        }}>
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="btn btn-secondary"
            style={{ padding: "6px 14px", fontSize: 13 }}
          >Previous</button>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            Page {page} of {totalPages} ({totalLeads} leads)
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            className="btn btn-secondary"
            style={{ padding: "6px 14px", fontSize: 13 }}
          >Next</button>
        </div>
      )}

      {selectedLead && (
        <LeadDetailDrawer
          lead={selectedLead}
          onClose={() => setSelectedLead(null)}
          onSave={handleLeadSave}
          onDelete={handleLeadDelete}
        />
      )}

      {duplicates !== null && (
        <div className="modal-overlay" onClick={() => setDuplicates(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 600, maxHeight: "80vh", overflow: "auto" }}>
            <h3>Duplicate Leads</h3>
            {duplicates.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>No duplicates found.</p>
            ) : (
              duplicates.map((dup, i) => (
                <div key={i} style={{ marginBottom: 16, padding: 12, background: "var(--bg-secondary)", borderRadius: 8, border: "1px solid var(--border-color)" }}>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: 8 }}>
                    Match: {dup.match_field} = {dup.match_value}
                  </div>
                  {dup.leads.map((lead) => (
                    <div key={lead.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid var(--border-color)" }}>
                      <div>
                        <div style={{ fontWeight: 600 }}>{lead.name || "No name"}</div>
                        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{lead.email || ""} {lead.phone || ""}</div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Score: {lead.lead_score ?? "N/A"} | {lead.status}</div>
                      </div>
                      <div style={{ display: "flex", gap: 4 }}>
                        {dup.leads.filter((l) => l.id !== lead.id).map((other) => (
                          <button
                            key={other.id}
                            className="btn-sm"
                            disabled={merging}
                            onClick={() => handleMerge(lead.id, other.id)}
                            title={`Keep this, merge ${other.name || other.email || "other"} into it`}
                          >
                            Keep this
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ))
            )}
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setDuplicates(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
