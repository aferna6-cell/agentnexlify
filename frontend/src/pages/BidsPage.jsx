import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  fetchBids,
  createBid,
  updateBid,
  deleteBid,
  updateBidStatus,
  fetchBidStats,
  fetchBidTemplates,
  createBidTemplate,
  deleteBidTemplate,
  aiGenerateBid,
} from "../utils/api/bids";

const STATUS_FILTERS = ["all", "draft", "sent", "viewed", "accepted", "rejected"];

const STATUS_COLORS = {
  draft: { color: "var(--text-muted)", bg: "var(--hover-overlay)" },
  sent: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  viewed: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  accepted: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  rejected: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
};

const STATUS_PROGRESSION = {
  draft: ["sent"],
  sent: ["viewed", "accepted", "rejected"],
  viewed: ["accepted", "rejected"],
  accepted: [],
  rejected: [],
};

const emptyLineItem = { name: "", qty: 1, unit_price: 0 };

const emptyForm = {
  title: "",
  description: "",
  line_items: [{ ...emptyLineItem }],
  terms: "",
  timeline: "",
};

function formatCurrency(val) {
  const num = Number(val);
  if (isNaN(num)) return "$0.00";
  return "$" + num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function calcTotal(items) {
  return (items || []).reduce((sum, it) => sum + (Number(it.qty) || 0) * (Number(it.unit_price) || 0), 0);
}

export default function BidsPage() {
  const { user, token } = useAuth();
  const [bids, setBids] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [activeFilter, setActiveFilter] = useState("all");

  // Create/Edit modal
  const [showModal, setShowModal] = useState(false);
  const [editBid, setEditBid] = useState(null);
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);

  // Detail modal
  const [detailBid, setDetailBid] = useState(null);

  // AI Generate
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiGenerating, setAiGenerating] = useState(false);

  // Templates
  const [showTemplates, setShowTemplates] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [savingTemplate, setSavingTemplate] = useState(false);

  // Deleting
  const [deletingIds, setDeletingIds] = useState(new Set());

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const params = {};
      if (activeFilter !== "all") params.status = activeFilter;
      const [bidsData, statsData] = await Promise.all([
        fetchBids(user.tenantId, token, params),
        fetchBidStats(user.tenantId, token),
      ]);
      setBids(bidsData.bids || bidsData || []);
      setStats(statsData);
      setError(null);
    } catch (err) {
      console.warn("Failed to load bids:", err.message);
      setError(err.message || "Failed to load bids");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, activeFilter]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  const loadTemplates = async () => {
    if (!user?.tenantId) return;
    setTemplatesLoading(true);
    try {
      const data = await fetchBidTemplates(user.tenantId, token);
      setTemplates(data.templates || data || []);
    } catch (err) {
      console.warn("Failed to load templates:", err.message);
    } finally {
      setTemplatesLoading(false);
    }
  };

  const openCreate = () => {
    setEditBid(null);
    setForm({ ...emptyForm, line_items: [{ ...emptyLineItem }] });
    setAiPrompt("");
    setShowModal(true);
  };

  const openEdit = (bid) => {
    setEditBid(bid);
    setForm({
      title: bid.title || "",
      description: bid.description || "",
      line_items: bid.line_items && bid.line_items.length > 0
        ? bid.line_items.map((li) => ({ ...li }))
        : [{ ...emptyLineItem }],
      terms: bid.terms || "",
      timeline: bid.timeline || "",
    });
    setShowModal(true);
    setDetailBid(null);
  };

  const handleSave = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    const body = {
      title: form.title.trim(),
      description: form.description.trim() || null,
      line_items: form.line_items.filter((li) => li.name.trim()),
      terms: form.terms.trim() || null,
      timeline: form.timeline.trim() || null,
    };
    try {
      if (editBid) {
        await updateBid(user.tenantId, token, editBid.id, body);
      } else {
        await createBid(user.tenantId, token, body);
      }
      setShowModal(false);
      setForm({ ...emptyForm });
      setEditBid(null);
      loadData();
    } catch (err) {
      console.warn("Save bid failed:", err.message);
      setError(err.message || "Failed to save bid");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (bidId) => {
    if (!window.confirm("Delete this bid? This cannot be undone.")) return;
    setDeletingIds((prev) => new Set(prev).add(bidId));
    try {
      await deleteBid(user.tenantId, token, bidId);
      setBids((prev) => prev.filter((b) => b.id !== bidId));
      if (detailBid && detailBid.id === bidId) setDetailBid(null);
      setError(null);
    } catch (err) {
      console.warn("Delete bid failed:", err.message);
      setError(err.message || "Failed to delete bid");
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(bidId);
        return next;
      });
    }
  };

  const handleStatusChange = async (bidId, newStatus) => {
    try {
      await updateBidStatus(user.tenantId, token, bidId, newStatus);
      setBids((prev) =>
        prev.map((b) => (b.id === bidId ? { ...b, status: newStatus } : b))
      );
      if (detailBid && detailBid.id === bidId) {
        setDetailBid((prev) => ({ ...prev, status: newStatus }));
      }
    } catch (err) {
      console.warn("Status update failed:", err.message);
      setError(err.message || "Failed to update status");
    }
  };

  const handleAiGenerate = async () => {
    if (!aiPrompt.trim()) return;
    setAiGenerating(true);
    try {
      const result = await aiGenerateBid(user.tenantId, token, aiPrompt.trim());
      setForm({
        title: result.title || "",
        description: result.description || "",
        line_items: result.line_items && result.line_items.length > 0
          ? result.line_items
          : [{ ...emptyLineItem }],
        terms: result.terms || "",
        timeline: result.timeline || "",
      });
      setAiPrompt("");
    } catch (err) {
      console.warn("AI generate failed:", err.message);
      setError(err.message || "AI generation failed");
    } finally {
      setAiGenerating(false);
    }
  };

  const handleSaveAsTemplate = async (bid) => {
    setSavingTemplate(true);
    try {
      await createBidTemplate(user.tenantId, token, {
        name: bid.title,
        line_items: bid.line_items || [],
        terms: bid.terms || "",
        timeline: bid.timeline || "",
        description: bid.description || "",
      });
      if (showTemplates) loadTemplates();
    } catch (err) {
      console.warn("Save template failed:", err.message);
      setError(err.message || "Failed to save template");
    } finally {
      setSavingTemplate(false);
    }
  };

  const handleDeleteTemplate = async (templateId) => {
    if (!window.confirm("Delete this template?")) return;
    try {
      await deleteBidTemplate(user.tenantId, token, templateId);
      setTemplates((prev) => prev.filter((t) => t.id !== templateId));
    } catch (err) {
      console.warn("Delete template failed:", err.message);
    }
  };

  const handleUseTemplate = (template) => {
    setForm({
      title: template.name || "",
      description: template.description || "",
      line_items: template.line_items && template.line_items.length > 0
        ? template.line_items.map((li) => ({ ...li }))
        : [{ ...emptyLineItem }],
      terms: template.terms || "",
      timeline: template.timeline || "",
    });
    setShowTemplates(false);
    if (!showModal) {
      setEditBid(null);
      setShowModal(true);
    }
  };

  // Line item helpers
  const addLineItem = () => {
    setForm((f) => ({ ...f, line_items: [...f.line_items, { ...emptyLineItem }] }));
  };

  const removeLineItem = (idx) => {
    setForm((f) => ({
      ...f,
      line_items: f.line_items.length > 1 ? f.line_items.filter((_, i) => i !== idx) : f.line_items,
    }));
  };

  const updateLineItem = (idx, field, value) => {
    setForm((f) => ({
      ...f,
      line_items: f.line_items.map((li, i) =>
        i === idx ? { ...li, [field]: value } : li
      ),
    }));
  };

  if (loading) return <SkeletonLoader />;

  const totalBids = stats?.total_bids ?? bids.length;
  const winRate = stats?.win_rate ?? 0;
  const avgValue = stats?.average_bid_value ?? 0;
  const pipelineValue = stats?.pipeline_value ?? 0;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Bids</h1>
          <p>Create, track, and manage contractor bids and proposals</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            className="btn-primary"
            onClick={() => {
              setShowTemplates(true);
              loadTemplates();
            }}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
            }}
          >
            Templates
          </button>
          <button
            className="btn-primary"
            onClick={() => {
              setLoading(true);
              loadData();
            }}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
            }}
          >
            Refresh
          </button>
          <button className="btn-primary" onClick={openCreate}>
            + New Bid
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 12,
          marginBottom: 24,
        }}
      >
        {[
          { label: "Total Bids", value: totalBids, color: "var(--text-secondary)" },
          { label: "Win Rate", value: `${Math.round(winRate)}%`, color: "#22c55e" },
          { label: "Avg Bid Value", value: formatCurrency(avgValue), color: "#3b82f6" },
          { label: "Pipeline Value", value: formatCurrency(pipelineValue), color: "#8b5cf6" },
        ].map((card) => (
          <div
            key={card.label}
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: "16px 20px",
            }}
          >
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4 }}>
              {card.label}
            </div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: card.color }}>
              {card.value}
            </div>
          </div>
        ))}
      </div>

      {/* Status Filter Tabs */}
      <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
        {STATUS_FILTERS.map((s) => {
          const isActive = activeFilter === s;
          const count =
            s === "all" ? bids.length : bids.filter((b) => b.status === s).length;
          return (
            <button
              key={s}
              onClick={() => setActiveFilter(s)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border: isActive
                  ? "1px solid var(--accent)"
                  : "1px solid var(--border)",
                background: isActive ? "var(--accent-dim)" : "var(--bg-secondary)",
                color: isActive ? "var(--accent)" : "var(--text-secondary)",
                cursor: "pointer",
                fontSize: "0.85rem",
                fontWeight: isActive ? 600 : 400,
                textTransform: "capitalize",
                transition: "all 0.15s ease",
              }}
            >
              {s}
              <span style={{ marginLeft: 6, fontSize: "0.75rem", opacity: 0.7 }}>
                {count}
              </span>
            </button>
          );
        })}
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

      {/* Bid List */}
      {bids.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>
            {activeFilter !== "all" ? "No bids match this filter" : "No bids yet"}
          </div>
          <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
            {activeFilter !== "all"
              ? "Try selecting a different status filter, or create a new bid."
              : "Create your first bid to start tracking proposals and win rates. You can generate bids with AI or build them from templates."}
          </p>
          {activeFilter !== "all" ? (
            <button
              className="btn-primary"
              onClick={() => setActiveFilter("all")}
              style={{
                background: "transparent",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
              }}
            >
              Clear Filter
            </button>
          ) : (
            <button className="btn-primary" onClick={openCreate}>
              Create Your First Bid
            </button>
          )}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {bids.map((bid) => {
            const statusColor = STATUS_COLORS[bid.status] || STATUS_COLORS.draft;
            const isDeleting = deletingIds.has(bid.id);
            const total = calcTotal(bid.line_items);

            return (
              <div
                key={bid.id}
                style={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  padding: 16,
                  borderLeft: `4px solid ${statusColor.color}`,
                  opacity: isDeleting ? 0.5 : 1,
                  cursor: "pointer",
                  transition: "opacity 0.2s ease",
                }}
                onClick={() => setDetailBid(bid)}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                    gap: 8,
                  }}
                >
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                      <span style={{ fontWeight: 600, fontSize: "1rem" }}>{bid.title}</span>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "2px 8px",
                          borderRadius: 4,
                          fontSize: "0.7rem",
                          fontWeight: 600,
                          color: statusColor.color,
                          background: statusColor.bg,
                          textTransform: "capitalize",
                        }}
                      >
                        {bid.status}
                      </span>
                    </div>
                    {bid.description && (
                      <div
                        style={{
                          fontSize: "0.85rem",
                          color: "var(--text-secondary)",
                          lineHeight: 1.4,
                          marginBottom: 4,
                        }}
                      >
                        {bid.description.length > 120
                          ? bid.description.slice(0, 120) + "..."
                          : bid.description}
                      </div>
                    )}
                    <div style={{ display: "flex", gap: 12, fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      {bid.timeline && <span>Timeline: {bid.timeline}</span>}
                      <span>{formatDate(bid.created_at)}</span>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#3b82f6" }}>
                        {formatCurrency(total)}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        {(bid.line_items || []).length} item{(bid.line_items || []).length !== 1 ? "s" : ""}
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 6 }} onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => openEdit(bid)}
                        disabled={isDeleting}
                        style={{
                          background: "none",
                          border: "1px solid var(--border)",
                          borderRadius: 6,
                          padding: "6px 10px",
                          color: "var(--text-secondary)",
                          cursor: "pointer",
                          fontSize: "0.8rem",
                        }}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(bid.id)}
                        disabled={isDeleting}
                        style={{
                          background: "none",
                          border: "1px solid var(--border)",
                          borderRadius: 6,
                          padding: "6px 10px",
                          color: "var(--red, #ef4444)",
                          cursor: "pointer",
                          fontSize: "0.8rem",
                        }}
                      >
                        {isDeleting ? "..." : "Delete"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detail Modal */}
      {detailBid && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setDetailBid(null)}
        >
          <div
            style={{
              background: "var(--bg-primary)",
              borderRadius: 12,
              padding: 24,
              width: "90%",
              maxWidth: 600,
              maxHeight: "80vh",
              overflowY: "auto",
              border: "1px solid var(--border)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <h3 style={{ marginBottom: 6 }}>{detailBid.title}</h3>
                <span
                  style={{
                    display: "inline-block",
                    padding: "3px 10px",
                    borderRadius: 4,
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: (STATUS_COLORS[detailBid.status] || STATUS_COLORS.draft).color,
                    background: (STATUS_COLORS[detailBid.status] || STATUS_COLORS.draft).bg,
                    textTransform: "capitalize",
                  }}
                >
                  {detailBid.status}
                </span>
              </div>
              <button
                onClick={() => setDetailBid(null)}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  fontSize: "1.2rem",
                }}
              >
                x
              </button>
            </div>

            {detailBid.description && (
              <div style={{ fontSize: "0.9rem", color: "var(--text-secondary)", marginBottom: 16, lineHeight: 1.5 }}>
                {detailBid.description}
              </div>
            )}

            {/* Line Items */}
            {detailBid.line_items && detailBid.line_items.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                  Line Items
                </div>
                <div style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", padding: "8px 12px", background: "var(--bg-secondary)", fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>
                    <span>Item</span>
                    <span style={{ textAlign: "right" }}>Qty</span>
                    <span style={{ textAlign: "right" }}>Unit Price</span>
                    <span style={{ textAlign: "right" }}>Total</span>
                  </div>
                  {detailBid.line_items.map((li, idx) => (
                    <div key={idx} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", padding: "8px 12px", borderTop: "1px solid var(--border)", fontSize: "0.85rem" }}>
                      <span>{li.name}</span>
                      <span style={{ textAlign: "right" }}>{li.qty}</span>
                      <span style={{ textAlign: "right" }}>{formatCurrency(li.unit_price)}</span>
                      <span style={{ textAlign: "right", fontWeight: 600 }}>{formatCurrency((li.qty || 0) * (li.unit_price || 0))}</span>
                    </div>
                  ))}
                  <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", padding: "10px 12px", borderTop: "2px solid var(--border)", fontSize: "0.9rem", fontWeight: 700 }}>
                    <span>Total</span>
                    <span />
                    <span />
                    <span style={{ textAlign: "right", color: "#3b82f6" }}>{formatCurrency(calcTotal(detailBid.line_items))}</span>
                  </div>
                </div>
              </div>
            )}

            {detailBid.terms && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", marginBottom: 4 }}>Terms</div>
                <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>{detailBid.terms}</div>
              </div>
            )}

            {detailBid.timeline && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", marginBottom: 4 }}>Timeline</div>
                <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>{detailBid.timeline}</div>
              </div>
            )}

            {/* Status Progression Buttons */}
            {(STATUS_PROGRESSION[detailBid.status] || []).length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", marginBottom: 8 }}>
                  Update Status
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {(STATUS_PROGRESSION[detailBid.status] || []).map((nextStatus) => {
                    const sc = STATUS_COLORS[nextStatus] || STATUS_COLORS.draft;
                    return (
                      <button
                        key={nextStatus}
                        onClick={() => handleStatusChange(detailBid.id, nextStatus)}
                        style={{
                          padding: "6px 14px",
                          borderRadius: 6,
                          border: `1px solid ${sc.color}`,
                          background: sc.bg,
                          color: sc.color,
                          cursor: "pointer",
                          fontSize: "0.8rem",
                          fontWeight: 600,
                          textTransform: "capitalize",
                        }}
                      >
                        Mark as {nextStatus}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", borderTop: "1px solid var(--border)", paddingTop: 16 }}>
              <button
                onClick={() => handleSaveAsTemplate(detailBid)}
                disabled={savingTemplate}
                style={{
                  background: "transparent",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: "8px 16px",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                  fontSize: "0.8rem",
                }}
              >
                {savingTemplate ? "Saving..." : "Save as Template"}
              </button>
              <button
                onClick={() => openEdit(detailBid)}
                style={{
                  background: "transparent",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: "8px 16px",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                  fontSize: "0.8rem",
                }}
              >
                Edit
              </button>
              <button
                onClick={() => setDetailBid(null)}
                className="btn-primary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setShowModal(false)}
        >
          <div
            style={{
              background: "var(--bg-primary)",
              borderRadius: 12,
              padding: 24,
              width: "90%",
              maxWidth: 600,
              maxHeight: "85vh",
              overflowY: "auto",
              border: "1px solid var(--border)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 16 }}>
              {editBid ? "Edit Bid" : "Create New Bid"}
            </h3>

            {/* AI Generate (create only) */}
            {!editBid && (
              <div
                style={{
                  background: "rgba(139,92,246,0.08)",
                  border: "1px solid rgba(139,92,246,0.25)",
                  borderRadius: 8,
                  padding: 12,
                  marginBottom: 16,
                }}
              >
                <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#8b5cf6", marginBottom: 6 }}>
                  AI Generate
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <textarea
                    value={aiPrompt}
                    onChange={(e) => setAiPrompt(e.target.value)}
                    placeholder="Describe the job... e.g. 'Kitchen remodel: replace countertops, install backsplash, update plumbing'"
                    rows={2}
                    style={{ flex: 1, fontSize: "0.85rem", resize: "vertical" }}
                    disabled={aiGenerating}
                  />
                  <button
                    onClick={handleAiGenerate}
                    disabled={!aiPrompt.trim() || aiGenerating}
                    style={{
                      background: "#8b5cf6",
                      color: "#fff",
                      border: "none",
                      borderRadius: 6,
                      padding: "6px 14px",
                      cursor: "pointer",
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      whiteSpace: "nowrap",
                      opacity: !aiPrompt.trim() || aiGenerating ? 0.5 : 1,
                      alignSelf: "flex-end",
                    }}
                  >
                    {aiGenerating ? "Generating..." : "AI Generate"}
                  </button>
                </div>
                <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 4 }}>
                  Describe the project and AI will generate a professional bid with line items
                </div>
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
                  Title *
                </label>
                <input
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  placeholder="e.g. Kitchen Remodel Bid, Landscaping Proposal"
                  style={{ width: "100%" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
                  Description
                </label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="Project scope, overview, and details..."
                  rows={3}
                  style={{ width: "100%", resize: "vertical" }}
                />
              </div>

              {/* Line Items Editor */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Line Items</label>
                  <button
                    onClick={addLineItem}
                    style={{
                      background: "none",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      padding: "4px 10px",
                      color: "var(--accent)",
                      cursor: "pointer",
                      fontSize: "0.75rem",
                    }}
                  >
                    + Add Item
                  </button>
                </div>
                {form.line_items.map((li, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: "flex",
                      gap: 8,
                      marginBottom: 6,
                      alignItems: "center",
                    }}
                  >
                    <input
                      value={li.name}
                      onChange={(e) => updateLineItem(idx, "name", e.target.value)}
                      placeholder="Item name"
                      style={{ flex: 2 }}
                    />
                    <input
                      type="number"
                      value={li.qty}
                      onChange={(e) => updateLineItem(idx, "qty", e.target.value)}
                      placeholder="Qty"
                      min={0}
                      style={{ flex: 0.5, textAlign: "right" }}
                    />
                    <input
                      type="number"
                      value={li.unit_price}
                      onChange={(e) => updateLineItem(idx, "unit_price", e.target.value)}
                      placeholder="Unit $"
                      min={0}
                      step="0.01"
                      style={{ flex: 0.7, textAlign: "right" }}
                    />
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", minWidth: 60, textAlign: "right" }}>
                      {formatCurrency((Number(li.qty) || 0) * (Number(li.unit_price) || 0))}
                    </span>
                    {form.line_items.length > 1 && (
                      <button
                        onClick={() => removeLineItem(idx)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "#ef4444",
                          cursor: "pointer",
                          fontSize: "0.9rem",
                          padding: "0 4px",
                        }}
                      >
                        x
                      </button>
                    )}
                  </div>
                ))}
                <div style={{ textAlign: "right", fontSize: "0.9rem", fontWeight: 600, color: "#3b82f6", marginTop: 4 }}>
                  Total: {formatCurrency(calcTotal(form.line_items))}
                </div>
              </div>

              <div style={{ display: "flex", gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
                    Terms
                  </label>
                  <textarea
                    value={form.terms}
                    onChange={(e) => setForm((f) => ({ ...f, terms: e.target.value }))}
                    placeholder="Payment terms, warranty, conditions..."
                    rows={2}
                    style={{ width: "100%", resize: "vertical" }}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
                    Timeline
                  </label>
                  <input
                    value={form.timeline}
                    onChange={(e) => setForm((f) => ({ ...f, timeline: e.target.value }))}
                    placeholder="e.g. 2-3 weeks, Start March 25"
                    style={{ width: "100%" }}
                  />
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
              <button
                onClick={() => {
                  setShowModal(false);
                  setEditBid(null);
                }}
                style={{
                  background: "transparent",
                  border: "1px solid var(--border)",
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
                onClick={handleSave}
                disabled={!form.title.trim() || saving}
              >
                {saving ? "Saving..." : editBid ? "Save Changes" : "Create Bid"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Templates Modal */}
      {showTemplates && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setShowTemplates(false)}
        >
          <div
            style={{
              background: "var(--bg-primary)",
              borderRadius: 12,
              padding: 24,
              width: "90%",
              maxWidth: 520,
              maxHeight: "80vh",
              overflowY: "auto",
              border: "1px solid var(--border)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 16 }}>Bid Templates</h3>

            {templatesLoading ? (
              <div style={{ textAlign: "center", padding: "30px 0", color: "var(--text-muted)" }}>
                Loading templates...
              </div>
            ) : templates.length === 0 ? (
              <div style={{ textAlign: "center", padding: "30px 20px", color: "var(--text-muted)" }}>
                <div style={{ fontSize: "1.1rem", marginBottom: 8 }}>No templates saved yet</div>
                <p style={{ fontSize: "0.85rem", maxWidth: 360, margin: "0 auto" }}>
                  When viewing a bid, click "Save as Template" to reuse it for future bids.
                </p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {templates.map((tmpl) => (
                  <div
                    key={tmpl.id}
                    style={{
                      background: "var(--bg-secondary)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      padding: 12,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{tmpl.name}</div>
                      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                        {(tmpl.line_items || []).length} items
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button
                        onClick={() => handleUseTemplate(tmpl)}
                        style={{
                          background: "var(--accent-dim)",
                          border: "1px solid var(--accent)",
                          borderRadius: 6,
                          padding: "6px 12px",
                          color: "var(--accent)",
                          cursor: "pointer",
                          fontSize: "0.8rem",
                          fontWeight: 600,
                        }}
                      >
                        Use
                      </button>
                      <button
                        onClick={() => handleDeleteTemplate(tmpl.id)}
                        style={{
                          background: "none",
                          border: "1px solid var(--border)",
                          borderRadius: 6,
                          padding: "6px 10px",
                          color: "#ef4444",
                          cursor: "pointer",
                          fontSize: "0.8rem",
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
              <button
                onClick={() => setShowTemplates(false)}
                className="btn-primary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
