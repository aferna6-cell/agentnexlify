import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  fetchInvoices,
  createInvoice,
  updateInvoice,
  deleteInvoice,
  sendInvoice,
  markInvoicePaid,
  fetchInvoiceStats,
  createInvoiceFromBid,
  fetchLeads,
  fetchBids,
} from "../utils/api";

const STATUS_FILTERS = ["all", "draft", "sent", "viewed", "paid", "overdue", "cancelled"];

const STATUS_COLORS = {
  draft: { color: "var(--text-muted)", bg: "var(--hover-overlay)" },
  sent: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  viewed: { color: "#8b5cf6", bg: "rgba(139,92,246,0.1)" },
  paid: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  overdue: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
  cancelled: { color: "var(--text-muted)", bg: "var(--hover-overlay)" },
};

const emptyItem = { description: "", quantity: 1, unit_price: 0 };

const emptyForm = {
  lead_id: "",
  items: [{ ...emptyItem }],
  tax_rate: 0,
  due_date: "",
  notes: "",
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

function calcSubtotal(items) {
  return (items || []).reduce((sum, it) => sum + (Number(it.quantity) || 0) * (Number(it.unit_price) || 0), 0);
}

function calcTotal(items, taxRate) {
  const sub = calcSubtotal(items);
  return sub + sub * (Number(taxRate) / 100 || 0);
}

function StatusBadge({ status }) {
  const sc = STATUS_COLORS[status] || STATUS_COLORS.draft;
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
      {status}
    </span>
  );
}

