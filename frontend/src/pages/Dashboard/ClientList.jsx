import { useState, useEffect, useCallback, useMemo } from "react";
import { useAuth } from "../../context/AuthContext";
import { fetchClients, changeClientStage } from "../../utils/api/crm";
import SkeletonLoader from "../../components/SkeletonLoader";
import { leadTemperature } from "../../utils/leadTemperature";

const STAGES = ["new", "contacted", "appointment_booked", "closed", "lost"];

function scoreLabel(score) {
  if (score >= 70) return "hot";
  if (score >= 40) return "warm";
  return "cold";
}

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export default function ClientList({ onNavigate }) {
  const { user, token } = useAuth();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [stageFilter, setStageFilter] = useState("");
  const [sortField, setSortField] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");
  const [selected, setSelected] = useState(new Set());

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const res = await fetchClients(user.tenantId, token, {
        search: search || undefined,
        stage: stageFilter || undefined,
        sort: sortField,
        order: sortOrder,
      });
      setClients(res.clients || []);
    } catch (err) {
      console.error("Failed to load clients", err);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, search, stageFilter, sortField, sortOrder]);

  useEffect(() => {
    const timer = setTimeout(load, 300);
    return () => clearTimeout(timer);
  }, [load]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder((o) => (o === "desc" ? "asc" : "desc"));
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const sortIndicator = (field) => {
    if (sortField !== field) return "";
    return sortOrder === "desc" ? " \u2193" : " \u2191";
  };

  const handleBulkStage = async (stage) => {
    if (selected.size === 0) return;
    for (const id of selected) {
      try {
        await changeClientStage(user.tenantId, id, token, stage);
      } catch (err) {
        console.error(`Failed to update stage for ${id}`, err);
      }
    }
    setSelected(new Set());
    load();
  };

  const toggleSelect = (id, e) => {
    e.stopPropagation();
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const exportCsv = () => {
    const headers = ["Name", "Email", "Phone", "Score", "Stage", "Temperature", "Created"];
    const rows = clients.map((c) => [
      c.name || "",
      c.email || "",
      c.phone || "",
      c.lead_score,
      c.status,
      c.lead_temperature || "",
      new Date(c.created_at).toLocaleDateString(),
    ]);
    const csv = [headers, ...rows].map((r) => r.map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "clients.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading && clients.length === 0) return <SkeletonLoader />;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Clients</h1>
        <p>Manage your client relationships</p>
      </div>

      <div className="client-list-header">
        <div className="client-list-controls">
          <input
            className="client-search"
            placeholder="Search by name, email, or phone..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className="client-filter-select"
            value={stageFilter}
            onChange={(e) => setStageFilter(e.target.value)}
          >
            <option value="">All stages</option>
            {STAGES.map((s) => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
        </div>
        <div className="client-list-actions">
          {selected.size > 0 && (
            <select
              className="client-filter-select"
              value=""
              onChange={(e) => e.target.value && handleBulkStage(e.target.value)}
            >
              <option value="">Bulk: Set stage ({selected.size})</option>
              {STAGES.map((s) => (
                <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
              ))}
            </select>
          )}
          <button className="btn-sm" onClick={exportCsv}>Export CSV</button>
        </div>
      </div>

      {clients.length === 0 ? (
        <div className="client-empty">
          <p>No clients found. Clients will appear here as leads come in through your widget.</p>
        </div>
      ) : (
        <table className="client-table">
          <thead>
            <tr>
              <th style={{ width: 30 }}></th>
              <th onClick={() => handleSort("name")}>Name{sortIndicator("name")}</th>
              <th onClick={() => handleSort("email")}>Email{sortIndicator("email")}</th>
              <th onClick={() => handleSort("phone")}>Phone{sortIndicator("phone")}</th>
              <th onClick={() => handleSort("lead_score")}>Interest{sortIndicator("lead_score")}</th>
              <th onClick={() => handleSort("status")}>Stage{sortIndicator("status")}</th>
              <th onClick={() => handleSort("created_at")}>Last Activity{sortIndicator("created_at")}</th>
            </tr>
          </thead>
          <tbody>
            {clients.map((c) => (
              <tr
                key={c.id}
                onClick={() => onNavigate("client_profile", { leadId: c.id })}
              >
                <td>
                  <input
                    type="checkbox"
                    checked={selected.has(c.id)}
                    onChange={(e) => toggleSelect(c.id, e)}
                  />
                </td>
                <td className="client-name-cell">{c.name || "Unknown"}</td>
                <td>{c.email || "-"}</td>
                <td>{c.phone || "-"}</td>
                <td>
                  <span className={`score-badge ${scoreLabel(c.lead_score)}`}>
                    {(() => {
                      const t = leadTemperature(c.lead_score);
                      return t.emoji ? `${t.emoji} ${t.label}` : t.label;
                    })()}
                  </span>
                </td>
                <td>
                  <span className={`stage-badge ${c.status}`}>
                    {c.status}
                  </span>
                </td>
                <td>{timeAgo(c.last_activity || c.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
