import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchLeads, updateLead, deleteLead } from "../utils/api";
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
    { key: "lead_stage", label: "Stage" },
    { key: "lead_score", label: "Score" },
    { key: "source", label: "Source" },
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
                onClick={() => onSort(col.key)}
                className={sortField === col.key ? "sorted" : ""}
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
              <td><span className={`stage-badge stage-${lead.lead_stage || "new"}`}>{lead.lead_stage || "new"}</span></td>
              <td>
                <span className={`lead-tag ${scoreClass(lead.lead_score)}`}>
                  {lead.lead_score ?? "N/A"} &middot; {scoreLabel(lead.lead_score)}
                </span>
              </td>
              <td>{lead.source || "widget"}</td>
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
      cur.map((l) => (l.id === leadId ? { ...l, lead_stage: newStage } : l))
    );
    try {
      await updateLead(user.tenantId, token, leadId, { lead_stage: newStage });
    } catch {
      setLeads(prev);
    }
  }, [leads, user?.tenantId, token]);

  const handleLeadSave = useCallback(async (leadId, updates) => {
    const updated = await updateLead(user.tenantId, token, leadId, updates);
    setLeads((cur) => cur.map((l) => (l.id === leadId ? { ...l, ...updated } : l)));
    setSelectedLead((cur) => (cur?.id === leadId ? { ...cur, ...updated } : cur));
  }, [user?.tenantId, token]);

  const handleLeadDelete = useCallback(async (leadId) => {
    await deleteLead(user.tenantId, token, leadId);
    setLeads((cur) => cur.filter((l) => l.id !== leadId));
    setSelectedLead(null);
  }, [user?.tenantId, token]);

  const handleExportCSV = () => {
    if (!leads.length) return;
    const headers = ["Name", "Email", "Phone", "Stage", "Score", "Source", "Service Interest", "Timeline", "Budget", "Notes", "Created"];
    const rows = leads.map((l) => [
      l.name || "", l.email || "", l.phone || "", l.lead_stage || "", l.lead_score ?? "",
      l.source || "", l.service_interest || "", l.timeline || "", l.budget || "",
      (l.notes || "").replace(/"/g, '""'), l.created_at || "",
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
      </div>

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
    </div>
  );
}
