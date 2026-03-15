import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  fetchServiceRecords,
  createServiceRecord,
  updateServiceRecord,
  deleteServiceRecord,
  generatePortalLink,
  fetchLeads,
  sendLeadEmail,
} from "../utils/api";

function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function formatCurrency(val) {
  const num = Number(val);
  if (isNaN(num) || num === 0) return "";
  return "$" + num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const emptyForm = {
  title: "",
  description: "",
  service_date: "",
  notes: "",
  invoice_amount: "",
  lead_id: "",
};

export default function ClientPortalPage() {
  const { user, token } = useAuth();
  const [records, setRecords] = useState([]);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal
  const [showModal, setShowModal] = useState(false);
  const [editRecord, setEditRecord] = useState(null);
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);

  // Portal link generation
  const [generatingLinkFor, setGeneratingLinkFor] = useState(null);
  const [portalLinks, setPortalLinks] = useState({});
  const [copiedId, setCopiedId] = useState(null);

  // Send portal link to client
  const [sendingToClient, setSendingToClient] = useState(null);
  const [sendToast, setSendToast] = useState(null);

  // Deleting
  const [deletingIds, setDeletingIds] = useState(new Set());

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const [recordsData, leadsData] = await Promise.all([
        fetchServiceRecords(user.tenantId, token),
        fetchLeads(user.tenantId, token, { per_page: 200 }),
      ]);
      setRecords(recordsData.records || recordsData || []);
      const leadsList = leadsData.leads || leadsData || [];
      setLeads(leadsList);
      setError(null);
    } catch (err) {
      console.warn("Failed to load service records:", err.message);
      setError(err.message || "Failed to load service records");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  const openCreate = () => {
    setEditRecord(null);
    setForm({ ...emptyForm });
    setShowModal(true);
  };

  const openEdit = (record) => {
    setEditRecord(record);
    setForm({
      title: record.title || "",
      description: record.description || "",
      service_date: record.service_date ? record.service_date.split("T")[0] : "",
      notes: record.notes || "",
      invoice_amount: record.invoice_amount || "",
      lead_id: record.lead_id || "",
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    const body = {
      title: form.title.trim(),
      description: form.description.trim() || null,
      service_date: form.service_date || null,
      notes: form.notes.trim() || null,
      invoice_amount: form.invoice_amount ? Number(form.invoice_amount) : null,
      lead_id: form.lead_id || null,
    };
    try {
      if (editRecord) {
        await updateServiceRecord(user.tenantId, token, editRecord.id, body);
      } else {
        await createServiceRecord(user.tenantId, token, body);
      }
      setShowModal(false);
      setForm({ ...emptyForm });
      setEditRecord(null);
      loadData();
    } catch (err) {
      console.warn("Save record failed:", err.message);
      setError(err.message || "Failed to save service record");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (recordId) => {
    if (!window.confirm("Delete this service record? This cannot be undone.")) return;
    setDeletingIds((prev) => new Set(prev).add(recordId));
    try {
      await deleteServiceRecord(user.tenantId, token, recordId);
      setRecords((prev) => prev.filter((r) => r.id !== recordId));
      setError(null);
    } catch (err) {
      console.warn("Delete record failed:", err.message);
      setError(err.message || "Failed to delete record");
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(recordId);
        return next;
      });
    }
  };

  const handleGeneratePortalLink = async (leadId) => {
    if (!leadId) return;
    setGeneratingLinkFor(leadId);
    try {
      const result = await generatePortalLink(user.tenantId, token, leadId);
      setPortalLinks((prev) => ({ ...prev, [leadId]: result.portal_url || result.url || "" }));
    } catch (err) {
      console.warn("Generate portal link failed:", err.message);
      setError(err.message || "Failed to generate portal link");
    } finally {
      setGeneratingLinkFor(null);
    }
  };

  const handleCopyLink = (leadId) => {
    const url = portalLinks[leadId];
    if (!url) return;
    navigator.clipboard.writeText(url).then(() => {
      setCopiedId(leadId);
      setTimeout(() => setCopiedId(null), 2000);
    }).catch((err) => {
      console.warn("Copy failed:", err.message);
    });
  };

  const handleSendToClient = async (leadId) => {
    const url = portalLinks[leadId];
    const lead = leadMap[leadId];
    if (!url || !lead) return;
    setSendingToClient(leadId);
    setSendToast(null);
    try {
      await sendLeadEmail(user.tenantId, token, leadId, {
        subject: "Your service portal",
        body: `Hello${lead.name ? " " + lead.name : ""},\n\nYou can view your service history, invoices, and details through your personal portal:\n\n${url}\n\nIf you have any questions, feel free to reach out.\n\nThank you!`,
      });
      setSendToast({ type: "success", message: `Portal link sent to ${lead.email || lead.name || "client"}` });
      setTimeout(() => setSendToast(null), 4000);
    } catch (err) {
      console.warn("Send portal link failed:", err.message);
      setSendToast({ type: "error", message: err.body?.detail || err.message || "Failed to send portal link. Make sure the client has an email address." });
      setTimeout(() => setSendToast(null), 5000);
    } finally {
      setSendingToClient(null);
    }
  };

  // Build lead name lookup
  const leadMap = {};
  leads.forEach((l) => { leadMap[l.id] = l; });

  // Get unique leads that have service records
  const leadsWithRecords = [...new Set(records.filter((r) => r.lead_id).map((r) => r.lead_id))];

  if (loading) return <SkeletonLoader />;

  const totalRecords = records.length;
  const totalInvoiced = records.reduce((sum, r) => sum + (Number(r.invoice_amount) || 0), 0);
  const uniqueClients = leadsWithRecords.length;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Client Portal</h1>
          <p>Manage service records and generate portal access links for clients</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            className="btn-primary"
            onClick={() => {
              setLoading(true);
              loadData();
            }}
            style={{
              background: "transparent",
              border: "1px solid var(--border-color)",
              color: "var(--text-primary)",
            }}
          >
            Refresh
          </button>
          <button className="btn-primary" onClick={openCreate}>
            + New Record
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
          { label: "Service Records", value: totalRecords, color: "var(--text-secondary)" },
          { label: "Total Invoiced", value: formatCurrency(totalInvoiced) || "$0.00", color: "#22c55e" },
          { label: "Unique Clients", value: uniqueClients, color: "#3b82f6" },
        ].map((card) => (
          <div
            key={card.label}
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-color)",
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

      {/* Portal Link Generator per lead */}
      {leadsWithRecords.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
            Generate Portal Links
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {leadsWithRecords.map((leadId) => {
              const lead = leadMap[leadId];
              const displayName = lead ? (lead.name || lead.email || "Unknown") : `Lead #${leadId}`;
              const hasLink = portalLinks[leadId];
              const isGenerating = generatingLinkFor === leadId;
              const isCopied = copiedId === leadId;

              return (
                <div
                  key={leadId}
                  style={{
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border-color)",
                    borderRadius: 8,
                    padding: "8px 12px",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <span style={{ fontSize: "0.85rem", fontWeight: 500 }}>{displayName}</span>
                  {hasLink ? (
                    <>
                      <button
                        onClick={() => handleCopyLink(leadId)}
                        style={{
                          background: isCopied ? "rgba(34,197,94,0.1)" : "var(--accent-dim)",
                          border: `1px solid ${isCopied ? "#22c55e" : "var(--accent)"}`,
                          borderRadius: 6,
                          padding: "4px 10px",
                          color: isCopied ? "#22c55e" : "var(--accent)",
                          cursor: "pointer",
                          fontSize: "0.75rem",
                          fontWeight: 600,
                        }}
                      >
                        {isCopied ? "Copied!" : "Copy Link"}
                      </button>
                      <button
                        onClick={() => handleSendToClient(leadId)}
                        disabled={sendingToClient === leadId}
                        style={{
                          background: "rgba(139,92,246,0.1)",
                          border: "1px solid rgba(139,92,246,0.4)",
                          borderRadius: 6,
                          padding: "4px 10px",
                          color: "#8b5cf6",
                          cursor: sendingToClient === leadId ? "default" : "pointer",
                          fontSize: "0.75rem",
                          fontWeight: 600,
                          opacity: sendingToClient === leadId ? 0.6 : 1,
                        }}
                      >
                        {sendingToClient === leadId ? "Sending..." : "Send to Client"}
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => handleGeneratePortalLink(leadId)}
                      disabled={isGenerating}
                      style={{
                        background: "var(--accent-dim)",
                        border: "1px solid var(--accent)",
                        borderRadius: 6,
                        padding: "4px 10px",
                        color: "var(--accent)",
                        cursor: "pointer",
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        opacity: isGenerating ? 0.5 : 1,
                      }}
                    >
                      {isGenerating ? "Generating..." : "Generate Link"}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Send-to-client toast */}
      {sendToast && (
        <div
          style={{
            marginBottom: 16,
            padding: "10px 16px",
            background: sendToast.type === "success" ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
            border: `1px solid ${sendToast.type === "success" ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"}`,
            borderRadius: 8,
            color: sendToast.type === "success" ? "#22c55e" : "#ef4444",
            fontSize: "0.85rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span>{sendToast.message}</span>
          <button
            onClick={() => setSendToast(null)}
            style={{
              marginLeft: 12,
              background: "none",
              border: "none",
              color: sendToast.type === "success" ? "#22c55e" : "#ef4444",
              cursor: "pointer",
              fontSize: "0.8rem",
              textDecoration: "underline",
            }}
          >
            dismiss
          </button>
        </div>
      )}

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

      {/* Service Records List */}
      {records.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>No service records yet</div>
          <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
            Create service records to track completed work for your clients. You can then generate unique portal links so clients can view their service history and invoices.
          </p>
          <button className="btn-primary" onClick={openCreate}>
            Create Your First Record
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {records.map((record) => {
            const isDeleting = deletingIds.has(record.id);
            const lead = record.lead_id ? leadMap[record.lead_id] : null;

            return (
              <div
                key={record.id}
                style={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 12,
                  padding: 16,
                  opacity: isDeleting ? 0.5 : 1,
                  transition: "opacity 0.2s ease",
                }}
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
                      <span style={{ fontWeight: 600, fontSize: "1rem" }}>{record.title}</span>
                      {lead && (
                        <span
                          style={{
                            display: "inline-block",
                            padding: "2px 8px",
                            borderRadius: 4,
                            fontSize: "0.7rem",
                            fontWeight: 600,
                            color: "#3b82f6",
                            background: "rgba(59,130,246,0.1)",
                          }}
                        >
                          {lead.name || lead.email || "Client"}
                        </span>
                      )}
                    </div>
                    {record.description && (
                      <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.4, marginBottom: 4 }}>
                        {record.description.length > 150
                          ? record.description.slice(0, 150) + "..."
                          : record.description}
                      </div>
                    )}
                    <div style={{ display: "flex", gap: 12, fontSize: "0.8rem", color: "var(--text-muted)", flexWrap: "wrap" }}>
                      {record.service_date && <span>Date: {formatDate(record.service_date)}</span>}
                      {record.notes && (
                        <span>
                          Notes: {record.notes.length > 60 ? record.notes.slice(0, 60) + "..." : record.notes}
                        </span>
                      )}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    {record.invoice_amount ? (
                      <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#22c55e", textAlign: "right" }}>
                        {formatCurrency(record.invoice_amount)}
                      </div>
                    ) : null}
                    <div style={{ display: "flex", gap: 6 }}>
                      <button
                        onClick={() => openEdit(record)}
                        disabled={isDeleting}
                        style={{
                          background: "none",
                          border: "1px solid var(--border-color)",
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
                        onClick={() => handleDelete(record.id)}
                        disabled={isDeleting}
                        style={{
                          background: "none",
                          border: "1px solid var(--border-color)",
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
              maxWidth: 520,
              maxHeight: "80vh",
              overflowY: "auto",
              border: "1px solid var(--border-color)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 16 }}>
              {editRecord ? "Edit Service Record" : "Create Service Record"}
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
                  Title *
                </label>
                <input
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  placeholder="e.g. Monthly HVAC Maintenance, Roof Inspection"
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
                  placeholder="What was done, findings, recommendations..."
                  rows={3}
                  style={{ width: "100%", resize: "vertical" }}
                />
              </div>

              <div style={{ display: "flex", gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
                    Service Date
                  </label>
                  <input
                    type="date"
                    value={form.service_date}
                    onChange={(e) => setForm((f) => ({ ...f, service_date: e.target.value }))}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontSize: "0.85rem",
                    }}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
                    Invoice Amount
                  </label>
                  <input
                    type="number"
                    value={form.invoice_amount}
                    onChange={(e) => setForm((f) => ({ ...f, invoice_amount: e.target.value }))}
                    placeholder="0.00"
                    min={0}
                    step="0.01"
                    style={{ width: "100%" }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
                  Client (Lead)
                </label>
                <select
                  value={form.lead_id}
                  onChange={(e) => setForm((f) => ({ ...f, lead_id: e.target.value }))}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    fontSize: "0.85rem",
                    cursor: "pointer",
                  }}
                >
                  <option value="">-- No client linked --</option>
                  {leads.map((lead) => (
                    <option key={lead.id} value={lead.id}>
                      {lead.name || lead.email || lead.phone || `Lead #${lead.id}`}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
                  Notes
                </label>
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  placeholder="Internal notes, follow-up actions..."
                  rows={2}
                  style={{ width: "100%", resize: "vertical" }}
                />
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
              <button
                onClick={() => {
                  setShowModal(false);
                  setEditRecord(null);
                }}
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
                onClick={handleSave}
                disabled={!form.title.trim() || saving}
              >
                {saving ? "Saving..." : editRecord ? "Save Changes" : "Create Record"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
