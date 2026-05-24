import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import SkeletonLoader from "../../components/SkeletonLoader";
import {
  fetchDocuments,
  createDocument,
  sendDocument,
  deleteDocument,
  fetchDocTemplates,
  createDocTemplate,
} from "../../utils/api/documents";
import { fetchLeads } from "../../utils/api/leads";
import { STATUS_FILTERS, emptyForm } from "./constants";
import { formatDate } from "./utils";
import StatusBadge from "./StatusBadge";
import DocumentDetail from "./DocumentDetail";
import DocumentModal from "./DocumentModal";
import SendModal from "./SendModal";

export default function DocumentsPage() {
  const { user, token } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeFilter, setActiveFilter] = useState("all");
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);
  const [leads, setLeads] = useState([]);
  const [loadingDropdowns, setLoadingDropdowns] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [detailDoc, setDetailDoc] = useState(null);
  const [showSendModal, setShowSendModal] = useState(false);
  const [sendTarget, setSendTarget] = useState(null);
  const [sendMethod, setSendMethod] = useState("email");
  const [sending, setSending] = useState(false);
  const [deletingIds, setDeletingIds] = useState(new Set());
  const [copiedId, setCopiedId] = useState(null);

  const loadData = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const params = {};
      if (activeFilter !== "all") params.status = activeFilter;
      const data = await fetchDocuments(user.tenantId, token, params);
      setDocuments(data.documents || data || []);
      setError(null);
    } catch (err) {
      console.warn("Failed to load documents:", err.message);
      setError(err.message || "Failed to load documents");
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
      const [leadsData, templatesData] = await Promise.all([
        fetchLeads(user.tenantId, token, { per_page: 200 }),
        fetchDocTemplates(user.tenantId, token).catch(() => []),
      ]);
      setLeads(leadsData.leads || []);
      setTemplates(
        Array.isArray(templatesData)
          ? templatesData
          : templatesData?.templates || [],
      );
    } catch (err) {
      console.warn("Failed to load dropdowns:", err.message);
    } finally {
      setLoadingDropdowns(false);
    }
  };

  const openCreate = () => {
    setForm({ ...emptyForm });
    setSelectedTemplateId("");
    setShowModal(true);
    loadDropdowns();
  };

  const handleTemplateSelect = (templateId) => {
    setSelectedTemplateId(templateId);
    if (!templateId) return;
    const tmpl = templates.find((t) => t.id === templateId);
    if (tmpl)
      setForm((f) => ({
        ...f,
        title: tmpl.name || f.title,
        html_content: tmpl.html_content || tmpl.content || f.html_content,
      }));
  };

  const handleSave = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    const body = {
      title: form.title.trim(),
      html_content: form.html_content.trim() || null,
      signer_name: form.signer_name.trim() || null,
      signer_email: form.signer_email.trim() || null,
      signer_phone: form.signer_phone.trim() || null,
      lead_id: form.lead_id || null,
      expiry_days: Number(form.expiry_days) || 30,
      notes: form.notes.trim() || null,
    };
    try {
      await createDocument(user.tenantId, token, body);
      setShowModal(false);
      setForm({ ...emptyForm });
      loadData();
    } catch (err) {
      console.warn("Save document failed:", err.message);
      setError(err.message || "Failed to save document");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAsTemplate = async () => {
    if (!form.title.trim() || !form.html_content.trim()) return;
    setSavingTemplate(true);
    try {
      const created = await createDocTemplate(user.tenantId, token, {
        name: form.title.trim(),
        html_content: form.html_content.trim(),
      });
      setTemplates((prev) => [...prev, created]);
    } catch (err) {
      console.warn("Save template failed:", err.message);
      setError(err.message || "Failed to save template");
    } finally {
      setSavingTemplate(false);
    }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm("Delete this document? This cannot be undone.")) return;
    setDeletingIds((prev) => new Set(prev).add(docId));
    try {
      await deleteDocument(user.tenantId, token, docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      if (detailDoc?.id === docId) setDetailDoc(null);
      setError(null);
    } catch (err) {
      console.warn("Delete document failed:", err.message);
      setError(err.message || "Failed to delete document");
    } finally {
      setDeletingIds((prev) => {
        const n = new Set(prev);
        n.delete(docId);
        return n;
      });
    }
  };

  const openSend = (doc, e) => {
    if (e) e.stopPropagation();
    setSendTarget(doc);
    setSendMethod("email");
    setShowSendModal(true);
  };

  const handleSend = async () => {
    if (!sendTarget) return;
    setSending(true);
    try {
      await sendDocument(user.tenantId, token, sendTarget.id, {
        method: sendMethod,
      });
      setShowSendModal(false);
      setSendTarget(null);
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === sendTarget.id ? { ...d, status: "sent" } : d,
        ),
      );
      if (detailDoc?.id === sendTarget.id)
        setDetailDoc((prev) => ({ ...prev, status: "sent" }));
    } catch (err) {
      console.warn("Send document failed:", err.message);
      setError(err.message || "Failed to send document");
    } finally {
      setSending(false);
    }
  };

  const handleCopyLink = (doc, e) => {
    if (e) e.stopPropagation();
    const link = doc.signing_url || `${window.location.origin}/sign/${doc.id}`;
    navigator.clipboard
      .writeText(link)
      .then(() => {
        setCopiedId(doc.id);
        setTimeout(() => setCopiedId(null), 2000);
      })
      .catch(() => {
        setError("Failed to copy link to clipboard");
      });
  };

  if (loading) return <SkeletonLoader />;

  const totalDocs = documents.length;
  const pendingCount = documents.filter(
    (d) => d.status === "sent" || d.status === "viewed",
  ).length;
  const signedCount = documents.filter((d) => d.status === "signed").length;
  const draftCount = documents.filter((d) => d.status === "draft").length;
  const filteredDocs =
    activeFilter === "all"
      ? documents
      : documents.filter((d) => d.status === activeFilter);

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Documents & E-Signatures</h1>
          <p>Create, send, and track documents for signing</p>
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
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
            }}
          >
            Refresh
          </button>
          <button className="btn-primary" onClick={openCreate}>
            + New Document
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
            label: "Total Documents",
            value: totalDocs,
            color: "var(--text-secondary)",
          },
          { label: "Pending Signature", value: pendingCount, color: "#f59e0b" },
          { label: "Signed", value: signedCount, color: "#22c55e" },
          { label: "Draft", value: draftCount, color: "var(--text-muted)" },
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
        {STATUS_FILTERS.map((s) => {
          const isActive = activeFilter === s;
          const count =
            s === "all"
              ? documents.length
              : documents.filter((d) => d.status === s).length;
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
              {s}
              <span
                style={{ marginLeft: 6, fontSize: "0.75rem", opacity: 0.7 }}
              >
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

      {filteredDocs.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            color: "var(--text-muted)",
          }}
        >
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>
            {activeFilter !== "all"
              ? "No documents match this filter"
              : "No documents yet"}
          </div>
          <p style={{ maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
            {activeFilter !== "all"
              ? "Try selecting a different status filter, or create a new document."
              : "Create your first document to start collecting e-signatures. Add an HTML template, assign a signer, and send it via email or SMS."}
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
              Create Your First Document
            </button>
          )}
        </div>
      ) : (
        <div
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "2fr 1fr 100px 110px 160px",
              padding: "10px 16px",
              borderBottom: "1px solid var(--border)",
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            <span>Title</span>
            <span>Signer</span>
            <span style={{ textAlign: "center" }}>Status</span>
            <span style={{ textAlign: "center" }}>Created</span>
            <span style={{ textAlign: "right" }}>Actions</span>
          </div>
          {filteredDocs.map((doc) => {
            const isDeleting = deletingIds.has(doc.id);
            const canSend = doc.status === "draft";
            const hasSentOrViewed =
              doc.status === "sent" || doc.status === "viewed";
            return (
              <div
                key={doc.id}
                onClick={() => setDetailDoc(doc)}
                style={{
                  display: "grid",
                  gridTemplateColumns: "2fr 1fr 100px 110px 160px",
                  padding: "12px 16px",
                  borderBottom: "1px solid var(--border)",
                  alignItems: "center",
                  cursor: "pointer",
                  opacity: isDeleting ? 0.5 : 1,
                  transition: "background 0.1s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "var(--hover-overlay)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                }}
              >
                <span
                  style={{
                    fontSize: "0.85rem",
                    fontWeight: 600,
                    color: "var(--accent)",
                  }}
                >
                  {doc.title || "Untitled"}
                </span>
                <span
                  style={{
                    fontSize: "0.85rem",
                    color: "var(--text-secondary)",
                  }}
                >
                  {doc.signer_name || doc.signer_email || "--"}
                </span>
                <span style={{ textAlign: "center" }}>
                  <StatusBadge status={doc.status} />
                </span>
                <span
                  style={{
                    textAlign: "center",
                    fontSize: "0.8rem",
                    color: "var(--text-muted)",
                  }}
                >
                  {formatDate(doc.created_at)}
                </span>
                <div
                  style={{
                    display: "flex",
                    gap: 4,
                    justifyContent: "flex-end",
                  }}
                  onClick={(e) => e.stopPropagation()}
                >
                  {canSend && (
                    <button
                      onClick={(e) => openSend(doc, e)}
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
                  {hasSentOrViewed && (
                    <button
                      onClick={(e) => handleCopyLink(doc, e)}
                      style={{
                        background:
                          copiedId === doc.id ? "rgba(34,197,94,0.1)" : "none",
                        border: "1px solid var(--border)",
                        borderRadius: 6,
                        padding: "4px 8px",
                        color:
                          copiedId === doc.id
                            ? "#22c55e"
                            : "var(--text-secondary)",
                        cursor: "pointer",
                        fontSize: "0.75rem",
                      }}
                    >
                      {copiedId === doc.id ? "Copied!" : "Link"}
                    </button>
                  )}
                  {canSend && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(doc.id);
                      }}
                      disabled={isDeleting}
                      style={{
                        background: "none",
                        border: "1px solid var(--border)",
                        borderRadius: 6,
                        padding: "4px 8px",
                        color: "#ef4444",
                        cursor: "pointer",
                        fontSize: "0.75rem",
                      }}
                    >
                      {isDeleting ? "..." : "Del"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <DocumentDetail
        detailDoc={detailDoc}
        copiedId={copiedId}
        onClose={() => setDetailDoc(null)}
        onCopyLink={handleCopyLink}
        onSend={openSend}
        onDelete={handleDelete}
      />

      {showModal && (
        <DocumentModal
          form={form}
          setForm={setForm}
          templates={templates}
          selectedTemplateId={selectedTemplateId}
          onTemplateSelect={handleTemplateSelect}
          leads={leads}
          loadingDropdowns={loadingDropdowns}
          saving={saving}
          savingTemplate={savingTemplate}
          onClose={() => setShowModal(false)}
          onSave={handleSave}
          onSaveAsTemplate={handleSaveAsTemplate}
        />
      )}

      <SendModal
        sendTarget={showSendModal ? sendTarget : null}
        sendMethod={sendMethod}
        setSendMethod={setSendMethod}
        sending={sending}
        onClose={() => setShowSendModal(false)}
        onSend={handleSend}
      />
    </div>
  );
}
