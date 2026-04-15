import { useCallback, useEffect, useState } from "react";
import { notify } from "../utils/notify";

import InvoiceDetailModal from "../components/invoices/InvoiceDetailModal";
import InvoiceFormModal from "../components/invoices/InvoiceFormModal";
import InvoiceSendModal from "../components/invoices/InvoiceSendModal";
import InvoicesTableSection from "../components/invoices/InvoicesTableSection";
import {
  STATUS_FILTERS,
  emptyForm,
  emptyItem,
  formatCurrency,
} from "../components/invoices/invoiceUtils";
import SkeletonLoader from "../components/SkeletonLoader";
import { useAuth } from "../context/AuthContext";
import { fetchBids } from "../utils/api/bids";
import {
  bulkSendInvoices,
  createInvoice,
  createInvoiceFromBid,
  createItemTemplate,
  deleteInvoice,
  fetchInvoiceStats,
  fetchInvoices,
  fetchItemTemplates,
  markInvoicePaid,
  recordPayment,
  sendInvoice,
} from "../utils/api/invoices";
import { fetchLeads } from "../utils/api/leads";

export default function InvoicesPage() {
  const { user, token } = useAuth();
  const [invoices, setInvoices] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [activeFilter, setActiveFilter] = useState("all");

  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);

  const [leads, setLeads] = useState([]);
  const [bids, setBids] = useState([]);
  const [loadingDropdowns, setLoadingDropdowns] = useState(false);

  const [detailInvoice, setDetailInvoice] = useState(null);

  const [showSendModal, setShowSendModal] = useState(false);
  const [sendTarget, setSendTarget] = useState(null);
  const [sendMethod, setSendMethod] = useState("email");
  const [sending, setSending] = useState(false);

  const [markingPaid, setMarkingPaid] = useState(false);
  const [deletingIds, setDeletingIds] = useState(new Set());
  const [copiedId, setCopiedId] = useState(null);
  const [itemTemplates, setItemTemplates] = useState([]);
  const [showTemplates, setShowTemplates] = useState(false);
  const [paymentAmount, setPaymentAmount] = useState("");
  const [recordingPayment, setRecordingPayment] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkSending, setBulkSending] = useState(false);

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
  }, [activeFilter, token, user?.tenantId]);

  useEffect(() => {
    setLoading(true);
    void loadData();
  }, [loadData]);

  const loadDropdowns = async () => {
    if (!user?.tenantId || loadingDropdowns) return;

    setLoadingDropdowns(true);
    try {
      const [leadsData, bidsData, templatesData] = await Promise.all([
        fetchLeads(user.tenantId, token, { per_page: 200 }),
        fetchBids(user.tenantId, token),
        fetchItemTemplates(user.tenantId, token).catch(() => []),
      ]);

      setLeads(leadsData.leads || []);
      setBids(bidsData.bids || bidsData || []);
      setItemTemplates(Array.isArray(templatesData) ? templatesData : []);
    } catch (err) {
      console.warn("Failed to load dropdowns:", err.message);
    } finally {
      setLoadingDropdowns(false);
    }
  };

  const openCreate = () => {
    setForm({ ...emptyForm, items: [{ ...emptyItem }] });
    setShowTemplates(false);
    setShowModal(true);
    void loadDropdowns();
  };

  const closeCreate = () => {
    setShowModal(false);
    setShowTemplates(false);
  };

  const openDetail = (invoice) => {
    setPaymentAmount("");
    setDetailInvoice(invoice);
  };

  const closeDetail = () => {
    setPaymentAmount("");
    setDetailInvoice(null);
  };

  const openSend = (invoice, event) => {
    if (event) event.stopPropagation();
    setSendTarget(invoice);
    setSendMethod("email");
    setShowSendModal(true);
  };

  const closeSend = () => {
    setShowSendModal(false);
    setSendTarget(null);
  };

  const handleCreateFromBid = async (bidId) => {
    setSaving(true);
    try {
      await createInvoiceFromBid(user.tenantId, token, bidId);
      closeCreate();
      await loadData();
    } catch (err) {
      console.warn("Create from bid failed:", err.message);
      setError(err.message || "Failed to create invoice from bid");
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    if (!form.items.some((item) => item.description.trim())) return;

    setSaving(true);
    const body = {
      lead_id: form.lead_id || null,
      items: form.items.filter((item) => item.description.trim()),
      tax_rate: Number(form.tax_rate) || 0,
      due_date: form.due_date || null,
      notes: form.notes.trim() || null,
      deposit_amount: Number(form.deposit_amount) || 0,
      is_recurring: form.is_recurring,
      recurrence_interval: form.is_recurring
        ? form.recurrence_interval || null
        : null,
    };

    try {
      await createInvoice(user.tenantId, token, body);
      closeCreate();
      setForm({ ...emptyForm });
      await loadData();
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
      setInvoices((prev) => prev.filter((invoice) => invoice.id !== invoiceId));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(invoiceId);
        return next;
      });
      if (detailInvoice?.id === invoiceId) closeDetail();
      setError(null);
      void loadData();
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

  const handleSend = async () => {
    if (!sendTarget) return;

    setSending(true);
    try {
      await sendInvoice(user.tenantId, token, sendTarget.id, {
        method: sendMethod,
      });
      closeSend();
      if (detailInvoice?.id === sendTarget.id) {
        setDetailInvoice((prev) =>
          prev ? { ...prev, status: "sent" } : prev,
        );
      }
      await loadData();
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
      if (detailInvoice?.id === invoiceId) {
        setDetailInvoice((prev) =>
          prev ? { ...prev, status: "paid" } : prev,
        );
      }
      await loadData();
    } catch (err) {
      console.warn("Mark paid failed:", err.message);
      setError(err.message || "Failed to mark invoice as paid");
    } finally {
      setMarkingPaid(false);
    }
  };

  const handleCopyPaymentLink = (invoice, event) => {
    if (event) event.stopPropagation();

    const link =
      invoice.stripe_payment_link ||
      `${window.location.origin}/pay/${invoice.id}`;

    navigator.clipboard
      .writeText(link)
      .then(() => {
        setCopiedId(invoice.id);
        setTimeout(() => setCopiedId(null), 2000);
      })
      .catch(() => {
        setError("Failed to copy link to clipboard");
      });
  };

  const addItem = () => {
    setForm((current) => ({
      ...current,
      items: [...current.items, { ...emptyItem }],
    }));
  };

  const addFromTemplate = (template) => {
    setForm((current) => ({
      ...current,
      items: [
        ...current.items,
        {
          description: template.description,
          quantity: 1,
          unit_price: Number(template.unit_price),
        },
      ],
    }));
    setShowTemplates(false);
  };

  const handleRecordPayment = async (invoiceId) => {
    const amount = parseFloat(paymentAmount);
    if (!amount || amount <= 0) return;

    setRecordingPayment(true);
    try {
      await recordPayment(user.tenantId, token, invoiceId, { amount });
      setPaymentAmount("");
      closeDetail();
      await loadData();
    } catch (err) {
      console.warn("Failed to record payment:", err.message);
      setError(err.body?.detail || err.message || "Failed to record payment");
    } finally {
      setRecordingPayment(false);
    }
  };

  const saveAsTemplate = async (item) => {
    if (!item.description.trim()) return;

    try {
      const created = await createItemTemplate(user.tenantId, token, {
        description: item.description,
        unit_price: Number(item.unit_price) || 0,
      });
      setItemTemplates((prev) => [...prev, created]);
    } catch (err) {
      console.warn("Failed to save template:", err.message);
    }
  };

  const removeItem = (idx) => {
    setForm((current) => ({
      ...current,
      items:
        current.items.length > 1
          ? current.items.filter((_, itemIdx) => itemIdx !== idx)
          : current.items,
    }));
  };

  const updateItem = (idx, field, value) => {
    setForm((current) => ({
      ...current,
      items: current.items.map((item, itemIdx) =>
        itemIdx === idx ? { ...item, [field]: value } : item,
      ),
    }));
  };

  const handleBulkSend = async () => {
    if (selectedIds.size === 0) return;

    setBulkSending(true);
    try {
      const result = await bulkSendInvoices(
        user.tenantId,
        token,
        [...selectedIds],
        "email",
      );
      setError(null);
      setSelectedIds(new Set());
      await loadData();
      notify.error(
        `Sent: ${result.sent}, Failed: ${result.failed}${
          result.errors?.length ? "\n" + result.errors.join("\n") : ""
        }`,
      );
    } catch (err) {
      setError(err.body?.detail || err.message || "Bulk send failed");
    } finally {
      setBulkSending(false);
    }
  };

  if (loading) return <SkeletonLoader />;

  const subtotal = stats?.total_outstanding ?? 0;
  const totalPaid = stats?.total_paid ?? 0;
  const overdueCount =
    stats?.overdue_count ??
    invoices.filter((invoice) => invoice.status === "overdue").length;
  const avgDays = stats?.avg_days_to_payment ?? 0;

  const filteredInvoices =
    activeFilter === "all"
      ? invoices
      : invoices.filter((invoice) => invoice.status === activeFilter);

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
            onClick={() => {
              setLoading(true);
              void loadData();
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
            + Create Invoice
          </button>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 12,
          marginBottom: 24,
        }}
      >
        {[
          {
            label: "Total Outstanding",
            value: formatCurrency(subtotal),
            color: "#f59e0b",
          },
          {
            label: "Total Paid",
            value: formatCurrency(totalPaid),
            color: "#22c55e",
          },
          { label: "Overdue", value: overdueCount, color: "#ef4444" },
          {
            label: "Avg Days to Payment",
            value: avgDays ? `${Math.round(avgDays)}d` : "-",
            color: "#3b82f6",
          },
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
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                marginBottom: 4,
              }}
            >
              {card.label}
            </div>
            <div
              style={{ fontSize: "1.5rem", fontWeight: 700, color: card.color }}
            >
              {card.value}
            </div>
          </div>
        ))}
      </div>

      <div
        style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}
      >
        {STATUS_FILTERS.map((status) => {
          const isActive = activeFilter === status;
          const count =
            status === "all"
              ? invoices.length
              : invoices.filter((invoice) => invoice.status === status).length;

          return (
            <button
              key={status}
              onClick={() => setActiveFilter(status)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border: isActive
                  ? "1px solid var(--accent)"
                  : "1px solid var(--border)",
                background: isActive
                  ? "var(--accent-dim)"
                  : "var(--bg-secondary)",
                color: isActive ? "var(--accent)" : "var(--text-secondary)",
                cursor: "pointer",
                fontSize: "0.85rem",
                fontWeight: isActive ? 600 : 400,
                textTransform: "capitalize",
                transition: "all 0.15s ease",
              }}
            >
              {status}
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

      <InvoicesTableSection
        activeFilter={activeFilter}
        filteredInvoices={filteredInvoices}
        selectedIds={selectedIds}
        deletingIds={deletingIds}
        markingPaid={markingPaid}
        copiedId={copiedId}
        bulkSending={bulkSending}
        onSelectedIdsChange={setSelectedIds}
        onClearFilter={() => setActiveFilter("all")}
        onOpenCreate={openCreate}
        onOpenDetail={openDetail}
        onOpenSend={openSend}
        onMarkPaid={handleMarkPaid}
        onCopyPaymentLink={handleCopyPaymentLink}
        onDelete={handleDelete}
        onBulkSend={handleBulkSend}
      />

      {detailInvoice && (
        <InvoiceDetailModal
          detailInvoice={detailInvoice}
          copiedId={copiedId}
          paymentAmount={paymentAmount}
          recordingPayment={recordingPayment}
          markingPaid={markingPaid}
          onClose={closeDetail}
          onCopyPaymentLink={handleCopyPaymentLink}
          onPaymentAmountChange={setPaymentAmount}
          onRecordPayment={handleRecordPayment}
          onOpenSend={openSend}
          onMarkPaid={handleMarkPaid}
        />
      )}

      {showModal && (
        <InvoiceFormModal
          bids={bids}
          saving={saving}
          leads={leads}
          loadingDropdowns={loadingDropdowns}
          form={form}
          setForm={setForm}
          itemTemplates={itemTemplates}
          showTemplates={showTemplates}
          onShowTemplatesChange={setShowTemplates}
          onClose={closeCreate}
          onCreateFromBid={handleCreateFromBid}
          onAddItem={addItem}
          onAddFromTemplate={addFromTemplate}
          onSaveTemplate={saveAsTemplate}
          onRemoveItem={removeItem}
          onUpdateItem={updateItem}
          onSave={handleSave}
        />
      )}

      {showSendModal && sendTarget && (
        <InvoiceSendModal
          sendTarget={sendTarget}
          sendMethod={sendMethod}
          setSendMethod={setSendMethod}
          sending={sending}
          onClose={closeSend}
          onSend={handleSend}
        />
      )}
    </div>
  );
}