export default function InvoicesPage() {
  const { user, token } = useAuth();
  const [invoices, setInvoices] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [activeFilter, setActiveFilter] = useState("all");

  // Create modal
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);

  // Leads + bids for dropdowns
  const [leads, setLeads] = useState([]);
  const [bids, setBids] = useState([]);
  const [loadingDropdowns, setLoadingDropdowns] = useState(false);

  // Detail view
  const [detailInvoice, setDetailInvoice] = useState(null);

  // Send modal
  const [showSendModal, setShowSendModal] = useState(false);
  const [sendTarget, setSendTarget] = useState(null); // invoice to send
  const [sendMethod, setSendMethod] = useState("email");
  const [sending, setSending] = useState(false);

  // Mark paid
  const [markingPaid, setMarkingPaid] = useState(false);

  // Deleting
  const [deletingIds, setDeletingIds] = useState(new Set());

  // Copy payment link
  const [copiedId, setCopiedId] = useState(null);

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const params = {};
      if (activeFilter !== "all") params.status = activeFilter;
      const [invoicesData, statsData] = await Promise.all([
        fetchInvoices(user.tenantId, token, params),
        fetchInvoiceStats(user.tenantId, token),
      ]);
      setInvoices(invoicesData.invoices || invoicesData || []);
      setStats(statsData);
      setError(null);
    } catch (err) {
      console.warn("Failed to load invoices:", err.message);
      setError(err.message || "Failed to load invoices");
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, activeFilter]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  const loadDropdowns = async () => {
    if (!user?.tenantId || loadingDropdowns) return;
    setLoadingDropdowns(true);
    try {
      const [leadsData, bidsData] = await Promise.all([
        fetchLeads(user.tenantId, token, { per_page: 200 }),
        fetchBids(user.tenantId, token),
      ]);
      setLeads(leadsData.leads || []);
      setBids(bidsData.bids || bidsData || []);
    } catch (err) {
      console.warn("Failed to load dropdowns:", err.message);
    } finally {
      setLoadingDropdowns(false);
    }
  };

  const openCreate = () => {
    setForm({ ...emptyForm, items: [{ ...emptyItem }] });
    setShowModal(true);
    loadDropdowns();
  };

  const handleCreateFromBid = async (bidId) => {
    setSaving(true);
    try {
      await createInvoiceFromBid(user.tenantId, token, bidId);
      setShowModal(false);
      loadData();
    } catch (err) {
      console.warn("Create from bid failed:", err.message);
      setError(err.message || "Failed to create invoice from bid");
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    if (!form.items.some((it) => it.description.trim())) return;
    setSaving(true);
    const body = {
      lead_id: form.lead_id || null,
      items: form.items.filter((it) => it.description.trim()),
      tax_rate: Number(form.tax_rate) || 0,
      due_date: form.due_date || null,
      notes: form.notes.trim() || null,
    };
    try {
      await createInvoice(user.tenantId, token, body);
      setShowModal(false);
      setForm({ ...emptyForm });
      loadData();
    } catch (err) {
      console.warn("Save invoice failed:", err.message);
      setError(err.message || "Failed to save invoice");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (invoiceId) => {
    if (!window.confirm("Delete this invoice? This cannot be undone.")) return;
    setDeletingIds((prev) => new Set(prev).add(invoiceId));
    try {
      await deleteInvoice(user.tenantId, token, invoiceId);
      setInvoices((prev) => prev.filter((inv) => inv.id !== invoiceId));
      if (detailInvoice?.id === invoiceId) setDetailInvoice(null);
      setError(null);
    } catch (err) {
      console.warn("Delete invoice failed:", err.message);
      setError(err.message || "Failed to delete invoice");
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(invoiceId);
        return next;
      });
    }
  };

  const openSend = (invoice, e) => {
    if (e) e.stopPropagation();
    setSendTarget(invoice);
    setSendMethod("email");
    setShowSendModal(true);
  };

  const handleSend = async () => {
    if (!sendTarget) return;
    setSending(true);
    try {
      await sendInvoice(user.tenantId, token, sendTarget.id, { method: sendMethod });
      setShowSendModal(false);
      setSendTarget(null);
      // Update local status to sent
      setInvoices((prev) =>
        prev.map((inv) => (inv.id === sendTarget.id ? { ...inv, status: "sent" } : inv))
      );
      if (detailInvoice?.id === sendTarget.id) {
        setDetailInvoice((prev) => ({ ...prev, status: "sent" }));
      }
    } catch (err) {
      console.warn("Send invoice failed:", err.message);
      setError(err.message || "Failed to send invoice");
    } finally {
      setSending(false);
    }
  };

  const handleMarkPaid = async (invoiceId) => {
    setMarkingPaid(true);
    try {
      await markInvoicePaid(user.tenantId, token, invoiceId);
      setInvoices((prev) =>
        prev.map((inv) => (inv.id === invoiceId ? { ...inv, status: "paid" } : inv))
      );
      if (detailInvoice?.id === invoiceId) {
        setDetailInvoice((prev) => ({ ...prev, status: "paid" }));
      }
    } catch (err) {
      console.warn("Mark paid failed:", err.message);
      setError(err.message || "Failed to mark invoice as paid");
    } finally {
      setMarkingPaid(false);
    }
  };

  const handleCopyPaymentLink = (invoice, e) => {
    if (e) e.stopPropagation();
    const link = invoice.payment_link || `${window.location.origin}/pay/${invoice.id}`;
    navigator.clipboard.writeText(link).then(() => {
      setCopiedId(invoice.id);
      setTimeout(() => setCopiedId(null), 2000);
    }).catch(() => {
      setError("Failed to copy link to clipboard");
    });
  };

  // Line item helpers
  const addItem = () => {
    setForm((f) => ({ ...f, items: [...f.items, { ...emptyItem }] }));
  };

  const removeItem = (idx) => {
    setForm((f) => ({
      ...f,
      items: f.items.length > 1 ? f.items.filter((_, i) => i !== idx) : f.items,
    }));
  };

  const updateItem = (idx, field, value) => {
    setForm((f) => ({
      ...f,
      items: f.items.map((it, i) => (i === idx ? { ...it, [field]: value } : it)),
    }));
  };

  if (loading) return <SkeletonLoader />;

  const subtotal = stats?.total_outstanding ?? 0;
  const totalPaid = stats?.total_paid ?? 0;
  const overdueCount = stats?.overdue_count ?? invoices.filter((inv) => inv.status === "overdue").length;
  const avgDays = stats?.avg_days_to_payment ?? 0;

  const filteredInvoices = activeFilter === "all"
    ? invoices
    : invoices.filter((inv) => inv.status === activeFilter);

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Invoices</h1>
          <p>Create and track invoices, get paid faster</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            className="btn-primary"
            onClick={() => { setLoading(true); loadData(); }}
            style={{
              background: "transparent",
              border: "1px solid var(--border-color)",
              color: "var(--text-primary)",
            }}
          >
            Refresh
          </button>
          <button className="btn-primary" onClick={openCreate}>
            + Create Invoice
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
          { label: "Total Outstanding", value: formatCurrency(subtotal), color: "#f59e0b" },
          { label: "Total Paid", value: formatCurrency(totalPaid), color: "#22c55e" },
          { label: "Overdue", value: overdueCount, color: "#ef4444" },
          { label: "Avg Days to Payment", value: avgDays ? `${Math.round(avgDays)}d` : "—", color: "#3b82f6" },
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

      {/* Status Filter Tabs */}
      <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
        {STATUS_FILTERS.map((s) => {
          const isActive = activeFilter === s;
          const count = s === "all" ? invoices.length : invoices.filter((inv) => inv.status === s).length;
          return (
            <button
              key={s}
              onClick={() => setActiveFilter(s)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border: isActive ? "1px solid var(--accent)" : "1px solid var(--border-color)",
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
              <span style={{ marginLeft: 6, fontSize: "0.75rem", opacity: 0.7 }}>{count}</span>
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
            style={{ marginLeft: 12, background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: "0.8rem", textDecoration: "underline" }}
          >
            dismiss
          </button>
        </div>
      )}

      {/* Invoice Table */}
      {filteredInvoices.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>
            {activeFilter !== "all" ? "No invoices match this filter" : "No invoices yet"}
          </div>
          <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
            {activeFilter !== "all"
              ? "Try selecting a different status filter, or create a new invoice."
              : "Create your first invoice to start tracking payments. You can create invoices manually or convert a bid into an invoice."}
          </p>
          {activeFilter !== "all" ? (
            <button
              className="btn-primary"
              onClick={() => setActiveFilter("all")}
              style={{ background: "transparent", border: "1px solid var(--border-color)", color: "var(--text-primary)" }}
            >
              Clear Filter
            </button>
          ) : (
            <button className="btn-primary" onClick={openCreate}>
              Create Your First Invoice
            </button>
          )}
        </div>
      ) : (
        <div
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border-color)",
            borderRadius: 12,
            overflow: "hidden",
          }}
        >
          {/* Table Header */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "100px 1fr 120px 100px 110px 110px 160px",
              padding: "10px 16px",
              borderBottom: "1px solid var(--border-color)",
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            <span>Invoice #</span>
            <span>Customer</span>
            <span style={{ textAlign: "right" }}>Amount</span>
            <span style={{ textAlign: "center" }}>Status</span>
            <span style={{ textAlign: "center" }}>Due Date</span>
            <span style={{ textAlign: "center" }}>Sent</span>
            <span style={{ textAlign: "right" }}>Actions</span>
          </div>

          {filteredInvoices.map((inv) => {
            const isDeleting = deletingIds.has(inv.id);
            const total = calcTotal(inv.items || [], inv.tax_rate || 0);
            const canSend = inv.status === "draft" || inv.status === "sent";
            const canPay = inv.status === "sent" || inv.status === "viewed" || inv.status === "overdue";

            return (
              <div
                key={inv.id}
                onClick={() => setDetailInvoice(inv)}
                style={{
                  display: "grid",
                  gridTemplateColumns: "100px 1fr 120px 100px 110px 110px 160px",
                  padding: "12px 16px",
                  borderBottom: "1px solid var(--border-color)",
                  alignItems: "center",
                  cursor: "pointer",
                  opacity: isDeleting ? 0.5 : 1,
                  transition: "background 0.1s ease",
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = "var(--hover-overlay)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
              >
                <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--accent)" }}>
                  #{inv.invoice_number || inv.id?.slice(0, 8)}
                </span>
                <span style={{ fontSize: "0.85rem" }}>
                  {inv.customer_name || inv.lead_name || "—"}
                </span>
                <span style={{ textAlign: "right", fontSize: "0.9rem", fontWeight: 700, color: "#3b82f6" }}>
                  {formatCurrency(inv.total ?? total)}
                </span>
                <span style={{ textAlign: "center" }}>
                  <StatusBadge status={inv.status} />
                </span>
                <span style={{ textAlign: "center", fontSize: "0.8rem", color: inv.status === "overdue" ? "#ef4444" : "var(--text-secondary)" }}>
                  {formatDate(inv.due_date) || "—"}
                </span>
                <span style={{ textAlign: "center", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  {formatDate(inv.sent_at) || "—"}
                </span>
                <div
                  style={{ display: "flex", gap: 4, justifyContent: "flex-end" }}
                  onClick={(e) => e.stopPropagation()}
                >
                  {canSend && (
                    <button
                      onClick={(e) => openSend(inv, e)}
                      style={{
                        background: "rgba(59,130,246,0.1)",
                        border: "1px solid rgba(59,130,246,0.3)",
                        borderRadius: 6,
                        padding: "4px 10px",
                        color: "#3b82f6",
                        cursor: "pointer",
                        fontSize: "0.75rem",
                        fontWeight: 600,
                      }}
                    >
                      Send
                    </button>
                  )}
                  {canPay && (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleMarkPaid(inv.id); }}
                      disabled={markingPaid}
                      style={{
                        background: "rgba(34,197,94,0.1)",
                        border: "1px solid rgba(34,197,94,0.3)",
                        borderRadius: 6,
                        padding: "4px 10px",
                        color: "#22c55e",
                        cursor: "pointer",
                        fontSize: "0.75rem",
                        fontWeight: 600,
                      }}
                    >
                      {markingPaid ? "..." : "Paid"}
                    </button>
                  )}
                  <button
                    onClick={(e) => handleCopyPaymentLink(inv, e)}
                    style={{
                      background: "none",
                      border: "1px solid var(--border-color)",
                      borderRadius: 6,
                      padding: "4px 8px",
                      color: copiedId === inv.id ? "#22c55e" : "var(--text-secondary)",
                      cursor: "pointer",
                      fontSize: "0.75rem",
                    }}
                    title="Copy payment link"
                  >
                    {copiedId === inv.id ? "Copied!" : "Link"}
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(inv.id); }}
                    disabled={isDeleting}
                    style={{
                      background: "none",
                      border: "1px solid var(--border-color)",
                      borderRadius: 6,
                      padding: "4px 8px",
                      color: "#ef4444",
                      cursor: "pointer",
                      fontSize: "0.75rem",
                    }}
                  >
                    {isDeleting ? "..." : "Del"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Invoice Detail Modal */}
      {detailInvoice && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}
          onClick={() => setDetailInvoice(null)}
        >
          <div
            style={{ background: "var(--bg-primary)", borderRadius: 12, padding: 24, width: "90%", maxWidth: 620, maxHeight: "85vh", overflowY: "auto", border: "1px solid var(--border-color)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <h3 style={{ marginBottom: 6 }}>
                  Invoice #{detailInvoice.invoice_number || detailInvoice.id?.slice(0, 8)}
                </h3>
                <StatusBadge status={detailInvoice.status} />
              </div>
              <button
                onClick={() => setDetailInvoice(null)}
                style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "1.2rem" }}
              >
                x
              </button>
            </div>

            {(detailInvoice.customer_name || detailInvoice.lead_name) && (
              <div style={{ marginBottom: 12, fontSize: "0.9rem", color: "var(--text-secondary)" }}>
                <strong>Customer:</strong> {detailInvoice.customer_name || detailInvoice.lead_name}
              </div>
            )}

            <div style={{ display: "flex", gap: 20, marginBottom: 16, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              {detailInvoice.due_date && (
                <div><strong>Due:</strong> {formatDate(detailInvoice.due_date)}</div>
              )}
              {detailInvoice.sent_at && (
                <div><strong>Sent:</strong> {formatDate(detailInvoice.sent_at)}</div>
              )}
              {detailInvoice.paid_at && (
                <div><strong>Paid:</strong> {formatDate(detailInvoice.paid_at)}</div>
              )}
            </div>

            {/* Line Items */}
            {(detailInvoice.items || []).length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                  Items
                </div>
                <div style={{ border: "1px solid var(--border-color)", borderRadius: 8, overflow: "hidden" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", padding: "8px 12px", background: "var(--bg-secondary)", fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>
                    <span>Description</span>
                    <span style={{ textAlign: "right" }}>Qty</span>
                    <span style={{ textAlign: "right" }}>Unit Price</span>
                    <span style={{ textAlign: "right" }}>Total</span>
                  </div>
                  {detailInvoice.items.map((item, idx) => (
                    <div key={idx} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", padding: "8px 12px", borderTop: "1px solid var(--border-color)", fontSize: "0.85rem" }}>
                      <span>{item.description}</span>
                      <span style={{ textAlign: "right" }}>{item.quantity}</span>
                      <span style={{ textAlign: "right" }}>{formatCurrency(item.unit_price)}</span>
                      <span style={{ textAlign: "right", fontWeight: 600 }}>{formatCurrency((item.quantity || 0) * (item.unit_price || 0))}</span>
                    </div>
                  ))}
                </div>

                {/* Totals */}
                <div style={{ padding: "8px 12px", fontSize: "0.85rem" }}>
                  {(() => {
                    const sub = calcSubtotal(detailInvoice.items);
                    const taxRate = detailInvoice.tax_rate || 0;
                    const taxAmt = sub * (taxRate / 100);
                    const total = sub + taxAmt;
                    return (
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
                        <div style={{ color: "var(--text-secondary)" }}>Subtotal: {formatCurrency(sub)}</div>
                        {taxRate > 0 && (
                          <div style={{ color: "var(--text-secondary)" }}>Tax ({taxRate}%): {formatCurrency(taxAmt)}</div>
                        )}
                        <div style={{ fontWeight: 700, fontSize: "1rem", color: "#3b82f6" }}>Total: {formatCurrency(total)}</div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            )}

            {detailInvoice.notes && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", marginBottom: 4 }}>Notes</div>
                <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>{detailInvoice.notes}</div>
              </div>
            )}

            {/* Payment Link */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", marginBottom: 4 }}>Payment Link</div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input
                  readOnly
                  value={detailInvoice.payment_link || `${window.location.origin}/pay/${detailInvoice.id}`}
                  style={{ flex: 1, fontSize: "0.8rem", background: "var(--bg-secondary)", color: "var(--text-secondary)" }}
                />
                <button
                  onClick={() => handleCopyPaymentLink(detailInvoice)}
                  style={{
                    background: copiedId === detailInvoice.id ? "rgba(34,197,94,0.1)" : "var(--bg-secondary)",
                    border: "1px solid var(--border-color)",
                    borderRadius: 6,
                    padding: "6px 12px",
                    color: copiedId === detailInvoice.id ? "#22c55e" : "var(--text-secondary)",
                    cursor: "pointer",
                    fontSize: "0.8rem",
                    whiteSpace: "nowrap",
                  }}
                >
                  {copiedId === detailInvoice.id ? "Copied!" : "Copy Link"}
                </button>
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", borderTop: "1px solid var(--border-color)", paddingTop: 16 }}>
              {(detailInvoice.status === "draft" || detailInvoice.status === "sent") && (
                <button
                  onClick={() => { setDetailInvoice(null); openSend(detailInvoice); }}
                  style={{ background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.3)", borderRadius: 8, padding: "8px 16px", color: "#3b82f6", cursor: "pointer", fontSize: "0.85rem", fontWeight: 600 }}
                >
                  Send Invoice
                </button>
              )}
              {(detailInvoice.status === "sent" || detailInvoice.status === "viewed" || detailInvoice.status === "overdue") && (
                <button
                  onClick={() => handleMarkPaid(detailInvoice.id)}
                  disabled={markingPaid}
                  style={{ background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.3)", borderRadius: 8, padding: "8px 16px", color: "#22c55e", cursor: "pointer", fontSize: "0.85rem", fontWeight: 600 }}
                >
                  {markingPaid ? "Marking..." : "Mark as Paid"}
                </button>
              )}
              <button
                onClick={() => setDetailInvoice(null)}
                className="btn-primary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Invoice Modal */}
      {showModal && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}
          onClick={() => setShowModal(false)}
        >
          <div
            style={{ background: "var(--bg-primary)", borderRadius: 12, padding: 24, width: "90%", maxWidth: 640, maxHeight: "88vh", overflowY: "auto", border: "1px solid var(--border-color)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 16 }}>Create Invoice</h3>

            {/* Create from Bid shortcut */}
            {bids.length > 0 && (
              <div style={{ background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.2)", borderRadius: 8, padding: 12, marginBottom: 16 }}>
                <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#3b82f6", marginBottom: 8 }}>
                  Create from Bid
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <select
                    id="bid-select"
                    defaultValue=""
                    style={{ flex: 1, fontSize: "0.85rem" }}
                  >
                    <option value="" disabled>Select a bid...</option>
                    {bids.map((bid) => (
                      <option key={bid.id} value={bid.id}>
                        {bid.title} — {formatCurrency(calcTotal(bid.line_items || [], 0))}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => {
                      const sel = document.getElementById("bid-select");
                      if (sel.value) handleCreateFromBid(sel.value);
                    }}
                    disabled={saving}
                    style={{ background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "6px 14px", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600, whiteSpace: "nowrap" }}
                  >
                    {saving ? "Creating..." : "Convert"}
                  </button>
                </div>
                <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 4 }}>
                  Instantly converts a bid into an invoice with all line items copied over
                </div>
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {/* Customer */}
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
                  Customer (optional)
                </label>
                {loadingDropdowns ? (
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Loading customers...</div>
                ) : (
                  <select
                    value={form.lead_id}
                    onChange={(e) => setForm((f) => ({ ...f, lead_id: e.target.value }))}
                    style={{ width: "100%" }}
                  >
                    <option value="">No customer linked</option>
                    {leads.map((lead) => (
                      <option key={lead.id} value={lead.id}>
                        {lead.name || lead.email || lead.phone || lead.id}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Line Items */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Items *</label>
                  <button
                    onClick={addItem}
                    style={{ background: "none", border: "1px solid var(--border-color)", borderRadius: 6, padding: "4px 10px", color: "var(--accent)", cursor: "pointer", fontSize: "0.75rem" }}
                  >
                    + Add Item
                  </button>
                </div>

                {/* Items header */}
                <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 80px 20px", gap: 6, marginBottom: 4, fontSize: "0.7rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>
                  <span>Description</span>
                  <span style={{ textAlign: "right" }}>Qty</span>
                  <span style={{ textAlign: "right" }}>Unit Price</span>
                  <span style={{ textAlign: "right" }}>Total</span>
                  <span />
                </div>

                {form.items.map((item, idx) => (
                  <div key={idx} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 80px 20px", gap: 6, marginBottom: 6, alignItems: "center" }}>
                    <input
                      value={item.description}
                      onChange={(e) => updateItem(idx, "description", e.target.value)}
                      placeholder="Item description"
                    />
                    <input
                      type="number"
                      value={item.quantity}
                      onChange={(e) => updateItem(idx, "quantity", e.target.value)}
                      min={0}
                      step="1"
                      style={{ textAlign: "right" }}
                    />
                    <input
                      type="number"
                      value={item.unit_price}
                      onChange={(e) => updateItem(idx, "unit_price", e.target.value)}
                      min={0}
                      step="0.01"
                      placeholder="0.00"
                      style={{ textAlign: "right" }}
                    />
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textAlign: "right" }}>
                      {formatCurrency((Number(item.quantity) || 0) * (Number(item.unit_price) || 0))}
                    </span>
                    {form.items.length > 1 && (
                      <button
                        onClick={() => removeItem(idx)}
                        style={{ background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: "0.9rem", padding: 0 }}
                      >
                        x
                      </button>
                    )}
                  </div>
                ))}

                {/* Totals summary */}
                <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: 8, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, fontSize: "0.85rem" }}>
                  <div style={{ color: "var(--text-secondary)" }}>
                    Subtotal: {formatCurrency(calcSubtotal(form.items))}
                  </div>
                  {Number(form.tax_rate) > 0 && (
                    <div style={{ color: "var(--text-secondary)" }}>
                      Tax ({form.tax_rate}%): {formatCurrency(calcSubtotal(form.items) * (Number(form.tax_rate) / 100))}
                    </div>
                  )}
                  <div style={{ fontWeight: 700, color: "#3b82f6", fontSize: "0.95rem" }}>
                    Total: {formatCurrency(calcTotal(form.items, form.tax_rate))}
                  </div>
                </div>
              </div>

              {/* Tax Rate + Due Date */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
                    Tax Rate (%)
                  </label>
                  <input
                    type="number"
                    value={form.tax_rate}
                    onChange={(e) => setForm((f) => ({ ...f, tax_rate: e.target.value }))}
                    min={0}
                    max={100}
                    step="0.1"
                    placeholder="0"
                    style={{ width: "100%" }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
                    Due Date
                  </label>
                  <input
                    type="date"
                    value={form.due_date}
                    onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))}
                    style={{ width: "100%" }}
                  />
                </div>
              </div>

              {/* Notes */}
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", marginBottom: 4, color: "var(--text-secondary)" }}>
                  Notes
                </label>
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  placeholder="Payment terms, special instructions..."
                  rows={3}
                  style={{ width: "100%", resize: "vertical" }}
                />
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowModal(false)}
                style={{ background: "transparent", border: "1px solid var(--border-color)", borderRadius: 8, padding: "8px 16px", color: "var(--text-primary)", cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleSave}
                disabled={!form.items.some((it) => it.description.trim()) || saving}
              >
                {saving ? "Creating..." : "Create Invoice"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Send Invoice Modal */}
      {showSendModal && sendTarget && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1100 }}
          onClick={() => setShowSendModal(false)}
        >
          <div
            style={{ background: "var(--bg-primary)", borderRadius: 12, padding: 24, width: "90%", maxWidth: 480, border: "1px solid var(--border-color)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 4 }}>Send Invoice</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 20 }}>
              Invoice #{sendTarget.invoice_number || sendTarget.id?.slice(0, 8)} —{" "}
              {formatCurrency(sendTarget.total ?? calcTotal(sendTarget.items || [], sendTarget.tax_rate || 0))}
            </p>

            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: 10, fontWeight: 600 }}>
                Send Method
              </div>
              {["email", "sms", "both"].map((method) => (
                <label
                  key={method}
                  style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, cursor: "pointer" }}
                >
                  <input
                    type="radio"
                    name="send-method"
                    value={method}
                    checked={sendMethod === method}
                    onChange={() => setSendMethod(method)}
                    style={{ width: "auto" }}
                  />
                  <span style={{ fontSize: "0.9rem", textTransform: "capitalize" }}>
                    {method === "both" ? "Email + SMS" : method.toUpperCase()}
                  </span>
                </label>
              ))}
            </div>

            <div
              style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-color)", borderRadius: 8, padding: 12, marginBottom: 20, fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: 1.6 }}
            >
              <strong>Preview:</strong>
              <br />
              {sendMethod === "sms" || sendMethod === "both"
                ? `SMS: "Invoice #${sendTarget.invoice_number || sendTarget.id?.slice(0, 8)} for ${formatCurrency(sendTarget.total ?? 0)} is ready. Pay at: [payment link]"`
                : null}
              {(sendMethod === "email" || sendMethod === "both") && (
                <span>
                  {sendMethod === "both" && <br />}
                  Email: Professional invoice with itemized breakdown, payment link, and your business details.
                </span>
              )}
            </div>

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowSendModal(false)}
                style={{ background: "transparent", border: "1px solid var(--border-color)", borderRadius: 8, padding: "8px 16px", color: "var(--text-primary)", cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleSend}
                disabled={sending}
              >
                {sending ? "Sending..." : "Send Invoice"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
