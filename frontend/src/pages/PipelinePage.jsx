import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import { fetchLeads, movePipelineLead, createLead } from "../utils/api";

const PIPELINE_STAGES = [
  { key: "new", label: "New", color: "#6b7280", bg: "rgba(107,114,128,0.1)" },
  { key: "contacted", label: "Contacted", color: "#3b82f6", bg: "rgba(59,130,246,0.08)" },
  { key: "quoted", label: "Quoted", color: "#f59e0b", bg: "rgba(245,158,11,0.08)" },
  { key: "won", label: "Won", color: "#22c55e", bg: "rgba(34,197,94,0.08)" },
  { key: "lost", label: "Lost", color: "#ef4444", bg: "rgba(239,68,68,0.08)" },
];

const TEMPERATURE_COLORS = {
  hot: { color: "#ef4444", bg: "rgba(239,68,68,0.1)", label: "Hot" },
  warm: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)", label: "Warm" },
  cold: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)", label: "Cold" },
};

function formatCurrency(val) {
  const num = Number(val);
  if (!num || isNaN(num)) return null;
  return "$" + num.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function daysAgo(dateStr) {
  if (!dateStr) return null;
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return "Today";
  if (days === 1) return "1d ago";
  return `${days}d ago`;
}

function PipelineCard({ lead, onMove, onSelect, movingId }) {
  const [showMoveMenu, setShowMoveMenu] = useState(false);
  const temp = TEMPERATURE_COLORS[lead.lead_temperature] || null;
  const dealValue = formatCurrency(lead.deal_value);
  const isMoving = movingId === lead.id;

  const otherStages = PIPELINE_STAGES.filter((s) => s.key !== lead.status);

  return (
    <div
      style={{
        background: "var(--bg-primary)",
        border: "1px solid var(--border-color)",
        borderRadius: 10,
        padding: "12px 14px",
        cursor: "pointer",
        opacity: isMoving ? 0.5 : 1,
        transition: "all 0.15s ease",
        position: "relative",
      }}
      onMouseEnter={(e) => { if (!isMoving) e.currentTarget.style.borderColor = "var(--accent)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border-color)"; }}
      onClick={() => onSelect(lead)}
    >
      {/* Header row: name + move button */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 8 }}>
        <div style={{ fontWeight: 600, fontSize: "0.9rem", lineHeight: 1.3, flex: 1, wordBreak: "break-word" }}>
          {lead.name || "Unnamed lead"}
        </div>
        <div
          style={{ position: "relative", flexShrink: 0 }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={() => setShowMoveMenu((prev) => !prev)}
            disabled={isMoving}
            style={{
              background: "none",
              border: "1px solid var(--border-color)",
              borderRadius: 4,
              padding: "2px 6px",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: "0.7rem",
              lineHeight: 1.6,
            }}
            title="Move to stage"
          >
            {isMoving ? "..." : "Move"}
          </button>
          {showMoveMenu && (
            <div
              style={{
                position: "absolute",
                right: 0,
                top: "calc(100% + 4px)",
                background: "var(--bg-primary)",
                border: "1px solid var(--border-color)",
                borderRadius: 8,
                zIndex: 50,
                minWidth: 140,
                boxShadow: "0 4px 16px rgba(0,0,0,0.25)",
                overflow: "hidden",
              }}
            >
              {otherStages.map((stage) => (
                <button
                  key={stage.key}
                  onClick={() => {
                    setShowMoveMenu(false);
                    onMove(lead.id, stage.key);
                  }}
                  style={{
                    display: "block",
                    width: "100%",
                    padding: "8px 14px",
                    background: "none",
                    border: "none",
                    textAlign: "left",
                    cursor: "pointer",
                    fontSize: "0.82rem",
                    color: stage.color,
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = stage.bg; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "none"; }}
                >
                  {stage.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Deal value */}
      {dealValue && (
        <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "#22c55e", marginBottom: 6 }}>
          {dealValue}
        </div>
      )}

      {/* Badges row */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        {temp && (
          <span
            style={{
              display: "inline-block",
              padding: "1px 6px",
              borderRadius: 4,
              fontSize: "0.65rem",
              fontWeight: 600,
              color: temp.color,
              background: temp.bg,
            }}
          >
            {temp.label}
          </span>
        )}
        {lead.lead_score != null && (
          <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
            Score: {lead.lead_score}
          </span>
        )}
        {lead.email && (
          <span
            style={{ fontSize: "0.7rem", color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 120 }}
            title={lead.email}
          >
            {lead.email}
          </span>
        )}
      </div>

      {/* Days in stage */}
      {lead.created_at && (
        <div style={{ marginTop: 8, fontSize: "0.7rem", color: "var(--text-muted)" }}>
          {daysAgo(lead.updated_at || lead.created_at)}
        </div>
      )}
    </div>
  );
}

function AddDealModal({ onClose, onSave, saving }) {
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    deal_value: "",
    expected_close: "",
    status: "new",
  });

  const handleSubmit = () => {
    if (!form.name.trim()) return;
    onSave(form);
  };

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}
      onClick={onClose}
    >
      <div
        style={{ background: "var(--bg-primary)", borderRadius: 12, padding: 24, width: "90%", maxWidth: 480, border: "1px solid var(--border-color)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ marginBottom: 16 }}>Add Deal</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>Name *</label>
            <input
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Contact or company name"
              style={{ width: "100%" }}
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>Email</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                placeholder="email@example.com"
                style={{ width: "100%" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>Phone</label>
              <input
                type="tel"
                value={form.phone}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                placeholder="(555) 555-5555"
                style={{ width: "100%" }}
              />
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>Deal Value ($)</label>
              <input
                type="number"
                value={form.deal_value}
                onChange={(e) => setForm((f) => ({ ...f, deal_value: e.target.value }))}
                placeholder="0"
                min={0}
                step="0.01"
                style={{ width: "100%" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>Expected Close</label>
              <input
                type="date"
                value={form.expected_close}
                onChange={(e) => setForm((f) => ({ ...f, expected_close: e.target.value }))}
                style={{ width: "100%" }}
              />
            </div>
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>Initial Stage</label>
            <select
              value={form.status}
              onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
              style={{ width: "100%" }}
            >
              {PIPELINE_STAGES.map((s) => (
                <option key={s.key} value={s.key}>{s.label}</option>
              ))}
            </select>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
          <button
            onClick={onClose}
            style={{ background: "transparent", border: "1px solid var(--border-color)", borderRadius: 8, padding: "8px 16px", color: "var(--text-primary)", cursor: "pointer" }}
          >
            Cancel
          </button>
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={!form.name.trim() || saving}
          >
            {saving ? "Adding..." : "Add Deal"}
          </button>
        </div>
      </div>
    </div>
  );
}

function LeadQuickView({ lead, onClose }) {
  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}
      onClick={onClose}
    >
      <div
        style={{ background: "var(--bg-primary)", borderRadius: 12, padding: 24, width: "90%", maxWidth: 480, border: "1px solid var(--border-color)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
          <div>
            <h3 style={{ marginBottom: 4 }}>{lead.name || "Unnamed Lead"}</h3>
            {lead.lead_temperature && (
              <span style={{ fontSize: "0.75rem", color: TEMPERATURE_COLORS[lead.lead_temperature]?.color }}>
                {(TEMPERATURE_COLORS[lead.lead_temperature]?.label || lead.lead_temperature)} lead
              </span>
            )}
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "1.2rem" }}>x</button>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: "0.875rem" }}>
          {lead.email && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--text-muted)", minWidth: 80 }}>Email</span>
              <span>{lead.email}</span>
            </div>
          )}
          {lead.phone && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--text-muted)", minWidth: 80 }}>Phone</span>
              <span>{lead.phone}</span>
            </div>
          )}
          {lead.deal_value != null && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--text-muted)", minWidth: 80 }}>Deal Value</span>
              <span style={{ color: "#22c55e", fontWeight: 600 }}>{formatCurrency(lead.deal_value) || "—"}</span>
            </div>
          )}
          {lead.lead_score != null && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--text-muted)", minWidth: 80 }}>Lead Score</span>
              <span>{lead.lead_score}</span>
            </div>
          )}
          {lead.areas_of_interest && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--text-muted)", minWidth: 80 }}>Interested In</span>
              <span>{lead.areas_of_interest}</span>
            </div>
          )}
          {lead.conversation_summary && (
            <div style={{ display: "flex", gap: 8 }}>
              <span style={{ color: "var(--text-muted)", minWidth: 80, flexShrink: 0 }}>Summary</span>
              <span style={{ color: "var(--text-secondary)", lineHeight: 1.5 }}>{lead.conversation_summary}</span>
            </div>
          )}
          {(lead.tags || []).length > 0 && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <span style={{ color: "var(--text-muted)", minWidth: 80 }}>Tags</span>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {lead.tags.map((tag, i) => (
                  <span key={i} style={{ padding: "2px 8px", borderRadius: 12, fontSize: "0.7rem", background: "var(--accent-dim)", color: "var(--accent)" }}>
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div style={{ marginTop: 20, display: "flex", justifyContent: "flex-end" }}>
          <button className="btn-primary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

export default function PipelinePage() {
  const { user, token } = useAuth();
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [movingId, setMovingId] = useState(null);
  const [selectedLead, setSelectedLead] = useState(null);
  const [showAddDeal, setShowAddDeal] = useState(false);
  const [savingDeal, setSavingDeal] = useState(false);

  const loadLeads = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      // Fetch all leads across all pipeline stages
      const res = await fetchLeads(user.tenantId, token, { per_page: 500 });
      setLeads(res.leads || []);
      setError(null);
    } catch (err) {
      console.warn("Failed to load pipeline leads:", err.message);
      setError(err.message || "Failed to load pipeline");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    setLoading(true);
    loadLeads();
  }, [loadLeads]);

  const handleMove = useCallback(async (leadId, newStage) => {
    const prev = leads.slice();
    setLeads((cur) => cur.map((l) => (l.id === leadId ? { ...l, status: newStage } : l)));
    setMovingId(leadId);
    try {
      await movePipelineLead(user.tenantId, token, leadId, { new_stage: newStage });
      setError(null);
    } catch (err) {
      setLeads(prev);
      console.warn("Move lead failed:", err.message);
      setError(err.message || "Failed to move lead");
    } finally {
      setMovingId(null);
    }
  }, [leads, user?.tenantId, token]);

  const handleAddDeal = async (formData) => {
    setSavingDeal(true);
    try {
      const body = {
        name: formData.name.trim(),
        email: formData.email.trim() || null,
        phone: formData.phone.trim() || null,
        status: formData.status || "new",
        deal_value: Number(formData.deal_value) || null,
        expected_close_date: formData.expected_close || null,
      };

      const newLead = await createLead(user.tenantId, token, body);
      setLeads((prev) => [newLead, ...prev]);
      setShowAddDeal(false);
      setError(null);
    } catch (err) {
      console.warn("Add deal failed:", err.message);
      setError(err.message || "Failed to add deal");
    } finally {
      setSavingDeal(false);
    }
  };

  if (loading) return <SkeletonLoader />;

  // Compute stats
  const totalPipelineValue = leads.reduce((sum, l) => sum + (Number(l.deal_value) || 0), 0);
  const wonLeads = leads.filter((l) => l.status === "won");
  const closedLeads = leads.filter((l) => l.status === "won" || l.status === "lost");
  const conversionRate = closedLeads.length > 0 ? Math.round((wonLeads.length / closedLeads.length) * 100) : 0;
  const leadsWithValue = leads.filter((l) => Number(l.deal_value) > 0);
  const avgDealValue = leadsWithValue.length > 0
    ? totalPipelineValue / leadsWithValue.length
    : 0;

  // Group leads by stage key
  const leadsByStage = {};
  PIPELINE_STAGES.forEach((s) => { leadsByStage[s.key] = []; });
  leads.forEach((lead) => {
    const stageKey = lead.status;
    if (leadsByStage[stageKey]) {
      leadsByStage[stageKey].push(lead);
    } else {
      // Unknown stage — put in "new"
      leadsByStage["new"].push(lead);
    }
  });

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Pipeline</h1>
          <p>Visual sales pipeline — track deals from lead to close</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            className="btn-primary"
            onClick={() => { setLoading(true); loadLeads(); }}
            style={{ background: "transparent", border: "1px solid var(--border-color)", color: "var(--text-primary)" }}
          >
            Refresh
          </button>
          <button className="btn-primary" onClick={() => setShowAddDeal(true)}>
            + Add Deal
          </button>
        </div>
      </div>

      {/* Pipeline Stats Bar */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 12,
          marginBottom: 24,
        }}
      >
        {[
          { label: "Pipeline Value", value: totalPipelineValue ? ("$" + totalPipelineValue.toLocaleString("en-US", { maximumFractionDigits: 0 })) : "$0", color: "#3b82f6" },
          { label: "Conversion Rate", value: closedLeads.length > 0 ? `${conversionRate}%` : "—", color: "#22c55e" },
          { label: "Avg Deal Value", value: avgDealValue ? ("$" + Math.round(avgDealValue).toLocaleString("en-US")) : "—", color: "#8b5cf6" },
          { label: "Total Deals", value: leads.length, color: "var(--text-secondary)" },
        ].map((card) => (
          <div
            key={card.label}
            style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-color)", borderRadius: 12, padding: "16px 20px" }}
          >
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4 }}>{card.label}</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: card.color }}>{card.value}</div>
          </div>
        ))}
      </div>

      {error && (
        <div
          style={{ marginBottom: 16, padding: "10px 16px", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 8, color: "#ef4444", fontSize: "0.85rem" }}
        >
          {error}
          <button onClick={() => setError(null)} style={{ marginLeft: 12, background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: "0.8rem", textDecoration: "underline" }}>
            dismiss
          </button>
        </div>
      )}

      {/* Kanban Board */}
      {leads.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>No deals in pipeline</div>
          <p style={{ maxWidth: 440, margin: "0 auto 20px", lineHeight: 1.6 }}>
            Add your first deal to start tracking your sales pipeline. Leads captured from your chat widget will also appear here automatically.
          </p>
          <button className="btn-primary" onClick={() => setShowAddDeal(true)}>
            Add Your First Deal
          </button>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(${PIPELINE_STAGES.length}, minmax(220px, 1fr))`,
            gap: 12,
            overflowX: "auto",
            paddingBottom: 8,
          }}
        >
          {PIPELINE_STAGES.map((stage, stageIdx) => {
            const stageLeads = leadsByStage[stage.key] || [];
            const stageValue = stageLeads.reduce((sum, l) => sum + (Number(l.deal_value) || 0), 0);

            return (
              <div
                key={stage.key}
                style={{
                  background: stageIdx % 2 === 0 ? "var(--bg-secondary)" : "rgba(255,255,255,0.02)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 12,
                  display: "flex",
                  flexDirection: "column",
                  minHeight: 400,
                  overflow: "hidden",
                }}
              >
                {/* Column Header */}
                <div
                  style={{
                    padding: "12px 14px",
                    borderBottom: "2px solid var(--border-color)",
                    borderTopLeftRadius: 12,
                    borderTopRightRadius: 12,
                    background: stage.bg,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontWeight: 700, fontSize: "0.9rem", color: stage.color }}>
                      {stage.label}
                    </span>
                    <span
                      style={{
                        background: stage.color,
                        color: "#fff",
                        borderRadius: "50%",
                        width: 22,
                        height: 22,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "0.7rem",
                        fontWeight: 700,
                        flexShrink: 0,
                      }}
                    >
                      {stageLeads.length}
                    </span>
                  </div>
                  {stageValue > 0 && (
                    <div style={{ fontSize: "0.75rem", color: stage.color, marginTop: 4, fontWeight: 600, opacity: 0.8 }}>
                      ${stageValue.toLocaleString("en-US", { maximumFractionDigits: 0 })}
                    </div>
                  )}
                </div>

                {/* Cards */}
                <div style={{ padding: "10px 10px", display: "flex", flexDirection: "column", gap: 8, flex: 1, overflowY: "auto" }}>
                  {stageLeads.length === 0 ? (
                    <div
                      style={{
                        border: "1px dashed var(--border-color)",
                        borderRadius: 8,
                        padding: "20px 12px",
                        textAlign: "center",
                        color: "var(--text-muted)",
                        fontSize: "0.8rem",
                        flex: 1,
                      }}
                    >
                      No deals in {stage.label.toLowerCase()}
                      <br />
                      <span style={{ fontSize: "0.7rem", marginTop: 4, display: "block", opacity: 0.7 }}>
                        Move a deal here using the "Move" button on a card
                      </span>
                    </div>
                  ) : (
                    stageLeads.map((lead) => (
                      <PipelineCard
                        key={lead.id}
                        lead={lead}
                        onMove={handleMove}
                        onSelect={setSelectedLead}
                        movingId={movingId}
                      />
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Lead Quick View Modal */}
      {selectedLead && (
        <LeadQuickView lead={selectedLead} onClose={() => setSelectedLead(null)} />
      )}

      {/* Add Deal Modal */}
      {showAddDeal && (
        <AddDealModal
          onClose={() => setShowAddDeal(false)}
          onSave={handleAddDeal}
          saving={savingDeal}
        />
      )}
    </div>
  );
}
