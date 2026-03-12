import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchLeads, updateLead, deleteLead, importLeadsCSV, findDuplicateLeads, mergeLeads } from "../utils/api";
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

function LeadTable({ leads, sortField, sortOrder, onSort, onSelectLead }) {
  const columns = [
    { key: "name", label: "Name" },
    { key: "email", label: "Email" },
    { key: "phone", label: "Phone" },
    { key: "status", label: "Stage" },
    { key: "lead_score", label: "Score" },
    { key: "tags", label: "Tags", sortable: false },
    { key: "created_at", label: "Created" },
  ];

  return (
    <div className="leads-table-wrapper">
      <table className="leads-table">
        <thead>
          <tr>
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
            <tr key={lead.id} onClick={() => onSelectLead(lead)}>
              <td>{lead.name || "Unknown"}</td>
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
            <tr><td colSpan={7} className="leads-table-empty">No leads found</td></tr>
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
  const fileInputRef = useRef(null);
  const debounceRef = useRef(null);

  const loadLeads = useCallback(async (params = {}) => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const res = await fetchLeads(user.tenantId, token, params);
      setLeads(res.leads || []);
    } catch {
      setLeads([]);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadLeads({ stage: stageFilter || undefined, sort: sortField, order: sortOrder });
  }, [loadLeads, stageFilter, sortField, sortOrder]);

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      loadLeads({
        stage: stageFilter || undefined,
        search: search || undefined,
        sort: sortField,
        order: sortOrder,
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
      loadLeads({ stage: stageFilter || undefined, sort: sortField, order: sortOrder });
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
      loadLeads({ stage: stageFilter || undefined, sort: sortField, order: sortOrder });
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
        <p>{leads.length} total lead{leads.length !== 1 ? "s" : ""}</p>
      </div>

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
          onChange={(e) => setStageFilter(e.target.value)}
        >
          <option value="">All Stages</option>
          {STAGES.map((s) => (
            <option key={s.key} value={s.key}>{s.label}</option>
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
        <LeadTable
          leads={leads}
          sortField={sortField}
          sortOrder={sortOrder}
          onSort={handleSort}
          onSelectLead={setSelectedLead}
        />
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
